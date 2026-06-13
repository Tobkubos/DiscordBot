"""Deepfake Detection Service Application"""

from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging
from app.core.config import Settings

__version__ = Settings.APP_VERSION or "1.0.0"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    
    app = FastAPI(
        title="Deepfake Detection Service",
        description="Backend service for deepfake detection with support for multiple ML models",
        version=__version__,
    )
    
    # Include API routes
    app.include_router(api_router)
    
    @app.on_event("startup")
    async def startup_event():
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Deepfake Detection Service is starting up...")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Deepfake Detection Service is shutting down...")
    
    return app
