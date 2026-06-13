import logging
import json
import re
import os
from typing import Dict, Any, List
from duckduckgo_search import DDGS
import google.generativeai as genai

logger = logging.getLogger(__name__)

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Przeszukuje internet bez limitów i bez kluczy API za pomocą DuckDuckGo."""
    logger.info(f"Wyszukiwanie w sieci dla zapytania: {query}")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            formatted_results = []
            for r in results:
                formatted_results.append({
                    "title": r.get("title", "Brak tytułu"),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "Brak opisu")
                })
            return formatted_results
    except Exception as e:
        logger.error(f"Błąd wyszukiwania DuckDuckGo: {e}", exc_info=True)
        return []

async def analyze_with_gemini(statement: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analizuje stwierdzenie na podstawie wyników wyszukiwania za pomocą Gemini API."""
    # Pobieramy klucz bezpośrednio ze środowiska lub .env
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("Brak klucza GEMINI_API_KEY w środowisku systemowym!")
        return {
            "verdict": "SPORNE",
            "explanation": "Błąd backendu: Brak skonfigurowanego klucza GEMINI_API_KEY w pliku .env.",
            "confidence": 0.0,
            "sources_used_indices": []
        }
        
    genai.configure(api_key=api_key)
    
    # Przygotowanie czytelnego tekstu ze źródłami dla LLM
    sources_text = ""
    for idx, s in enumerate(sources, start=1):
        sources_text += f"[{idx}] Tytuł: {s['title']}\nURL: {s['url']}\nTreść: {s['snippet']}\n\n"
        
    prompt = f"""Jesteś zaawansowanym asystentem do weryfikacji faktów (fact-checking).
Twoim zadaniem jest ocena, czy podane STWIERDZENIE jest prawdziwe, fałszywe czy sporne na podstawie dostarczonych WYNIKÓW WYSZUKIWANIA.

STWIERDZENIE DO WERYFIKACJI:
"{statement}"

WYNIKI WYSZUKIWANIA:
{sources_text}

Wygeneruj rzetelną analizę. Odpowiedz w języku polskim. Twoja odpowiedź MUSI być poprawnym, czystym obiektem JSON o następującym formacie (i niczym innym):
{{
  "verdict": "PRAWDA" lub "FAŁSZ" lub "SPORNE",
  "explanation": "Zwięzłe (2-4 zdania), merytoryczne i obiektywne uzasadnienie werdyktu w języku polskim wraz z odniesieniem do źródeł.",
  "confidence": 0.85,
  "sources_used_indices": [1, 3]
}}

Zasady oceny:
- "PRAWDA": Wyniki jednoznacznie potwierdzają to stwierdzenie.
- "FAŁSZ": Wyniki wykazują błąd, dezinformację lub bezpośrednio zaprzeczają stwierdzeniu.
- "SPORNE": Istnieją sprzeczne informacje, jest to kwestia opinii lub źródła nie dają jednoznacznej odpowiedzi.

Zwróć TYLKO czysty obiekt JSON. Nie dodawaj bloków kodu ```json ani żadnych komentarzy poza obiektem JSON."""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Niska temperatura chroni przed zmyślaniem (hallucination)
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        
        # Oczyszczenie formatowania markdown, gdyby model mimo wszystko go dodał
        if raw_text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
                
        return json.loads(raw_text)
    except Exception as e:
        logger.error(f"Błąd analizy Gemini API: {e}", exc_info=True)
        return {
            "verdict": "SPORNE",
            "explanation": f"Wystąpił błąd komunikacji z modelem językowym: {str(e)}",
            "confidence": 0.0,
            "sources_used_indices": []
        }