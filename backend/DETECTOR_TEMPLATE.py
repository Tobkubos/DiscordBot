"""
Template for creating new detector models.

Copy this file and implement the detect() method with your custom ML logic.
Then register it in app/services/detector/__init__.py

Example:
    # Copy this file as app/services/detector/mydetector.py
    # Modify the class and model_name
    # Add to get_detector() in __init__.py
"""

import logging
import time
from typing import Dict, Any

from app.services.detector.base import BaseDetector

logger = logging.getLogger(__name__)


class MyDetector(BaseDetector):
    """
    Template detector implementation.
    
    Replace 'MyDetector' with your detector name.
    """
    
    def __init__(self):
        """Initialize the detector."""
        # Change 'mydetector' to your model name
        super().__init__("mydetector")
    
    async def detect(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if file is a deepfake.
        
        Args:
            file_bytes: The file contents as bytes
            
        Returns:
            Dictionary with:
            - is_deepfake: Boolean
            - confidence: Float between 0.0 and 1.0
            - analysis_time: Float in seconds
        """
        logger.info(f"Starting detection with {self.model_name}...")
        
        start_time = time.time()
        
        # ========================================
        # TODO: Implement your ML model logic here
        # ========================================
        # Example:
        # 1. Preprocess file_bytes if needed
        # 2. Load your ML model
        # 3. Run inference
        # 4. Post-process results
        
        # For now, return placeholder results
        is_deepfake = True
        confidence = 0.85
        
        analysis_time = time.time() - start_time
        
        result = {
            "is_deepfake": is_deepfake,
            "confidence": round(confidence, 3),
            "analysis_time": round(analysis_time, 3),
        }
        
        logger.info(f"Detection completed. Result: {result}")
        return result


# =====================================================
# REGISTRATION INSTRUCTIONS:
# =====================================================
# 
# 1. Save this file as: app/services/detector/mydetector.py
# 
# 2. Update app/services/detector/__init__.py:
#    
#    from app.services.detector.mydetector import MyDetector
#    
#    def get_detector(model_name: str = "mock") -> BaseDetector:
#        detectors = {
#            "mock": MockDetector,
#            "mydetector": MyDetector,  # ADD THIS LINE
#        }
#        # ... rest of function
# 
# 3. Update .env.example:
#    
#    DEFAULT_DETECTOR_MODEL=mydetector
# 
# 4. Test your detector:
#    
#    POST /analyze
#    {
#        "file_url": "https://example.com/video.mp4",
#        "model": "mydetector"
#    }
#
# =====================================================
