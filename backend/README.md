# Deepfake Detection Service Backend

A scalable FastAPI backend for deepfake detection with support for multiple ML models and future Redis integration for task queuing.

## 📁 Project Structure

```
backend/
├── app/
│   ├── core/                 # Core configuration and setup
│   │   ├── config.py        # Settings management
│   │   └── logging_config.py # Logging setup
│   ├── models/              # Data models
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/            # Business logic layer
│   │   ├── download.py      # File download service
│   │   ├── queue.py         # Task queue service (Redis-ready)
│   │   └── detector/        # ML detector models
│   │       ├── base.py      # Abstract base detector class
│   │       └── mock.py      # Mock detector implementation
│   ├── api/                 # API endpoints
│   │   └── routes.py        # Route handlers
│   └── utils/               # Utilities
│       └── exceptions.py    # Custom exceptions
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or conda

### Installation

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   # Using venv
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```

The server will start on `http://127.0.0.1:8000`

## 📖 API Documentation

Once the server is running, interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 🔌 API Endpoints

### Health Check
```bash
GET /
```

Returns service status and available models.

**Response:**
```json
{
  "status": "ok",
  "service": "Deepfake Detection Service",
  "version": "1.0.0",
  "available_models": ["mock"]
}
```

### Analyze File
```bash
POST /analyze
Content-Type: application/json

{
  "file_url": "https://example.com/video.mp4",
  "model": "mock"
}
```

**Request Parameters:**
- `file_url` (required): URL of the file to analyze
- `model` (optional): Detector model to use. Defaults to configured model

**Response (200 OK):**
```json
{
  "is_deepfake": true,
  "confidence": 0.847,
  "analysis_time": 1.234,
  "model_used": "mock"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid URL, file too large, or unsupported model
- `408 Request Timeout`: File download timed out
- `500 Internal Server Error`: Server error during analysis

## ⚙️ Configuration

Configuration is managed through environment variables. Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Server
HOST=127.0.0.1
PORT=8000

# File handling
DOWNLOAD_TIMEOUT=30
MAX_FILE_SIZE=104857600  # 100 MB

# ML Model
DEFAULT_DETECTOR_MODEL=mock

# Redis (for future use)
REDIS_ENABLED=False
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
LOG_FILE=
```

## 🎯 Adding New ML Models

The architecture supports easy addition of new detector models:

1. **Create a new detector class** in `app/services/detector/`:

```python
# app/services/detector/deepseek.py
from app.services.detector.base import BaseDetector

class DeepseekDetector(BaseDetector):
    def __init__(self):
        super().__init__("deepseek")
    
    async def detect(self, file_bytes: bytes) -> dict:
        # Your ML model implementation
        return {
            "is_deepfake": False,
            "confidence": 0.95,
            "analysis_time": 2.5
        }
```

2. **Register the detector** in `app/services/detector/__init__.py`:

```python
def get_detector(model_name: str = "mock") -> BaseDetector:
    detectors = {
        "mock": MockDetector,
        "deepseek": DeepseekDetector,  # Add this
        # ... more models
    }
    # ... rest of code
```

3. **Update `.env.example`** to document the new model

## 🚦 Future Redis Integration

The queue service is designed to support Redis task queuing without major refactoring:

1. Set `REDIS_ENABLED=True` in `.env`
2. Set correct `REDIS_URL`
3. The queue service will automatically use Redis for task management

Redis support will enable:
- Asynchronous task processing
- Task result caching
- Improved scalability for high-volume requests

## 📝 Logging

Logs are configured in `app/core/logging_config.py`. By default:
- Level: INFO
- Output: Console
- Rotation: Automatic (if LOG_FILE is set)

Configure logging level via environment:
```bash
LOG_LEVEL=DEBUG  # For verbose logging
```

## 🧪 Testing the API

### Using curl:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/video.mp4"}'
```

### Using Python requests:
```python
import requests

response = requests.post(
    "http://localhost:8000/analyze",
    json={"file_url": "https://example.com/video.mp4"}
)
print(response.json())
```

### Using httpx (async):
```python
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/analyze",
            json={"file_url": "https://example.com/video.mp4"}
        )
        print(response.json())

asyncio.run(test())
```

## 🔒 Error Handling

The API provides comprehensive error handling:

```python
# Invalid URL
{
  "error": "Invalid URL format",
  "status_code": 400,
  "details": null
}

# File too large
{
  "error": "File size exceeds maximum allowed size of 104857600 bytes",
  "status_code": 400,
  "details": null
}

# Download timeout
{
  "error": "File download timed out",
  "status_code": 408,
  "details": null
}

# Unsupported model
{
  "error": "Detector model 'invalid' is not supported. Available models: mock",
  "status_code": 400,
  "details": null
}
```

## 🔧 Troubleshooting

**Port already in use:**
```bash
# Change port via environment variable
PORT=8001 python main.py
```

**Import errors:**
```bash
# Ensure you're in the backend directory and have activated venv
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Timeout issues:**
```bash
# Increase timeout for slow downloads
DOWNLOAD_TIMEOUT=60 python main.py
```

## 📦 Dependencies

- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and settings
- **httpx**: Async HTTP client for file downloads

See `requirements.txt` for exact versions.

## 📄 License

This project is part of the DiscordBot backend service.

## 🤝 Contributing

To add new features or models:

1. Follow the existing code structure
2. Implement abstract base classes for new functionality
3. Add comprehensive logging
4. Update documentation and examples

## 📧 Support

For issues or questions, please refer to the project documentation or contact the development team.
