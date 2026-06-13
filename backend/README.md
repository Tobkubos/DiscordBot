# Deepfake Detection Service Backend

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
  "used_model": "mock"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid URL, file too large, or unsupported model
- `408 Request Timeout`: File download timed out
- `500 Internal Server Error`: Server error during analysis


### Using curl:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/video.mp4"}'
```


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

