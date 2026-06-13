import io
import logging
import time
import gc
from typing import Dict, Any
from PIL import Image
from transformers import pipeline

from app.config_manager import get_active_image_model, is_multi_model_enabled
from app.core.config import get_settings
from app.utils.exceptions import SetupRequiredError

logger = logging.getLogger(__name__)

_loaded_classifiers = {}

def _load_model(target_model_name: str):
    global _loaded_classifiers
    
    if target_model_name in _loaded_classifiers:
        return _loaded_classifiers[target_model_name]
        
    logger.info(f"Model {target_model_name} nie jest załadowany. Ładowanie do RAM...")
    
    gc.collect()
    _loaded_classifiers[target_model_name] = pipeline(
        "image-classification",
        model=target_model_name,
        device=-1
    )
    logger.info(f"Model {target_model_name} został pomyślnie załadowany.")
    
    return _loaded_classifiers[target_model_name]

async def analyze_image(image_bytes: bytes, guild_id: str) -> Dict[str, Any]:
    start_time = time.time()
    settings = get_settings()
    
    multi_model_active = is_multi_model_enabled(guild_id)
    
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Failed to parse image bytes: {str(e)}")
        raise ValueError("Invalid image format or corrupted bytes") from e

    if multi_model_active:
        models_to_run = settings.AVAILABLE_MODELS.get("image", [])
        if not models_to_run:
            raise ValueError("Brak zdefiniowanych modeli obrazów w ustawieniach systemu.")
            
        logger.info(f"Wielomodelowa analiza obrazu dla serwera {guild_id} ({len(models_to_run)} modeli)")
        
        individual_results = []
        for m in models_to_run:
            try:
                classifier = _load_model(m)
                result = classifier(image)
                label = result[0]["label"]
                score = result[0]["score"]
                is_fake = label.lower() in ["fake", "ai", "synthetic", "label_1"]
                
                individual_results.append({
                    "model": m,
                    "is_deepfake": is_fake,
                    "confidence": round(score, 3)
                })
            except Exception as e:
                logger.error(f"Błąd modelu {m} podczas wielomodelowej analizy obrazu: {e}")
                
        if not individual_results:
            raise ValueError("Żaden z modeli obrazów nie dokonał pomyślnej analizy.")
            
        fake_votes = sum(1 for r in individual_results if r["is_deepfake"])
        is_deepfake = fake_votes > (len(individual_results) / 2)
        
        confidence = sum(r["confidence"] for r in individual_results) / len(individual_results)
        analysis_time = time.time() - start_time
        
        return {
            "is_deepfake": is_deepfake,
            "confidence": round(confidence, 3),
            "analysis_time": round(analysis_time, 3),
            "used_model": "Multi-Model Workflow (Ensemble)",
            "details": individual_results
        }
        
    else:
        active_model = get_active_image_model(guild_id)
        if not active_model:
            logger.warning(f"Zablokowano zapytanie! Serwer {guild_id} nie ma skonfigurowanego modelu dla obrazów.")
            raise SetupRequiredError(
                f"Serwer o ID '{guild_id}' nie został jeszcze skonfigurowany pod kątem analizy obrazów. "
                "Użyj komendy setup na Discordzie przed wykonaniem analizy."
            )

        logger.info(f"Starting image analysis for guild: {guild_id}, model: {active_model}, size: {len(image_bytes)} bytes")
        
        classifier = _load_model(active_model)
        result = classifier(image)
        
        label = result[0]["label"]
        score = result[0]["score"]
        
        is_deepfake = label.lower() in ["fake", "ai", "synthetic", "label_1"]
        confidence = score
        analysis_time = time.time() - start_time
        
        return {
            "is_deepfake": is_deepfake,
            "confidence": round(confidence, 3),
            "analysis_time": round(analysis_time, 3),
            "used_model": active_model,
            "details": None
        }