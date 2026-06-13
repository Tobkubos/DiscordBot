# Quick Reference Guide

## 🚀 Starting the Backend

### First Time Setup (Windows)
```powershell
cd backend
python setup.py
venv\Scripts\activate
python main.py
```

### First Time Setup (macOS/Linux)
```bash
cd backend
python setup.py
source venv/bin/activate
python main.py
```

### Subsequent Times
```bash
cd backend
run.bat      # Windows
# OR
./run.sh     # macOS/Linux
```

## 📡 API Quick Test

### Health Check
```bash
curl http://localhost:8000/
```

### Analyze a File
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/video.mp4"}'
```

### Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Configuration

Edit `backend/.env`:
```env
HOST=127.0.0.1
PORT=8000
DEFAULT_DETECTOR_MODEL=mock
LOG_LEVEL=INFO
DOWNLOAD_TIMEOUT=30
MAX_FILE_SIZE=104857600
```

## 📦 Project Structure

```
backend/
├── app/
│   ├── api/         # Routes
│   ├── services/    # Business logic (download, ML models, queuing)
│   ├── models/      # Data schemas
│   ├── core/        # Configuration
│   └── utils/       # Exceptions
├── main.py          # Entry point
├── README.md        # Full API docs
└── DEVELOPMENT.md   # Adding models, Redis, etc.
```

## ➕ Adding a New ML Model

1. Copy `DETECTOR_TEMPLATE.py`
2. Implement the `detect()` method
3. Register in `app/services/detector/__init__.py`
4. Update `.env` if setting as default

See `DEVELOPMENT.md` for detailed steps.

## 🔗 Integrating with Discord Bot

Use `DISCORD_BOT_EXAMPLE.py` as a template:

```python
from discord_bot_example import setup

# In your bot startup:
await setup(bot)

# Then use in your bot:
# !deepfake_check https://example.com/video.mp4
# !backend_status
```

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Activate venv first |
| Port 8000 in use | Change port: `PORT=8001 python main.py` |
| Import errors | `pip install -r requirements.txt` |
| Download timeout | Increase: `DOWNLOAD_TIMEOUT=60 python main.py` |

## 📊 Supported File Types

Any file type via URL:
- Videos: `.mp4`, `.webm`, `.avi`, etc.
- Images: `.jpg`, `.png`, `.gif`, etc.
- Any file up to 100 MB (configurable)

## 🔄 Async Support

Backend is fully async:
- Non-blocking file downloads
- Concurrent requests supported
- Scalable to Redis task queuing

## 📝 Logging Levels

```bash
# Normal operation
LOG_LEVEL=INFO python main.py

# Verbose debugging
LOG_LEVEL=DEBUG python main.py

# Warnings and errors only
LOG_LEVEL=WARNING python main.py
```

## 🚀 Production Deployment

For production, use Gunicorn with Uvicorn:

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📞 Response Format

**Success:**
```json
{
  "is_deepfake": true,
  "confidence": 0.95,
  "analysis_time": 1.5,
  "model_used": "mock"
}
```

**Error:**
```json
{
  "error": "Invalid URL format",
  "status_code": 400,
  "details": null
}
```

## 🔐 Default Security Settings

- Max file size: 100 MB
- Download timeout: 30 seconds
- URL validation: Enabled
- Error details: Minimal (no leakage)

Increase security for production:
- Add API keys/authentication
- Implement rate limiting
- Use HTTPS
- Add CORS restrictions

## 🎯 Next Steps

1. ✅ Backend running?
2. ⏳ Test with sample URLs
3. ⏳ Create Discord bot using example
4. ⏳ Add your ML models
5. ⏳ Deploy to production

---

For complete documentation, see `README.md` and `DEVELOPMENT.md` in the backend folder.
