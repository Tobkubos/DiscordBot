from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="Deepfake Detection Service",
    description="Backend service for deepfake detection with support for multiple ML models",
    version="1.0.0",
)

app.include_router(api_router)
