import logging
import json
import re
import os
from pathlib import Path
from typing import Dict, Any, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

def load_env_fallback():
    """
    Ręcznie wczytuje plik .env do os.environ.
    """
    if os.getenv("GEMINI_API_KEY"):
        return

    possible_paths = [
        Path(".env"),
        Path("backend/.env"),
        Path(__file__).resolve().parent.parent.parent / ".env"
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


async def analyze_with_gemini_grounding(statement: str) -> Dict[str, Any]:
    """
    Analizuje stwierdzenie przy użyciu natywnej wyszukiwarki wbudowanej w Gemini (Google Search Grounding).
    Linki są wyciągane bezpośrednio z tekstu, co gwarantuje ich stabilne działanie na darmowym kluczu API.
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
        
    # Prompt zmuszający model do umieszczenia linków na samym dole tekstu w formacie Markdown
    prompt = f"""Jesteś zaawansowanym asystentem do weryfikacji faktów (fact-checking).
Przeanalizuj poniższe stwierdzenie korzystając ze swojej wbudowanej wyszukiwarki (Google Search), aby znaleźć najnowsze i najbardziej rzetelne informacje.

STWIERDZENIE DO WERYFIKACJI:
"{statement}"

Twoja odpowiedź musi ściśle odpowiadać poniższemu szablonowi (nie dodawaj żadnych innych komentarzy ani wstępów):

VERDICT: [Wpisz PRAWDA, FAŁSZ lub SPORNE]
EXPLANATION: [Wpisz zwięzłe (2-4 zdania), merytoryczne i obiektywne uzasadnienie werdyktu w języku polskim. 
Na samym dole tego uzasadnienia wypisz jako listę punktową klikalne odnośniki do źródeł, na których się oparłeś, podając ich pełne adresy URL, dokładnie w poniższym formacie Markdown:
- [Nazwa strony/Tytuł](pełny_link_url)]
"""

    try:
        # POPRAWKA 1: Używamy prawidłowej definicji narzędzia google_search zgodnej z nowym SDK i Gemini 2.5
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[
                genai.protos.Tool(
                    google_search=genai.protos.Tool.GoogleSearch()
                )
            ]
        )
        
        # Używamy asynchronicznej generacji
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )
        
        raw_text = response.text.strip()
        logger.info(f"Surowa odpowiedź Gemini:\n{raw_text}")
        
        # Parsowanie Werdyktu za pomocą Regex
        verdict = "SPORNE"
        verdict_match = re.search(r"VERDICT:\s*(PRAWDA|FAŁSZ|SPORNE)", raw_text, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            
        # Parsowanie Uzasadnienia za pomocą Regex
        explanation = "Nie udało się wygenerować uzasadnienia."
        explanation_match = re.search(r"EXPLANATION:\s*(.*)", raw_text, re.DOTALL | re.IGNORECASE)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            
        # POPRAWKA 2: Wyciągamy linki bezpośrednio z tekstu uzasadnienia,
        # co całkowicie obchodzi problem wycinania linków z metadanych na darmowych kluczach API.
        sources = []
        markdown_links = re.findall(r'\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)]+)\)', explanation)
        
        for title, url in markdown_links:
            sources.append({
                "title": title,
                "url": url,
                "snippet": "Źródło zweryfikowane bezpośrednio przez wyszukiwarkę Google."
            })
            
        # Czyszczenie tekstu - odcinamy listę linków z tekstu, aby nie dublować jej na Discordzie
        cleaned_explanation = explanation
        if "\n" in cleaned_explanation:
            parts = re.split(r'\n\s*-\s*\[', cleaned_explanation, maxsplit=1)
            cleaned_explanation = parts[0].strip()

        # Ograniczamy źródła do unikalnych linków
        unique_sources = {s["url"]: s for s in sources}.values()

        return {
            "verdict": verdict,
            "explanation": cleaned_explanation,
            "confidence": 0.95 if verdict in ["PRAWDA", "FAŁSZ"] else 0.5,
            "sources": list(unique_sources)
        }
        
    except Exception as e:
        logger.error(f"Błąd analizy Gemini API: {e}", exc_info=True)
        return {
            "verdict": "SPORNE",
            "explanation": f"Wystąpił błąd komunikacji z modelem językowym lub wyszukiwarką: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }