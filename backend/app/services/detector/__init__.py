"""Detector models for deepfake detection."""

from app.services.detector.base import BaseDetector
from app.services.detector.mock import MockDetector

__all__ = ["BaseDetector", "MockDetector", "get_detector"]


def get_detector(model_name: str = "mock") -> BaseDetector:
    """
    Factory function to get detector instance by model name.
    
    Args:
        model_name: Name of the detector model
        
    Returns:
        Instance of the requested detector
        
    Raises:
        ValueError: If model is not supported
    """
    detectors = {
        "mock": MockDetector,
        # Future models:
        # "deepseek": DeepseekDetector,
        # "openai": OpenAIDetector,
        # "huggingface": HuggingFaceDetector,
    }
    
    if model_name not in detectors:
        available = ", ".join(detectors.keys())
        raise ValueError(
            f"Detector model '{model_name}' is not supported. "
            f"Available models: {available}"
        )
    
    return detectors[model_name]()
