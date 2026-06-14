import os
import sys
import random
import shutil
import socket
import requests
import threading
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from functools import partial
from http.server import SimpleHTTPRequestHandler, HTTPServer
from datasets import load_dataset
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, roc_curve, auc

# --- KONFIGURACJA ---
API_URL = "http://127.0.0.1:8000"       # Adres Twojego backendu FastAPI
TEST_GUILD_ID = "eval_test_guild"        # Testowa gildia
SAMPLE_SIZE = 30                         # Liczba próbek na klasę (30 FAKE + 30 REAL = 60 testów)
TEMP_DIR = "temp_eval_images"            # Katalog tymczasowy na zdjęcia
# ---------------------

def setup_test_guild():
    """Wysyła żądanie konfiguracji gildii testowej na backendzie."""
    print(f"[*] Konfigurowanie testowej gildii '{TEST_GUILD_ID}' na backendzie...")
    setup_payload = {
        "active_text_model": "none",
        "active_image_model": "capcheck/ai-image-detection",  # Model do przetestowania
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
        print(f"[-] Brak połączenia z FastAPI pod adresem {API_URL}. Błąd: {e}")
        sys.exit(1)

def prepare_dataset(sample_size):
    """Pobiera zbiór CIFAKE z Hugging Face i tworzy zbalansowany zbiór testowy."""
    print("[*] Pobieranie zbioru yanbax/CIFAKE_autotrain_compatible...")
    try:
        ds = load_dataset(
            "yanbax/CIFAKE_autotrain_compatible", 
            split="train", 
            revision="refs/convert/parquet"
        )
    except Exception as e:
        print(f"[-] Nie udało się pobrać zbioru z Hugging Face: {e}")
        sys.exit(1)
        
    # Pobieramy nazwy klas z metadanych zbioru
    label_names = ds.features['label'].names
    print(f"[+] Wykryte klasy w zbiorze: {label_names}")
    
    # Znajdujemy indeks klasy oznaczającej sztuczny obraz (fake)
    fake_label_idx = next(i for i, name in enumerate(label_names) if "fake" in name.lower())
    
    real_images = []
    fake_images = []
    
    print("[*] Filtrowanie i przygotowywanie próbek obrazów...")
    for item in ds:
        if item['label'] == fake_label_idx:
            fake_images.append(item['image'])
        else:
            real_images.append(item['image'])
            
        # Przerywamy zbieranie próbek, kiedy mamy ich wystarczająco dużo do losowania
        if len(real_images) >= sample_size * 2 and len(fake_images) >= sample_size * 2:
            break
            
    # Losowanie próbek
    random.seed(42)
    real_selected = random.sample(real_images, min(sample_size, len(real_images)))
    fake_selected = random.sample(fake_images, min(sample_size, len(fake_images)))
    
    test_set = []
    for img in real_selected:
        test_set.append({"image": img, "is_fake_ground_truth": False})
    for img in fake_selected:
        test_set.append({"image": img, "is_fake_ground_truth": True})
        
    random.shuffle(test_set)
    return test_set

def find_free_port():
    """Wyszukuje wolny port w systemie operacyjnym."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_evaluation(test_set, host, port):
    """Przeprowadza testy wysyłając żądania do FastAPI."""
    raw_results = []
    total = len(test_set)
    
    print(f"[*] Rozpoczynanie wysyłki {total} żądań do FastAPI...")
    
    for i, item in enumerate(test_set):
        # Generujemy lokalny URL prowadzący do naszego tymczasowego serwera HTTP
        image_url = f"http://{host}:{port}/{item['local_filename']}"
        
        payload = {
            "guild_id": TEST_GUILD_ID,
            "user_id": f"eval_user_img_{i}",  # Obejście limitera
            "image_url": image_url,
            "content_type": "image"
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
    df_all.to_csv("image_evaluation_raw_results.csv", index=False, encoding="utf-8")
    print("[+] Zapisano surowe wyniki do: image_evaluation_raw_results.csv")
    
    df_success = df_all[df_all["status"] == "SUCCESS"].copy()
    if df_success.empty:
        print("[-] Brak pomyślnych wyników analizy. Wykresy i raporty nie zostaną wygenerowane.")
        return
        
    y_true = df_success["ground_truth"].astype(bool).tolist()
    y_pred = df_success["predicted"].astype(bool).tolist()
    
    y_prob_fake = []
    for _, row in df_success.iterrows():
        conf = row["confidence"]
        pred = row["predicted"]
        y_prob_fake.append(conf if pred else 1.0 - conf)
    
    acc = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=["REAL_IMAGE", "AI_GENERATED"])
    avg_time = df_success["analysis_time"].mean()
    
    report_filename = "image_evaluation_summary_report.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("      RAPORT JAKOŚCI DETEKCJI OBRAZÓW (DEEPFAKE)  \n")
        f.write("==================================================\n")
        f.write(f"Zanalizowano pomyślnie próbki: {len(df_success)} / {len(df_all)}\n")
        f.write(f"Ogólna dokładność (Accuracy): {acc:.2%}\n")
        f.write(f"Średni czas analizy: {avg_time:.3f} sekundy\n\n")
        f.write("Szczegółowe metryki klasyfikacji:\n")
        f.write(report)
        f.write("==================================================\n")
    print(f"[+] Zapisano tekstowy raport końcowy do: {report_filename}")
    
    print("\n" + "="*50 + "\n" + f"DOKŁADNOŚĆ SYSTEMU (OBRAZY): {acc:.2%}" + "\n" + "="*50)
    print(report)

    # Wykres: Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Oranges",
        xticklabels=["REAL_IMAGE", "AI_GENERATED"],
        yticklabels=["REAL_IMAGE", "AI_GENERATED"]
    )
    plt.title("Macierz Pomyłek (Image Confusion Matrix)")
    plt.ylabel("Wartość Rzeczywista")
    plt.xlabel("Wartość Przewidziana")
    plt.tight_layout()
    plt.savefig("image_confusion_matrix.png")
    print("[+] Wygenerowano wykres: image_confusion_matrix.png")
    plt.close()

    # Wykres: Krzywa ROC
    fpr, tpr, _ = roc_curve(y_true, y_prob_fake)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="orangered", lw=2, label=f"Krzywa ROC (AUC = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate (1 - Specyficzność)")
    plt.ylabel("True Positive Rate (Czułość)")
    plt.title("Krzywa ROC (Detekcja Obrazu)")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig("image_roc_curve.png")
    print("[+] Wygenerowano wykres: image_roc_curve.png")
    plt.close()

if __name__ == "__main__":
    setup_test_guild()
    test_set = prepare_dataset(SAMPLE_SIZE)
    
    # Przygotowujemy tymczasowy folder i zapisujemy do niego obrazy
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    print("[*] Zapisywanie obrazów do katalogu tymczasowego...")
    for idx, item in enumerate(test_set):
        filename = f"img_{idx}.jpg"
        item["image"].save(os.path.join(TEMP_DIR, filename))
        item["local_filename"] = filename
        
    # Uruchamiamy lokalny serwer HTTP w tle na losowym wolnym porcie
    host = "127.0.0.1"
    port = find_free_port()
    handler_factory = partial(SimpleHTTPRequestHandler, directory=TEMP_DIR)
    server = HTTPServer((host, port), handler_factory)
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"[+] Uruchomiono asynchroniczny lokalny serwer HTTP na http://{host}:{port}/")
    
    # Wykonujemy testy
    raw_results = run_evaluation(test_set, host, port)
    
    # Wyłączamy serwer i sprzątamy folder
    print("[*] Zatrzymywanie lokalnego serwera i czyszczenie plików tymczasowych...")
    server.shutdown()
    server.server_close()
    shutil.rmtree(TEMP_DIR)
    
    # Analizujemy i zapisujemy wyniki
    process_and_save_results(raw_results)