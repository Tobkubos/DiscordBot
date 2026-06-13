"""Mock detector implementation for testing and development."""

import asyncio
import logging
import time
from typing import Dict, Any

from app.services.detector.base import BaseDetector

logger = logging.getLogger(__name__)


class MockDetector(BaseDetector):
    """
    Mock detector for testing and development.
    
    Simulates deepfake detection without requiring actual ML models.
    """
    
    def __init__(self):
        """Initialize the mock detector."""
        super().__init__("mock")
    
    async def detect(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Simulate deepfake detection with a random result.
        
        Args:
            file_bytes: The file contents as bytes
            
        Returns:
            Dictionary with is_deepfake, confidence, and analysis_time
        """
        logger.info("Starting mock deepfake analysis...")
        
        start_time = time.time()
        
        # Simulate processing delay (1 to 2 seconds)
        delay = 1.0 + (hash(file_bytes) % 100) / 100.0
        await asyncio.sleep(delay)
        
        analysis_time = time.time() - start_time
        
        # Simulate ML model output (deterministic based on file content hash)
        file_hash = hash(file_bytes) % 100
        is_deepfake = file_hash > 50  # ~50% chance
        confidence = (file_hash % 100) / 100.0
        
        result = {
            "is_deepfake": is_deepfake,
            "confidence": round(confidence, 3),
            "analysis_time": round(analysis_time, 3),
        }
        
        logger.info(f"Mock analysis completed. Result: {result}")
        return result
