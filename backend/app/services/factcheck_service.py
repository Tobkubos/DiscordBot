import logging
import json
import re
import os
from typing import Dict, Any, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

async def analyze_with_gemini_grounding(statement: str) -> Dict[str, Any]:
    """
    Analizuje stwierdzenie, automatycznie przeszukując internet za pomocą 
    wbudowanego w Gemini narzędzia Google Search Grounding.
    Rozwiązuje to całkowicie problemy z blokowaniem i timeoutami wyszukiwarek.
    """
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
    
    # Ponieważ nie możemy łączyć narzędzia wyszukiwania (Google Search) z trybem JSON w konfiguracji API,
    # wymuszamy strukturę JSON za pomocą precyzyjnego promptu systemowego.
    prompt = f"""Jesteś zaawansowanym asystentem do weryfikacji faktów (fact-checking).
Przeanalizuj poniższe stwierdzenie, korzystając z wyszukiwarki Google (masz do niej dostęp jako narzędzie), aby zweryfikować jego prawdziwość w czasie rzeczywistym.

STWIERDZENIE DO WERYFIKACJI:
"{statement}"

Twoja odpowiedź musi być wyłącznie poprawnym obiektem JSON (bez bloków kodu typu ```json, bez dodatkowego tekstu na początku ani na końcu). 
Format JSON:
{{
  "verdict": "PRAWDA" lub "FAŁSZ" lub "SPORNE",
  "explanation": "Zwięzłe (2-4 zdania), merytoryczne i obiektywne uzasadnienie werdyktu w języku polskim, wyjaśniające co mówią fakty."
}}

Wskazówki do werdyktu:
- "PRAWDA": Najnowsze fakty i wiarygodne źródła w pełni potwierdzają to stwierdzenie.
- "FAŁSZ": Fakty jednoznacznie zaprzeczają temu stwierdzeniu.
- "SPORNE": Informacje w sieci są sprzeczne, jest to kwestia opinii lub brak jednoznacznych dowodów.
"""

    try:
        # Inicjalizacja modelu z wbudowanym narzędziem Google Search
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=[{"google_search": {}}]  # Włączenie Google Search Grounding
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0  # Niska temperatura chroni przed zmyślaniem (halucynacjami)
            )
        )
        
        raw_text = response.text.strip()
        logger.info(f"Surowa odpowiedź Gemini: {raw_text}")
        
        # Wyczyszczenie tekstu z ewentualnych znaczników markdown ```json ... ```
        if raw_text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
                
        result_json = json.loads(raw_text)
        
        # Wyciąganie realnych źródeł (linków i tytułów), z których skorzystał model
        sources = []
        candidate = response.candidates[0]
        metadata = getattr(candidate, "grounding_metadata", None)
        
        if metadata and getattr(metadata, "grounding_chunks", None):
            for chunk in metadata.grounding_chunks:
                if chunk.web:
                    sources.append({
                        "title": chunk.web.title,
                        "url": chunk.web.uri,
                        "snippet": "Źródło zweryfikowane bezpośrednio przez wyszukiwarkę Google."
                    })
                    
        return {
            "verdict": result_json.get("verdict", "SPORNE"),
            "explanation": result_json.get("explanation", "Brak uzasadnienia."),
            "confidence": 0.95 if result_json.get("verdict") in ["PRAWDA", "FAŁSZ"] else 0.5,
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Błąd analizy Gemini Grounding API: {e}", exc_info=True)
        return {
            "verdict": "SPORNE",
            "explanation": f"Wystąpił błąd komunikacji z modelem językowym: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }