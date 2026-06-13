from pydantic import BaseModel, HttpUrl, Field
from typing import Union, Literal, Optional, Dict, List


class TextAnalysisRequest(BaseModel):
    content_type: Literal["text"]
    text: str = Field(..., description="Text content to analyze for deepfake detection")
    guild_id: str = Field(..., description="ID serwera Discord, z którego pochodzi żądanie")
    
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
    guild_id: str = Field(..., description="ID serwera Discord, z którego pochodzi żądanie")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "image",
                "image_url": "https://example.com/image.jpg"
            }
        }



AnalysisRequest = Union[
    TextAnalysisRequest,
    ImageAnalysisRequest
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
    available_models: Dict[str, List[str]] = Field(
        ..., description="Lista dostępnych modeli pogrupowana według typów"
    )
    supported_types: List[str] = Field(
        ..., description="Obsługiwane typy danych"
    )
    models_status: Dict[str, str] = Field(
        ..., description="Status gotowości handlerów dla poszczególnych typów"
    )
    
class GuildConfigSchema(BaseModel):
    active_text_model: Optional[str] = "none"
    # Tutaj możesz dodać inne parametry, które bot zbiera w sesji setup (np. log_channel_id)
    log_channel_id: Optional[str] = None
