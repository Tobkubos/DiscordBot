import logging
import time
from typing import Dict, Any
from transformers import pipeline

logger = logging.getLogger(__name__)

_text_classifier = None

def _load_model():
    global _text_classifier
    if _text_classifier is None:
        logger.info("Loading XLM-RoBERTa text detector model...")
        _text_classifier = pipeline(
            "text-classification",
            model="yaya36095/xlm-roberta-text-detector",
            device=-1
        )
        logger.info("Text detector model loaded successfully")
    return _text_classifier

async def analyze_text(text: str) -> Dict[str, Any]:
    start_time = time.time()
    
    logger.info(f"Starting text analysis, length: {len(text)} chars")
    
    classifier = _load_model()
    result = classifier(text)
    
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
    
    logger.info(f"Text analysis completed. Result: {response}")
    return response
