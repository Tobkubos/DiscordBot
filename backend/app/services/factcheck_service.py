import logging
import json
import re
import os
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List
import httpx
import google.generativeai as genai

logger = logging.getLogger(__name__)

def load_env_fallback():
    """
    Ręcznie wczytuje plik .env do os.environ z pełną diagnostyką w konsoli.
    """
    if os.getenv("GEMINI_API_KEY"):
        return

    possible_paths = [
        Path(".env"),                                      # Bieżący folder roboczy
        Path("backend/.env"),                              # Folder backend
        Path(__file__).resolve().parent.parent.parent / ".env"  # Ścieżka relatywna do serwisu
    ]

    print(f"\n🔍 [DIAGNOSTYKA .ENV] Bieżący katalog roboczy (CWD): {os.getcwd()}")
    
    found_any = False
    for path_obj in possible_paths:
        resolved_path = path_obj.resolve()
        exists = resolved_path.exists()
        print(f"👉 Sprawdzam ścieżkę: {resolved_path} -> [Znaleziono: {'TAK' if exists else 'NIE'}]")
        
        if exists:
            found_any = True
            print(f"📖 Próba wczytania pliku: {resolved_path}")
            try:
                loaded_keys = []
                with open(resolved_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            k_clean = key.strip()
                            v_clean = val.strip().strip("'\"")
                            os.environ[k_clean] = v_clean
                            loaded_keys.append(k_clean)
                print(f"✅ Pomyślnie wczytano klucze z pliku: {loaded_keys}")
                break
            except Exception as e:
                print(f"❌ Błąd odczytu pliku .env: {e}")
                
    if not found_any:
        print("❌ Nie znaleziono pliku .env w żadnej z badanych lokalizacji!")
        
    final_key = os.getenv("GEMINI_API_KEY")
    print(f"🔑 Status GEMINI_API_KEY: {'ZNAJDZIONO (zaczyna się od: ' + final_key[:6] + '...)' if final_key else 'NIE ZNAJDZIONO!'}\n")

# Uruchamiamy wczytywanie środowiska przy imporcie tego serwisu
load_env_fallback()


def search_web_manually(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Ręcznie wyszukuje informacje w DuckDuckGo HTML przy użyciu biblioteki httpx.
    Bypassuje błędy i limity Google API, gwarantując pobranie źródeł i linków.
    """
    logger.info(f"Ręczne wyszukiwanie w sieci dla zapytania: {query}")
    
    # Standardowe nagłówki przeglądarki, aby zapobiec blokowaniu przez DDG
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://html.duckduckgo.com/html/"
    
    try:
        with httpx.Client(headers=headers, timeout=10.0) as client:
            response = client.get(url, params={"q": query})
            response.raise_for_status()
            html = response.text
            
            # Regex do znajdowania linków i tytułów
            link_pattern = re.compile(
                r'<a[^>]*class="result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                re.IGNORECASE | re.DOTALL
            )
            # Regex do znajdowania snippetów (krótkich opisów)
            snippet_pattern = re.compile(
                r'<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
                re.IGNORECASE | re.DOTALL
            )
            
            links = link_pattern.findall(html)
            snippets = snippet_pattern.findall(html)
            
            results = []
            for i in range(min(len(links), max_results)):
                raw_url, raw_title = links[i]
                
                # Dekodowanie linku przekierowującego DuckDuckGo
                clean_url = raw_url
                if "uddg=" in raw_url:
                    match = re.search(r'uddg=([^&]+)', raw_url)
                    if match:
                        clean_url = urllib.parse.unquote(match.group(1))
                
                # Upewniamy się, że link ma poprawny protokół
                if clean_url.startswith("//"):
                    clean_url = "https:" + clean_url
                elif clean_url.startswith("/"):
                    clean_url = "https://duckduckgo.com" + clean_url
                
                # Oczyszczenie tekstu z tagów HTML
                clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
                
                clean_snippet = "Brak opisu."
                if i < len(snippets):
                    clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                
                results.append({
                    "title": clean_title,
                    "url": clean_url,
                    "snippet": clean_snippet
                })
            
            logger.info(f"Pomyślnie wyszukano {len(results)} źródeł z sieci.")
            return results
            
    except Exception as e:
        logger.error(f"Ręczne wyszukiwanie DuckDuckGo nie powiodło się: {e}", exc_info=True)
        return []


async def analyze_with_gemini_grounding(statement: str) -> Dict[str, Any]:
    """
    Analizuje stwierdzenie, najpierw pobierając najnowsze wyniki z sieci,
    a następnie przekazując je jako kontekst do modelu Gemini.
    Gwarantuje to stabilne działanie źródeł na Discordzie.
    """
    load_env_fallback()
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("Brak klucza GEMINI_API_KEY w środowisku systemowym!")
        return {
            "verdict": "SPORNE",
            "explanation": "Błąd backendu: Brak skonfigurowanego klucza GEMINI_API_KEY w pliku .env.",
            "confidence": 0.0,
            "sources": []
        }
        
    genai.configure(api_key=api_key)
    
    # 1. Pobieramy źródła ręcznie (bypasując błędy API Google)
    web_results = search_web_manually(statement, max_results=3)
    
    if not web_results:
        return {
            "verdict": "SPORNE",
            "explanation": "Wyszukiwarka nie zwróciła żadnych wyników w sieci dla tego stwierdzenia, co uniemożliwia weryfikację.",
            "confidence": 0.0,
            "sources": []
        }
        
    # Formatowanie pobranych źródeł do formy czytelnej dla modelu LLM
    sources_text = ""
    for idx, r in enumerate(web_results, start=1):
        sources_text += f"[{idx}] Tytuł: {r['title']}\nTreść: {r['snippet']}\n\n"
        
    prompt = f"""Jesteś zaawansowanym asystentem do weryfikacji faktów (fact-checking).
Przeanalizuj poniższe stwierdzenie na podstawie dostarczonych aktualnych wyników wyszukiwania z internetu.

STWIERDZENIE DO WERYFIKACJI:
"{statement}"

DOKUMENTY Z WYSZUKIWARKI:
{sources_text}

Twoja odpowiedź musi ściśle odpowiadać poniższemu szablonowi (nie dodawaj żadnych innych komentarzy ani wstępów):

VERDICT: [Wpisz PRAWDA, FAŁSZ lub SPORNE]
EXPLANATION: [Wpisz zwięzłe (2-4 zdania), merytoryczne i obiektywne uzasadnienie werdyktu w języku polskim, wyjaśniające co mówią najnowsze fakty na podstawie dostarczonych dokumentów.]

Zasady oceny:
- VERDICT: PRAWDA (dostarczone dokumenty w pełni potwierdzają to stwierdzenie)
- VERDICT: FAŁSZ (dostarczone dokumenty jednoznacznie zaprzeczają temu stwierdzeniu)
- VERDICT: SPORNE (informacje są sprzeczne, opinie podzielone lub brak wystarczających dowodów w dokumentach)
"""

    try:
        # Używamy standardowego modelu bez wbudowanego "google_search" w tools,
        # ponieważ sami zaimplementowaliśmy bezpieczny system RAG.
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )
        
        raw_text = response.text.strip()
        logger.info(f"Surowa odpowiedź Gemini: {raw_text}")
        
        # Parsowanie werdyktu za pomocą Regex
        verdict = "SPORNE"
        verdict_match = re.search(r"VERDICT:\s*(PRAWDA|FAŁSZ|SPORNE)", raw_text, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            
        # Parsowanie uzasadnienia za pomocą Regex
        explanation = "Nie udało się wygenerować uzasadnienia."
        explanation_match = re.search(r"EXPLANATION:\s*(.*)", raw_text, re.DOTALL | re.IGNORECASE)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            
        return {
            "verdict": verdict,
            "explanation": explanation,
            "confidence": 0.95 if verdict in ["PRAWDA", "FAŁSZ"] else 0.5,
            "sources": web_results  # Zwracamy dokładnie te źródła, które sami wyszukaliśmy!
        }
        
    except Exception as e:
        logger.error(f"Błąd analizy Gemini API: {e}", exc_info=True)
        return {
            "verdict": "SPORNE",
            "explanation": f"Wystąpił błąd komunikacji z modelem językowym: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }