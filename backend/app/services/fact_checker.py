import logging
import os
import json
from groq import Groq
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Pobranie klucza z pliku .env
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

def search_duckduckgo(query: str, max_results: int = 3) -> str:
    """Szuka w Google/DuckDuckGo i zwraca połączony tekst."""
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return ""
        
        context = ""
        for r in results:
            context += f"Tytuł: {r.get('title')}\nTreść: {r.get('body')}\nŹródło: {r.get('href')}\n\n"
        return context
    except Exception as e:
        logger.error(f"Błąd wyszukiwarki: {e}")
        return ""

async def verify_facts(text: str) -> dict:
    """Główna funkcja fact-checkingu używająca Groq API."""
    logger.info(f"Rozpoczynam Fact-Check dla: {text[:50]}...")
    
    if not client:
        return {
            "verdict": "BŁĄD",
            "explanation": "Brak klucza GROQ_API_KEY na serwerze.", 
            "sources": []
        }

    search_context = search_duckduckgo(text)
    if not search_context:
         return {
            "verdict": "SPORNE",
            "explanation": "Nie znaleziono w sieci wiarygodnych informacji na ten temat.", 
            "sources": []
        }

    prompt = f"""
    Jesteś obiektywnym weryfikatorem faktów. 
    Oto informacje przed chwilą znalezione w internecie:
    {search_context}
    
    Na podstawie tych informacji oceń tezę: "{text}"
    
    Zwróć wynik jako czysty obiekt JSON.
    Wymagana struktura:
    {{
        "verdict": "PRAWDA" lub "FAŁSZ" lub "SPORNE",
        "explanation": "Krótkie uzasadnienie na bazie źródeł.",
        "sources": ["tutaj_wklej_url_z_dostarczonego_tekstu"]
    }}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(chat_completion.choices[0].message.content)
        
        # Zabezpieczenie przed pustymi źródłami
        if "sources" not in data or not isinstance(data["sources"], list):
            data["sources"] = []
            
        return data

    except Exception as e:
        logger.error(f"Błąd modelu AI: {e}")
        return {
            "verdict": "BŁĄD",
            "explanation": "Błąd podczas analizy danych przez AI.", 
            "sources": []
        }