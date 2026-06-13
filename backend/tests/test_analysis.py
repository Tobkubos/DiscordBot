"""
Comprehensive tests for the Deepfake Detection Service.
Tests cover: text analysis, rate limiting, response validation, and Redis integration.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app import app
from app.services.text_analyzer import analyze_text
from app.services.queue import get_queue_service
from app.models.schemas import TextAnalysisRequest, AnalysisResponse
from app.core.limiter import limiter


client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """
    Automatyczny fixture, który przed KAŻDYM testem 
    czyści pamięć limitera zapytań SlowAPI.
    Dzięki temu testy nie blokują się nawzajem błędem 429.
    """
    limiter._storage.reset()

class TestTextAnalysis:
    """Test text deepfake analysis functionality."""
    
    def test_health_check(self):
        """Test health check endpoint returns correct status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert data["service"] == "Deepfake Detection Service"
        assert "available_models" in data
        assert "text" in data["supported_types"]
        assert "image" in data["supported_types"]
    
    def test_text_analysis_valid_input(self):
        """Test text analysis with valid AI-generated text."""
        payload = {
            "content_type": "text",
            "text": "This is an AI-generated text that demonstrates the capabilities of modern language models in creating coherent and contextually appropriate content without human intervention."
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "is_deepfake" in data
        assert isinstance(data["is_deepfake"], bool)
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert "analysis_time" in data
        assert data["analysis_time"] > 0
        assert "used_model" in data
        assert data["content_type"] == "text"
        assert "yaya36095/xlm-roberta-text-detector" in data["used_model"]
    
    def test_text_analysis_human_written(self):
        """Test text analysis with human-written text."""
        payload = {
            "content_type": "text",
            "text": "I went to the store yesterday and bought some groceries. The weather was nice, and I enjoyed the walk. I also met an old friend who I haven't seen in years. We talked about our lives and made plans to meet again soon."
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["is_deepfake"], bool)
        assert 0.0 <= data["confidence"] <= 1.0
    
    def test_text_analysis_too_short(self):
        """Test text analysis with text that's too short (< 50 chars)."""
        payload = {
            "content_type": "text",
            "text": "Short text"
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "at least 50 characters" in data["detail"]
    
    def test_text_analysis_too_long(self):
        """Test text analysis with text that exceeds max length."""
        payload = {
            "content_type": "text",
            "text": "A" * 5001  # Exceeds 5000 character limit
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "exceeds maximum length" in data["detail"]
    
    def test_text_analysis_exactly_50_chars(self):
        """Test text analysis with exactly 50 characters (minimum valid)."""
        text_50_chars = "A" * 50
        payload = {
            "content_type": "text",
            "text": text_50_chars
        }
        response = client.post("/analyze", json=payload)
        
        # Should either succeed or fail based on model behavior
        # but not because of length validation
        assert response.status_code in [200, 500]  # Success or model error, not validation error
    
    def test_text_analysis_empty_text(self):
        """Test text analysis with empty text."""
        payload = {
            "content_type": "text",
            "text": ""
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
    
    def test_text_analysis_missing_field(self):
        """Test text analysis with missing text field."""
        payload = {
            "content_type": "text"
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestRateLimiting:
    """Test rate limiting (slowapi) functionality."""
    
    def test_rate_limit_single_request(self):
        """Test that a single request is allowed."""
        payload = {
            "content_type": "text",
            "text": "This is a test text with sufficient length to pass validation and be analyzed by the deepfake detector model."
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code in [200, 500]  # Should not be rate limited
        assert response.status_code != 429
    
    def test_rate_limit_multiple_rapid_requests(self):
        """Test that rapid requests are rate limited (1 per 5 seconds)."""
        payload = {
            "content_type": "text",
            "text": "This is a test text with sufficient length to pass validation and be analyzed by the deepfake detector model."
        }
        
        # First request should succeed
        response1 = client.post("/analyze", json=payload)
        assert response1.status_code != 429
        
        # Immediate second request should be rate limited
        response2 = client.post("/analyze", json=payload)
        assert response2.status_code == 429
        assert "rate limit" in response2.text.lower()
    
    def test_rate_limit_recovery_after_delay(self):
        """Test that rate limit recovers after 5 seconds."""
        payload = {
            "content_type": "text",
            "text": "This is a test text with sufficient length to pass validation and be analyzed by the deepfake detector model."
        }
        
        # First request
        response1 = client.post("/analyze", json=payload)
        first_status = response1.status_code
        
        # Wait for rate limit to reset (5+ seconds)
        import time
        time.sleep(5.1)
        
        # Second request should now be allowed
        response2 = client.post("/analyze", json=payload)
        assert response2.status_code != 429


class TestResponseValidation:
    """Test response structure and validation."""
    
    def test_response_includes_all_fields(self):
        """Test that response includes all required fields."""
        payload = {
            "content_type": "text",
            "text": "This is a comprehensive test to ensure the response includes all necessary fields for proper API usage and data handling requirements."
        }
        response = client.post("/analyze", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["is_deepfake", "confidence", "analysis_time", "used_model", "content_type"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
    
    def test_response_confidence_range(self):
        """Test that confidence score is between 0.0 and 1.0."""
        payload = {
            "content_type": "text",
            "text": "This is another test to verify that the confidence score is properly normalized between zero and one for consistent API behavior."
        }
        response = client.post("/analyze", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert 0.0 <= data["confidence"] <= 1.0
    
    def test_response_analysis_time_positive(self):
        """Test that analysis_time is positive."""
        payload = {
            "content_type": "text",
            "text": "Testing the analysis time tracking to ensure it records valid positive durations for performance monitoring purposes."
        }
        response = client.post("/analyze", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert data["analysis_time"] > 0


class TestRedisIntegration:
    """Test Redis queue integration."""
    
    def test_queue_service_initialization(self):
        """Test that queue service initializes correctly."""
        queue_service = get_queue_service()
        assert queue_service is not None
    
    def test_queue_service_singleton(self):
        """Test that queue service is a singleton."""
        queue_service1 = get_queue_service()
        queue_service2 = get_queue_service()
        assert queue_service1 is queue_service2
    
    @pytest.mark.asyncio
    async def test_enqueue_analysis_task(self):
        """Test enqueuing an analysis task."""
        queue_service = get_queue_service()
        
        result = await queue_service.enqueue_analysis(
            file_url="https://example.com/text.txt",
            model="yaya36095/xlm-roberta-text-detector",
            task_id="test_task_001"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_task_result(self):
        """Test retrieving task result from queue."""
        queue_service = get_queue_service()
        
        # Try to get a non-existent result
        result = await queue_service.get_task_result("non_existent_task")
        
        # Should return None for non-existent task
        assert result is None
    
    def test_redis_config_available(self):
        """Test that Redis config is available."""
        from app.core.config import get_settings
        settings = get_settings()
        
        assert hasattr(settings, "REDIS_ENABLED")
        assert hasattr(settings, "REDIS_URL")
        assert hasattr(settings, "REDIS_QUEUE_NAME")


class TestAsyncTextAnalyzer:
    """Test async text analyzer directly."""
    
    @pytest.mark.asyncio
    async def test_analyze_text_valid_input(self):
        """Test analyze_text function with valid input."""
        text = "This is a comprehensive test of the async text analyzer to ensure it properly processes input and returns valid results."
        
        result = await analyze_text(text)
        
        assert isinstance(result, dict)
        assert "is_deepfake" in result
        assert "confidence" in result
        assert "analysis_time" in result
        assert isinstance(result["is_deepfake"], bool)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_text_multiple_calls(self):
        """Test that analyze_text can be called multiple times (model caching)."""
        text1 = "First test text that should be analyzed by the model to verify it works correctly on multiple invocations."
        text2 = "Second test text to ensure the model remains loaded in memory for subsequent analysis operations."
        
        result1 = await analyze_text(text1)
        result2 = await analyze_text(text2)
        
        assert result1 is not None
        assert result2 is not None
        assert "confidence" in result1
        assert "confidence" in result2


class TestErrorHandling:
    """Test error handling in endpoints."""
    
    def test_unsupported_content_type(self):
        """Test handling of unsupported content type."""
        payload = {
            "content_type": "unsupported_type",
            "data": "some data"
        }
        response = client.post("/analyze", json=payload)
        
        assert response.status_code in [415, 422]  # Unsupported media type or validation error
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        response = client.post(
            "/analyze",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_invalid_content_type_header(self):
        """Test handling of invalid Content-Type header."""
        payload = {
            "content_type": "text",
            "text": "Valid test text with sufficient length to be properly analyzed and validated by the system."
        }
        response = client.post(
            "/analyze",
            json=payload,
            headers={"Content-Type": "text/plain"}
        )
        
        # Should still work as FastAPI is lenient
        assert response.status_code in [200, 422, 400, 415, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
