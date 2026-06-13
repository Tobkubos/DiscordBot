# Development Guide for Deepfake Detection Backend

## Project Overview

This is a production-ready FastAPI backend for deepfake detection with a modular, extensible architecture. It's designed to support multiple ML models and easy integration with task queues like Redis.

## Architecture Overview

```
FastAPI Application (app/__init__.py)
├── API Routes (app/api/routes.py)
│   ├── GET / (Health check)
│   └── POST /analyze (Main endpoint)
├── Services Layer (app/services/)
│   ├── download.py (File downloading)
│   ├── queue.py (Redis-ready task queue)
│   └── detector/ (ML model implementations)
│       ├── base.py (Abstract interface)
│       ├── mock.py (Test implementation)
│       └── [custom_detector].py (Add your models here)
├── Models/Schemas (app/models/schemas.py)
└── Core Configuration (app/core/)
    ├── config.py (Settings)
    └── logging_config.py (Logging setup)
```

## Adding a New ML Model

### Step 1: Create Your Detector Class

Create a new file in `app/services/detector/` (e.g., `deepseek.py`):

```python
import logging
import time
from typing import Dict, Any
from app.services.detector.base import BaseDetector

logger = logging.getLogger(__name__)

class DeepseekDetector(BaseDetector):
    def __init__(self):
        super().__init__("deepseek")
        # Initialize your model here
        # self.model = load_deepseek_model()
    
    async def detect(self, file_bytes: bytes) -> Dict[str, Any]:
        logger.info("Starting Deepseek detection...")
        start_time = time.time()
        
        # Your detection logic
        is_deepfake = False  # Your ML logic
        confidence = 0.95
        
        analysis_time = time.time() - start_time
        
        return {
            "is_deepfake": is_deepfake,
            "confidence": round(confidence, 3),
            "analysis_time": round(analysis_time, 3),
        }
```

### Step 2: Register the Detector

Update `app/services/detector/__init__.py`:

```python
from app.services.detector.deepseek import DeepseekDetector

def get_detector(model_name: str = "mock") -> BaseDetector:
    detectors = {
        "mock": MockDetector,
        "deepseek": DeepseekDetector,  # Add this
    }
    # ... rest of code
```

### Step 3: Update Configuration

Add to `.env`:
```
DEFAULT_DETECTOR_MODEL=deepseek
```

### Step 4: Test Your Model

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/video.mp4", "model": "deepseek"}'
```

## Adding Redis Task Queuing

### Step 1: Install Redis

```bash
pip install redis aioredis
```

### Step 2: Update requirements.txt

Add to `requirements.txt`:
```
redis==5.0.0
aioredis==2.0.1
```

### Step 3: Enable Redis

In `.env`:
```
REDIS_ENABLED=True
REDIS_URL=redis://localhost:6379
```

### Step 4: Implement Queue Service

Update `app/services/queue.py` to implement async Redis operations:

```python
import aioredis
import json

class QueueService:
    async def _initialize_redis(self):
        self.redis_client = await aioredis.create_redis_pool(
            self.settings.REDIS_URL
        )
    
    async def enqueue_analysis(self, file_url: str, model: str, task_id: str):
        task_data = {
            "task_id": task_id,
            "file_url": file_url,
            "model": model,
        }
        await self.redis_client.lpush(
            self.settings.REDIS_QUEUE_NAME,
            json.dumps(task_data)
        )
    
    async def get_task_result(self, task_id: str):
        result = await self.redis_client.get(f"result:{task_id}")
        return json.loads(result) if result else None
```

### Step 5: Create Worker

Create `worker.py` in the backend directory:

```python
import asyncio
import json
import aioredis
from app.services.detector import get_detector
from app.services.download import download_file

async def worker():
    redis = await aioredis.create_redis_pool("redis://localhost:6379")
    
    while True:
        task_json = await redis.rpop("deepfake_analysis")
        if not task_json:
            await asyncio.sleep(1)
            continue
        
        task = json.loads(task_json)
        try:
            file_bytes = await download_file(task["file_url"])
            detector = get_detector(task["model"])
            result = await detector.detect(file_bytes)
            
            await redis.set(
                f"result:{task['task_id']}",
                json.dumps(result)
            )
        except Exception as e:
            logger.error(f"Task failed: {e}")
        
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(worker())
```

## Configuration Options

See `.env.example` for all available settings:

- `HOST`, `PORT` - Server address
- `DOWNLOAD_TIMEOUT` - File download timeout in seconds
- `MAX_FILE_SIZE` - Maximum file size in bytes
- `DEFAULT_DETECTOR_MODEL` - Default ML model to use
- `REDIS_ENABLED` - Enable Redis queuing
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## API Response Format

All responses follow a consistent format:

**Success (200):**
```json
{
  "is_deepfake": boolean,
  "confidence": float,
  "analysis_time": float,
  "model_used": "model_name"
}
```

**Error (4xx/5xx):**
```json
{
  "error": "Error message",
  "status_code": 400,
  "details": "Optional additional details"
}
```

## Error Handling

The service handles:
- **400 Bad Request**: Invalid URL, file too large, unsupported model
- **408 Request Timeout**: Download timeout
- **500 Internal Server Error**: Detector failure or unexpected error

Custom exceptions in `app/utils/exceptions.py` provide specific error types for proper handling.

## Logging

All operations are logged with timestamps and levels:

```python
logger.info("User action")        # Normal operations
logger.warning("Something odd")   # Unexpected but handled
logger.error("Failed action")     # Error occurred
logger.debug("Detailed info")     # Debug information (if enabled)
```

Enable debug logging:
```
LOG_LEVEL=DEBUG python main.py
```

## Testing

### Unit Test Example

```python
# tests/test_detector.py
import pytest
from app.services.detector import get_detector

@pytest.mark.asyncio
async def test_mock_detector():
    detector = get_detector("mock")
    result = await detector.detect(b"test_data")
    
    assert "is_deepfake" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["analysis_time"] > 0
```

### Integration Test Example

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app import create_app

client = TestClient(create_app())

def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_analyze():
    response = await client.post(
        "/analyze",
        json={"file_url": "https://example.com/file.mp4"}
    )
    assert response.status_code == 200
```

## Performance Considerations

1. **Async Operations**: All I/O is non-blocking using async/await
2. **Connection Pooling**: httpx uses connection pooling for downloads
3. **Memory Management**: Files are kept in memory (configure MAX_FILE_SIZE)
4. **Timeouts**: All operations have configurable timeouts
5. **Logging Overhead**: Disable debug logging in production

## Security Considerations

- Validate all URLs with Pydantic's HttpUrl validator
- Limit file size to prevent DoS attacks
- Add rate limiting for production use (FastAPI-limiter)
- Sanitize error messages to avoid information leakage
- Use HTTPS in production
- Add API authentication/authorization

## Deployment

For production deployment:

1. Use a production ASGI server (Gunicorn + Uvicorn)
2. Set `DEBUG=False` in `.env`
3. Configure logging to file
4. Enable Redis for scalability
5. Use environment secrets management
6. Add reverse proxy (nginx/Apache)
7. Enable CORS if needed
8. Add health checks for monitoring

## Common Issues and Solutions

**Issue**: Port 8000 already in use
```bash
PORT=8001 python main.py
```

**Issue**: Module import errors
```bash
# Make sure you're in backend directory and venv is activated
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

**Issue**: File download fails
- Check URL is accessible
- Increase DOWNLOAD_TIMEOUT
- Check MAX_FILE_SIZE limit

**Issue**: Detector not found
- Check model name spelling
- Verify registration in `get_detector()`
- List available models: `GET /`

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [Uvicorn Configuration](https://www.uvicorn.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

For more help, refer to README.md or the inline code documentation.
