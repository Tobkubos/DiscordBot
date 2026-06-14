import sys
import random
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datasets import load_dataset
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, roc_curve, auc

# --- KONFIGURACJA ---
API_URL = "http://127.0.0.1:8000"  # Adres Twojego backendu FastAPI
TEST_GUILD_ID = "eval_test_guild"   # Testowa gildia
SAMPLE_SIZE = 250                    # Liczba próbek na klasę (50 FAKE i 50 REAL = 100 testów)
# ---------------------

def setup_test_guild():
    """Wysyła żądanie konfiguracji gildii testowej, aby zapobiec SetupRequiredError."""
    print(f"[*] Konfigurowanie testowej gildii '{TEST_GUILD_ID}' na backendzie...")
    setup_payload = {
        "active_text_model": "bibbbu/multilingual-ai-human-detector_xlm-roberta-base",  # Model, który chcemy przetestować
        "active_image_model": "none",
        "log_channel_id": None,
        "multi_model_workflow": False
    }
    try:
        r = requests.post(f"{API_URL}/guilds/{TEST_GUILD_ID}/setup", json=setup_payload)
        if r.status_code == 200:
            print("[+] Testowa gildia skonfigurowana pomyślnie.")
        else:
            print(f"[-] Błąd konfiguracji gildii: {r.status_code} - {r.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Brak połączenia z FastAPI pod adresem {API_URL}. Upewnij się, że serwer działa. Błąd: {e}")
        sys.exit(1)

def prepare_dataset(sample_size):
    """Pobiera zbiór HC3 z Hugging Face i tworzy zbalansowany zbiór testowy."""
    print("[*] Pobieranie zbioru Hello-SimpleAI/HC3 z Hugging Face...")
    try:
        # Pobieranie bezpiecznej wersji Parquet
        ds = load_dataset(
            "Hello-SimpleAI/HC3", 
            "default", 
            revision="refs/convert/parquet", 
            split="train"
        )
    except Exception as e:
        print(f"[-] Nie udało się pobrać zbioru z Hugging Face: {e}")
        sys.exit(1)
        
    human_texts = []
    ai_texts = []
    
    print("[*] Filtrowanie i przygotowywanie próbek tekstowych...")
    for item in ds:
        # human_answers i chatgpt_answers są listami stringów
        for ans in item.get("human_answers", []):
            # Filtrujemy teksty: min 50 znaków (wymóg FastAPI), maks 1000 znaków dla szybkości
            if 50 <= len(ans) <= 1000:
                human_texts.append(ans)
        for ans in item.get("chatgpt_answers", []):
            if 50 <= len(ans) <= 1000:
                ai_texts.append(ans)
                
    # Losowanie zbalansowanej próbki z ziarnem losowości (powtarzalność testu)
    random.seed(42)
    human_selected = random.sample(human_texts, min(sample_size, len(human_texts)))
    ai_selected = random.sample(ai_texts, min(sample_size, len(ai_texts)))
    
    test_set = []
    for text in human_selected:
        test_set.append({"text": text, "is_fake_ground_truth": False})
    for text in ai_selected:
        test_set.append({"text": text, "is_fake_ground_truth": True})
        
    random.shuffle(test_set)
    
    return test_set  # <-- TA LINIA MUSI BYĆ NA KOŃCU FUNKCJI

def run_evaluation(test_set):
    """Przeprowadza testy wysyłając zapytania do endpointu FastAPI."""
    raw_results = []
    total = len(test_set)
    
    print(f"[*] Rozpoczynanie wysyłki {total} żądań do FastAPI...")
    
    for i, item in enumerate(test_set):
        payload = {
            "guild_id": TEST_GUILD_ID,
            "user_id": f"eval_user_{i}",  # Obejście limitera (unikalny użytkownik na zapytanie)
            "text": item["text"],
            "content_type": "text"
        }
        
        try:
            r = requests.post(f"{API_URL}/analyze", json=payload)
            if r.status_code == 200:
                data = r.json()
                is_deepfake_pred = data["is_deepfake"]
                confidence = data["confidence"]
                analysis_time = data["analysis_time"]
                used_model = data["used_model"]
                
                raw_results.append({
                    "id": i,
                    "text_snippet": item["text"][:60].replace("\n", " ") + "...",
                    "ground_truth": item["is_fake_ground_truth"],
                    "predicted": is_deepfake_pred,
                    "confidence": confidence,
                    "analysis_time": analysis_time,
                    "used_model": used_model,
                    "status": "SUCCESS"
                })
                print(f"[{i+1}/{total}] OK | GT: {item['is_fake_ground_truth']} | PRED: {is_deepfake_pred} | Conf: {confidence:.2f}")
            else:
                print(f"[{i+1}/{total}] Błąd API ({r.status_code}): {r.text}")
                raw_results.append({"id": i, "status": f"API_ERROR_{r.status_code}", "ground_truth": item["is_fake_ground_truth"]})
        except Exception as e:
            print(f"[{i+1}/{total}] Błąd połączenia: {e}")
            raw_results.append({"id": i, "status": "CONNECTION_ERROR", "ground_truth": item["is_fake_ground_truth"]})
            
    return raw_results

def process_and_save_results(raw_results):
    """Wylicza metryki, zapisuje raporty oraz generuje wykresy."""
    df_all = pd.DataFrame(raw_results)
    df_all.to_csv("evaluation_raw_results.csv", index=False, encoding="utf-8")
    print("[+] Zapisano surowe wyniki do: evaluation_raw_results.csv")
    
    # Filtrujemy tylko pomyślne wykonania do wyliczenia statystyk
    df_success = df_all[df_all["status"] == "SUCCESS"].copy()
    if df_success.empty:
        print("[-] Brak pomyślnych wyników analizy. Wykresy i raporty nie zostaną wygenerowane.")
        return
        
    y_true = df_success["ground_truth"].astype(bool).tolist()
    y_pred = df_success["predicted"].astype(bool).tolist()
    
    # Obliczamy ciągłe prawdopodobieństwo przynależności do klasy FAKE (potrzebne do krzywej ROC)
    # Jeśli model przewidział FAKE (True): prawdopodobieństwo FAKE to 'confidence'
    # Jeśli model przewidział REAL (False): prawdopodobieństwo FAKE to '1.0 - confidence'
    y_prob_fake = []
    for _, row in df_success.iterrows():
        conf = row["confidence"]
        pred = row["predicted"]
        y_prob_fake.append(conf if pred else 1.0 - conf)
    
    acc = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=["REAL (Human)", "FAKE (AI)"])
    avg_time = df_success["analysis_time"].mean()
    
    # 1. Zapisywanie raportu tekstowego
    report_filename = "evaluation_summary_report.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("      RAPORT JAKOŚCI USŁUGI DETEKCJI TEKSTU       \n")
        f.write("==================================================\n")
        f.write(f"Zanalizowano pomyślnie próbki: {len(df_success)} / {len(df_all)}\n")
        f.write(f"Ogólna dokładność (Accuracy): {acc:.2%}\n")
        f.write(f"Średni czas analizy: {avg_time:.3f} sekundy\n\n")
        f.write("Szczegółowe metryki klasyfikacji:\n")
        f.write(report)
        f.write("==================================================\n")
    print(f"[+] Zapisano tekstowy raport końcowy do: {report_filename}")
    
    # Wyświetlenie raportu w konsoli
    print("\n" + "="*50 + "\n" + f"DOKŁADNOŚĆ SYSTEMU: {acc:.2%}" + "\n" + "="*50)
    print(report)

    # 2. Wykres: Macierz Pomyłek (Confusion Matrix)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=["REAL (Human)", "FAKE (AI)"],
        yticklabels=["REAL (Human)", "FAKE (AI)"]
    )
    plt.title("Macierz Pomyłek (Confusion Matrix)")
    plt.ylabel("Wartość Rzeczywista")
    plt.xlabel("Wartość Przewidziana")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png")
    print("[+] Wygenerowano wykres: confusion_matrix.png")
    plt.close()

    # 3. Wykres: Krzywa ROC
    fpr, tpr, _ = roc_curve(y_true, y_prob_fake)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"Krzywa ROC (AUC = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate (1 - Specyficzność)")
    plt.ylabel("True Positive Rate (Czułość / Recall)")
    plt.title("Krzywa ROC (Receiver Operating Characteristic)")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig("roc_curve.png")
    print("[+] Wygenerowano wykres: roc_curve.png")
    plt.close()

if __name__ == "__main__":
    setup_test_guild()
    test_set = prepare_dataset(SAMPLE_SIZE)
    raw_results = run_evaluation(test_set)
    process_and_save_results(raw_results)