from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class AnalysisRequest(BaseModel):
    """Request model for deepfake analysis."""
    
    file_url: HttpUrl = Field(
        ..., description="URL of the file to analyze for deepfake detection"
    )
    model: Optional[str] = Field(
        None, description="Detector model to use (e.g., 'mock', 'deepseek', 'openai')"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_url": "https://example.com/video.mp4",
                "model": "mock"
            }
        }


class AnalysisResponse(BaseModel):
    """Response model for deepfake analysis results."""
    
    is_deepfake: bool = Field(
        ..., description="Whether the file is detected as a deepfake"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    analysis_time: float = Field(
        ..., description="Time taken for analysis in seconds"
    )
    model_used: str = Field(
        ..., description="The detector model that was used"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_deepfake": True,
                "confidence": 0.847,
                "analysis_time": 1.234,
                "model_used": "mock"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[str] = Field(
        None, description="Additional error details"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid URL format",
                "status_code": 400,
                "details": "The provided file_url is not a valid URL"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    available_models: list = Field(..., description="Available detector models")
