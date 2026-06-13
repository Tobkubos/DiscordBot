"""
Pytest configuration for the Deepfake Detection Service tests.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Provide a test client for API testing."""
    from app import app
    return TestClient(app)


@pytest.fixture
def sample_texts():
    """Provide sample text data for testing."""
    return {
        "ai_generated": "This is an AI-generated text that demonstrates the capabilities of modern language models in creating coherent and contextually appropriate content without human intervention.",
        "human_written": "I went to the store yesterday and bought some groceries. The weather was nice, and I enjoyed the walk.",
        "technical": "The implementation of neural networks requires careful consideration of hyperparameters, activation functions, and optimization techniques to achieve optimal performance.",
        "short": "Too short",
        "long": "A" * 5001,  # Exceeds 5000 char limit
        "minimum": "A" * 50,  # Exactly 50 chars (minimum valid)
    }
