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
    Ręcznie wczytuje plik .env do os.environ.
    """
    if os.getenv("GEMINI_API_KEY"):
        return

    possible_paths = [
        Path(".env"),                                      # Bieżący folder roboczy
        Path("backend/.env"),                              # Folder backend
        Path(__file__).resolve().parent.parent.parent / ".env"  # Ścieżka relatywna do serwisu
    ]

    for path_obj in possible_paths:
        resolved_path = path_obj.resolve()
        if resolved_path.exists():
            try:
                with open(resolved_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            os.environ[key.strip()] = val.strip().strip("'\"")
                break
            except Exception as e:
                logger.warning(f"Błąd odczytu .env: {e}")

# Uruchamiamy wczytywanie środowiska przy imporcie tego serwisu
load_env_fallback()


def search_web_with_fallback(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Próbuje pobrać wyniki z całego internetu (DuckDuckGo POST).
    W razie blokady IP automatycznie i cicho przełącza się na stabilne i darmowe Wikipedia API.
    Gwarantuje wyświetlenie źródeł bez żadnych opłat, rejestracji i kart płatniczych.
    """
    # 1. PRÓBA OGÓLNEGO INTERNETU (DuckDuckGo POST)
    logger.info(f"Wyszukiwanie w sieci (DuckDuckGo POST) dla zapytania: {query}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    url = "https://html.duckduckgo.com/html/"
    
    try:
        with httpx.Client(headers=headers, timeout=8.0, follow_redirects=True) as client:
            response = client.post(url, data={"q": query})
            response.raise_for_status()
            html = response.text
            
            # Sprawdzamy czy nie wystąpiła blokada IP
            lower_html = html.lower()
            if "ddg-captcha" in lower_html or "security check" in lower_html or "robot" in lower_html:
                print("⚠️  [BLOKADA IP] DuckDuckGo wykryło bota. Automatyczne przełączanie na darmowe Wikipedia API...")
                raise Exception("CAPTCHA Block")
                
            # Parsowanie linków
            links = []
            for m in re.finditer(r'<a\s+[^>]*href=["\'](?P<url>[^"\']+)["\'][^>]*>(?P<title>.*?)</a>', html, re.IGNORECASE | re.DOTALL):
                tag_full_text = m.group(0)
                if "result__a" in tag_full_text:
                    links.append({
                        "url": m.group("url"),
                        "title": m.group("title")
                    })
            
            # Parsowanie opisów (snippetów)
            snippets = []
            for m in re.finditer(r'<a\s+[^>]*href=["\'](?P<url>[^"\']+)["\'][^>]*>(?P<snippet>.*?)</a>', html, re.IGNORECASE | re.DOTALL):
                tag_full_text = m.group(0)
                if "result__snippet" in tag_full_text:
                    snippets.append(m.group("snippet"))
            
            results = []
            for i in range(min(len(links), max_results)):
                raw_url = links[i]["url"]
                raw_title = links[i]["title"]
                
                # Dekodowanie przekierowania
                clean_url = raw_url
                if "uddg=" in raw_url:
                    match = re.search(r'uddg=([^&]+)', raw_url)
                    if match:
                        clean_url = urllib.parse.unquote(match.group(1))
                
                if clean_url.startswith("//"):
                    clean_url = "https:" + clean_url
                elif clean_url.startswith("/"):
                    clean_url = "https://duckduckgo.com" + clean_url
                
                clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
                
                clean_snippet = "Brak opisu."
                if i < len(snippets):
                    clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                
                results.append({
                    "title": clean_title,
                    "url": clean_url,
                    "snippet": clean_snippet
                })
            
            if results:
                print(f"✅ [WYSZUKIWANIE] Pobrano {len(results)} wyników z ogólnego internetu.")
                return results
                
    except Exception as e:
        logger.warning(f"Ogólne wyszukiwanie nie powiodło się (prawdopodobnie blokada IP): {e}")

    # 2. PRÓBA AWARYJNA (Wikipedia API - 100% stabilna, darmowa, bez kluczy i bez blokad)
    logger.info("Uruchamianie stabilnego wyszukiwania awaryjnego w Wikipedii...")
    wiki_url = "https://pl.wikipedia.org/w/api.php"
    wiki_params = {
        "action": "opensearch",
        "search": query,
        "limit": max_results,
        "namespace": 0,
        "format": "json"
    }
    
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(wiki_url, params=wiki_params)
            response.raise_for_status()
            data = response.json()
            
            titles = data[1]
            descriptions = data[2]
            urls = data[3]
            
            results = []
            for i in range(len(titles)):
                results.append({
                    "title": titles[i],
                    "url": urls[i],
                    "snippet": descriptions[i] if descriptions[i] else "Artykuł w darmowej bazie wiedzy encyklopedii Wikipedia."
                })
            
            if results:
                print(f"✅ [WYSZUKIWANIE FALLBACK] Pobrano {len(results)} źródeł z Wikipedii.")
                return results
    except Exception as e:
        logger.error(f"Wyszukiwanie awaryjne w Wikipedii również się nie powiodło: {e}", exc_info=True)
        
    return []


async def analyze_with_gemini_grounding(statement: str) -> Dict[str, Any]:
    """
    Analizuje stwierdzenie, pobierając najnowsze wyniki z sieci (lub awaryjnej Wikipedii),
    a następnie przekazując je do modelu Gemini 2.5-Flash.
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
    
    # 1. Pobieramy źródła (z ogólnego sieci lub awaryjnie z Wikipedii)
    web_results = search_web_with_fallback(statement, max_results=3)
    
    if not web_results:
        return {
            "verdict": "SPORNE",
            "explanation": "Nie udało się pobrać wyników wyszukiwania z sieci ani bazy wiedzy. Sprawdź połączenie internetowe na serwerze.",
            "confidence": 0.0,
            "sources": []
        }
        
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
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )
        
        raw_text = response.text.strip()
        logger.info(f"Surowa odpowiedź Gemini: {raw_text}")
        
        verdict = "SPORNE"
        verdict_match = re.search(r"VERDICT:\s*(PRAWDA|FAŁSZ|SPORNE)", raw_text, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            
        explanation = "Nie udało się wygenerować uzasadnienia."
        explanation_match = re.search(r"EXPLANATION:\s*(.*)", raw_text, re.DOTALL | re.IGNORECASE)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            
        return {
            "verdict": verdict,
            "explanation": explanation,
            "confidence": 0.95 if verdict in ["PRAWDA", "FAŁSZ"] else 0.5,
            "sources": web_results
        }
        
    except Exception as e:
        logger.error(f"Błąd analizy Gemini API: {e}", exc_info=True)
        return {
            "verdict": "SPORNE",
            "explanation": f"Wystąpił błąd komunikacji z modelem językowym: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }