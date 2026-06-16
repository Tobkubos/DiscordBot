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
    Ręcznie wczytuje plik .env do os.environ z pełną diagnostyką w konsoli.
    """
    if os.getenv("GEMINI_API_KEY"):
        return

    possible_paths = [
        Path(".env"),                                      # Bieżący folder roboczy                            # Folder backend
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


async def analyze_with_gemini_grounding(statement: str) -> Dict[str, Any]:
    """
    Analizuje stwierdzenie, automatycznie przeszukując internet za pomocą 
    wbudowanego w Gemini narzędzia Google Search Grounding.
    """
    # Upewniamy się, że środowisko jest załadowane
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
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[
                genai.protos.Tool(
                    google_search=genai.protos.Tool.GoogleSearch()
                )
            ]
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )
        
        raw_text = response.text.strip()
        logger.info(f"Surowa odpowiedź Gemini: {raw_text}")
        
        if raw_text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
                
        result_json = json.loads(raw_text)
        
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