import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    HealthResponse,
    TextAnalysisRequest,
    ImageAnalysisRequest,
    VideoAnalysisRequest,
    FileAnalysisRequest,
)
from app.services.download import download_file
from app.services.text_analyzer import analyze_text
from app.services.image_analyzer import analyze_image
from app.core.config import get_settings
from app.utils.exceptions import DeepfakeDetectionError

logger = logging.getLogger(__name__)

router = APIRouter()

AVAILABLE_MODELS = {
    "text": ["yaya36095/xlm-roberta-text-detector"],
    "image": ["capcheck/ai-image-detection"],
    "video": [],
    "file": [],
}

MAX_CONTENT_SIZES = {
    "text": 5000,
    "image": 100 * 1024 * 1024,
    "video": 100 * 1024 * 1024,
    "file": 100 * 1024 * 1024,
}


@router.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    logger.info("Health check endpoint accessed")
    
    supported_types = ["text", "image", "video", "file"]
    
    return HealthResponse(
        status="ok",
        service="Deepfake Detection Service",
        version=settings.APP_VERSION,
        available_models=AVAILABLE_MODELS,
        supported_types=supported_types,
    )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Analysis"],
    summary="Analyze content for deepfake detection",
)
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    settings = get_settings()
    
    if isinstance(request, TextAnalysisRequest):
        content_type = "text"
        
        if len(request.text) > MAX_CONTENT_SIZES["text"]:
            raise HTTPException(
                status_code=400,
                detail=f"Text content exceeds maximum length of {MAX_CONTENT_SIZES['text']} characters"
            )
        
        if len(request.text) < 50:
            raise HTTPException(
                status_code=400,
                detail="Text content must be at least 50 characters"
            )
        
        if not AVAILABLE_MODELS["text"]:
            raise HTTPException(
                status_code=400,
                detail="No model available for text analysis"
            )
        
        model = AVAILABLE_MODELS["text"][0]
        logger.info(f"Received text analysis request, length: {len(request.text)} chars, model: {model}")
        
        try:
            analysis_result = await analyze_text(request.text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Text analysis error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to analyze text")
        
        logger.info(f"Text analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=model,
            content_type="text",
        )
    
    elif isinstance(request, ImageAnalysisRequest):
        content_type = "image"
        
        if not AVAILABLE_MODELS["image"]:
            raise HTTPException(
                status_code=400,
                detail="No model available for image analysis"
            )
        
        model = AVAILABLE_MODELS["image"][0]
        logger.info(f"Received image analysis request for URL: {request.image_url}, model: {model}")
        
        try:
            image_bytes = await download_file(str(request.image_url))
            if not image_bytes:
                raise HTTPException(status_code=500, detail="Failed to download image")
            
            if len(image_bytes) > MAX_CONTENT_SIZES["image"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image size exceeds maximum of {MAX_CONTENT_SIZES['image']} bytes"
                )
            
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await analyze_image(image_bytes)
        
        logger.info(f"Image analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=model,
            content_type="image",
        )
    
    elif isinstance(request, VideoAnalysisRequest):
        content_type = "video"
        
        if not AVAILABLE_MODELS["video"]:
            raise HTTPException(
                status_code=400,
                detail="No model available for video analysis"
            )
        
        model = AVAILABLE_MODELS["video"][0]
        logger.info(f"Received video analysis request for URL: {request.video_url}, model: {model}")
        
        try:
            video_bytes = await download_file(str(request.video_url))
            if not video_bytes:
                raise HTTPException(status_code=500, detail="Failed to download video")
            
            if len(video_bytes) > MAX_CONTENT_SIZES["video"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video size exceeds maximum of {MAX_CONTENT_SIZES['video']} bytes"
                )
            
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await analyze_image(video_bytes)
        
        logger.info(f"Video analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=model,
            content_type="video",
        )
    
    elif isinstance(request, FileAnalysisRequest):
        content_type = "file"
        
        if not AVAILABLE_MODELS["file"]:
            raise HTTPException(
                status_code=400,
                detail="No model available for file analysis"
            )
        
        model = AVAILABLE_MODELS["file"][0]
        logger.info(f"Received file analysis request for URL: {request.file_url}, model: {model}")
        
        try:
            file_bytes = await download_file(str(request.file_url))
            if not file_bytes:
                raise HTTPException(status_code=500, detail="Failed to download file")
            
            if len(file_bytes) > MAX_CONTENT_SIZES["file"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum of {MAX_CONTENT_SIZES['file']} bytes"
                )
            
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await analyze_image(file_bytes)
        
        logger.info(f"File analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=model,
            content_type="file",
        )
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
