import io
import logging
import time
from typing import Dict, Any
from PIL import Image
from transformers import pipeline

logger = logging.getLogger(__name__)

_image_classifier = None

def _load_model():
    global _image_classifier
    if _image_classifier is None:
        logger.info("Loading capcheck/ai-image-detection model...")
        _image_classifier = pipeline(
            "image-classification",
            model="capcheck/ai-image-detection",
            device=-1 
        )
        logger.info("Image detector model loaded successfully")
    return _image_classifier

async def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    start_time = time.time()
    
    logger.info(f"Starting image analysis, size: {len(image_bytes)} bytes")
    
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Failed to parse image bytes: {str(e)}")
        raise ValueError("Invalid image format or corrupted bytes") from e
    
    classifier = _load_model()
    
    result = classifier(image)
    
    label = result[0]["label"]
    score = result[0]["score"]
    
    is_deepfake = label.lower() == "fake"
    confidence = score
    
    analysis_time = time.time() - start_time
    
    response = {
        "is_deepfake": is_deepfake,
        "confidence": round(confidence, 3),
        "analysis_time": round(analysis_time, 3),
    }
    
    logger.info(f"Image analysis completed. Result: {response}")
    return response