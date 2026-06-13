"""Base detector class defining the interface for all detectors."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseDetector(ABC):
    """
    Abstract base class for deepfake detectors.
    
    All detector implementations should inherit from this class and implement
    the detect() method.
    """
    
    def __init__(self, model_name: str):
        """
        Initialize the detector.
        
        Args:
            model_name: Name of the detector model
        """
        self.model_name = model_name
    
    @abstractmethod
    async def detect(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if file is a deepfake.
        
        Args:
            file_bytes: The file contents as bytes
            
        Returns:
            Dictionary containing:
            - is_deepfake: Boolean indicating if file is a deepfake
            - confidence: Float between 0.0 and 1.0
            - analysis_time: Float representing processing time
        """
        pass
