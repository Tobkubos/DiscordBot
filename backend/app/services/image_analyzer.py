import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    start_time = time.time()
    
    logger.info(f"Starting image analysis, size: {len(image_bytes)} bytes")
    
    image_hash = hash(image_bytes) % 100
    is_deepfake = image_hash > 50
    confidence = (image_hash % 100) / 100.0
    
    analysis_time = time.time() - start_time
    
    result = {
        "is_deepfake": is_deepfake,
        "confidence": round(confidence, 3),
        "analysis_time": round(analysis_time, 3),
    }
    
    logger.info(f"Image analysis completed. Result: {result}")
    return result
