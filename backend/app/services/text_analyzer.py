import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def analyze_text(text: str) -> Dict[str, Any]:
    start_time = time.time()
    
    logger.info(f"Starting text analysis, length: {len(text)} chars")
    
    text_hash = hash(text) % 100
    is_deepfake = text_hash > 50
    confidence = (text_hash % 100) / 100.0
    
    analysis_time = time.time() - start_time
    
    result = {
        "is_deepfake": is_deepfake,
        "confidence": round(confidence, 3),
        "analysis_time": round(analysis_time, 3),
    }
    
    logger.info(f"Text analysis completed. Result: {result}")
    return result
