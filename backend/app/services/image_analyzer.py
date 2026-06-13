import io
import logging
import time
import gc
from typing import Dict, Any
from PIL import Image
from transformers import pipeline

# Importujemy helper do konfiguracji oraz wyjątek braku konfiguracji
from app.config_manager import get_active_image_model
from app.utils.exceptions import SetupRequiredError

logger = logging.getLogger(__name__)

# Przechowujemy referencje do aktualnie załadowanego modelu obrazów
_loaded_model_name = None
_image_classifier = None

def _load_model(target_model_name: str):
    global _image_classifier, _loaded_model_name
    
    # Jeśli model o tej nazwie jest już załadowany w pamięci, używamy go ponownie
    if _image_classifier is not None and _loaded_model_name == target_model_name:
        return _image_classifier
        
    logger.info(f"Wymagana zmiana modelu obrazu. Obecny w RAM: {_loaded_model_name}, Nowy: {target_model_name}")
    
    # Czyszczenie pamięci po poprzednim modelu obrazów
    _image_classifier = None
    gc.collect()
    
    logger.info(f"Ładowanie modelu image detector: {target_model_name}...")
    _image_classifier = pipeline(
        "image-classification",
        model=target_model_name,
        device=-1  # -1 oznacza CPU
    )
    _loaded_model_name = target_model_name
    logger.info(f"Model {target_model_name} został pomyślnie załadowany.")
    
    return _image_classifier

async def analyze_image(image_bytes: bytes, guild_id: str) -> Dict[str, Any]:
    start_time = time.time()
    
    # 1. Sprawdzamy konfigurację modelu dla danego serwera Discord
    active_model = get_active_image_model(guild_id)
    
    # BLOKADA: Jeżeli model to 'none' lub brak konfiguracji, natychmiast przerywamy i zgłaszamy błąd
    if not active_model:
        logger.warning(f"Zablokowano zapytanie! Serwer {guild_id} nie ma skonfigurowanego modelu dla obrazów.")
        raise SetupRequiredError(
            f"Serwer o ID '{guild_id}' nie został jeszcze skonfigurowany pod kątem analizy obrazów. "
            "Użyj komendy setup na Discordzie przed wykonaniem analizy."
        )

    logger.info(f"Starting image analysis for guild: {guild_id}, model: {active_model}, size: {len(image_bytes)} bytes")
    
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Failed to parse image bytes: {str(e)}")
        raise ValueError("Invalid image format or corrupted bytes") from e
    
    # 2. Dynamicznie pobieramy/ładujemy wskazany model
    classifier = _load_model(active_model)
    result = classifier(image)
    
    label = result[0]["label"]
    score = result[0]["score"]
    
    # Dostosowanie do najczęstszych etykiet fałszywych obrazów (np. "fake", "ai", "synthetic")
    is_deepfake = label.lower() in ["fake", "ai", "synthetic", "label_1"]
    confidence = score
    
    analysis_time = time.time() - start_time
    
    response = {
        "is_deepfake": is_deepfake,
        "confidence": round(confidence, 3),
        "analysis_time": round(analysis_time, 3),
        "used_model": active_model,
    }
    
    logger.info(f"Image analysis completed. Result: {response}")
    return response