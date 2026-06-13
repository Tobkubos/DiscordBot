"""
Deepfake Detection Service - Backend Entry Point

This is the main entry point for the FastAPI application.
Run this file directly to start the server on localhost:8000
"""

import logging
from app import create_app
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def main():
    """Initialize and run the FastAPI application."""
    settings = get_settings()
    app = create_app()
    
    import uvicorn
    
    logger.info(
        f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}"
    )
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
