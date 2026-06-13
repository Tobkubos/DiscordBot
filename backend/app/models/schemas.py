from pydantic import BaseModel, HttpUrl, Field
from typing import Union, Literal, Optional


class TextAnalysisRequest(BaseModel):
    content_type: Literal["text"]
    text: str = Field(..., description="Text content to analyze for deepfake detection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "text",
                "text": "Some text that might be AI-generated"
            }
        }


class ImageAnalysisRequest(BaseModel):
    content_type: Literal["image"]
    image_url: HttpUrl = Field(..., description="URL of the image to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "image",
                "image_url": "https://example.com/image.jpg"
            }
        }


class VideoAnalysisRequest(BaseModel):
    content_type: Literal["video"]
    video_url: HttpUrl = Field(..., description="URL of the video to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "video",
                "video_url": "https://example.com/video.mp4"
            }
        }


class FileAnalysisRequest(BaseModel):
    content_type: Literal["file"]
    file_url: HttpUrl = Field(..., description="URL of the file to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "file",
                "file_url": "https://example.com/video.mp4"
            }
        }


AnalysisRequest = Union[
    TextAnalysisRequest,
    ImageAnalysisRequest,
    VideoAnalysisRequest,
    FileAnalysisRequest,
]


class AnalysisResponse(BaseModel):
    is_deepfake: bool = Field(..., description="Whether the content is detected as a deepfake")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    analysis_time: float = Field(..., description="Time taken for analysis in seconds")
    used_model: str = Field(..., description="The detector model that was used")
    content_type: str = Field(..., description="Type of content analyzed (text/image/video/file)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_deepfake": True,
                "confidence": 0.847,
                "analysis_time": 1.234,
                "used_model": "mock",
                "content_type": "image"
            }
        }


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[str] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid URL format",
                "status_code": 400,
                "details": "The provided URL is not valid"
            }
        }


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    available_models: dict = Field(..., description="Available detector models per content type")
    supported_types: list = Field(..., description="Supported content types")
