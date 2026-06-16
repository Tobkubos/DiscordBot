from fastapi import FastAPI
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


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(api_router)
