import os

from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging
from app.core.limiter import limiter

setup_logging()

app = FastAPI(
    title="Deepfake Detection Service",
    description="Backend service for deepfake detection with support for multiple ML models",
    version="1.0.0",
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
EXPECTED_API_KEY = os.getenv("BACKEND_API_KEY")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not EXPECTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Błąd serwera: Klucz API nie został skonfigurowany."
        )
    if api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak autoryzacji: Nieprawidłowy lub brakujący klucz API."
        )
    return api_key

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(api_router)
