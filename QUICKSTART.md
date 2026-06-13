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

or 

"uvicorn app:app --reload --host 127.0.0.1 --port 8000"
"uvicorn app:app --host 127.0.0.1 --port 8000"
```

### Subsequent Times
```bash
cd backend
run.bat
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

