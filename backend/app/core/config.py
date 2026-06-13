import os
from typing import Optional
from functools import lru_cache


class Settings:
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Deepfake Detection Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # File handling
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024)))  # 100 MB
    
    # ML Model configuration
    DEFAULT_DETECTOR_MODEL: str = os.getenv("DEFAULT_DETECTOR_MODEL", "mock")
    # Supported models: "mock", "deepseek", "openai", etc. (easy to add more)
    
    # Redis configuration (for future queuing)
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_QUEUE_NAME: str = os.getenv("REDIS_QUEUE_NAME", "deepfake_analysis")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", None)
    
    AVAILABLE_MODELS = {
        "text": ["yaya36095/xlm-roberta-text-detector"],
        "image": ["capcheck/ai-image-detection"],
    }

    MAX_CONTENT_SIZES = {
        "text": 5000,
        "image": 100 * 1024 * 1024,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
