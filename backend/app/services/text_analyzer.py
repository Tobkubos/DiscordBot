import logging
import time
import gc
from typing import Dict, Any

from app.config_manager import get_active_text_model
from app.utils.exceptions import SetupRequiredError
from transformers import pipeline
# Importujesz helpery z Kroku 2:
# from config_manager import get_active_text_model 

logger = logging.getLogger(__name__)

# Przechowujemy nazwę aktualnie załadowanego modelu oraz sam obiekt klasyfikatora
_loaded_model_name = None
_text_classifier = None

def _load_model(target_model_name: str):
    global _text_classifier, _loaded_model_name
    
    # Jeśli model w pamięci jest tym, którego potrzebujemy, po prostu go zwracamy
    if _text_classifier is not None and _loaded_model_name == target_model_name:
        return _text_classifier
        
    logger.info(f"Wymagana zmiana modelu. Obecny w RAM: {_loaded_model_name}, Nowy: {target_model_name}")
    
    # Zwalnianie pamięci po poprzednim modelu
    _text_classifier = None
    gc.collect()
    
    logger.info(f"Ładowanie modelu text detector: {target_model_name}...")
    _text_classifier = pipeline(
        "text-classification",
        model=target_model_name,
        device=-1  # -1 oznacza CPU, jeśli masz GPU ustaw np. 0
    )
    _loaded_model_name = target_model_name
    logger.info(f"Model {target_model_name} został pomyślnie załadowany.")
    
    return _text_classifier

async def analyze_text(text: str, guild_id: str) -> Dict[str, Any]:
    start_time = time.time()
    
    # Pobranie aktywnego modelu dla danej gildii
    active_model = get_active_text_model(guild_id)
    
    # BLOKADA: Jeżeli model to 'none' lub brak konfiguracji, natychmiast wyrzucamy błąd
    if not active_model:
        logger.warning(f"Zablokowano zapytanie! Serwer {guild_id} nie ma skonfigurowanego modelu.")
        raise SetupRequiredError(
            f"Serwer o ID '{guild_id}' nie został jeszcze skonfigurowany. "
            "Użyj komendy setup na Discordzie przed wykonaniem analizy."
        )

    logger.info(f"Rozpoczęcie analizy tekstu dla serwera {guild_id} przy użyciu modelu: {active_model}")
    
    classifier = _load_model(active_model)
    result = classifier(text)
    
    label = result[0]["label"]
    score = result[0]["score"]
    
    is_deepfake = label.lower() in ["fake", "ai", "chatgpt", "label_1", "machine-generated"]
    confidence = score
    analysis_time = time.time() - start_time
    
    response = {
        "is_deepfake": is_deepfake,
        "confidence": round(confidence, 3),
        "analysis_time": round(analysis_time, 3),
        "used_model": active_model,
    }
    
    logger.info(f"Analiza zakończona sukcesem dla serwera {guild_id}.")
    return response