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
from app.services.detector import get_detector
from app.core.config import get_settings
from app.utils.exceptions import DeepfakeDetectionError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    logger.info("Health check endpoint accessed")
    
    available_models = ["mock"]
    supported_types = ["text", "image", "video", "file"]
    
    return HealthResponse(
        status="ok",
        service="Deepfake Detection Service",
        version=settings.APP_VERSION,
        available_models=available_models,
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
    detector_model = None
    
    if isinstance(request, TextAnalysisRequest):
        detector_model = request.model or settings.DEFAULT_DETECTOR_MODEL
        logger.info(f"Received text analysis request, length: {len(request.text)} chars, model: {detector_model}")
        
        try:
            detector = get_detector(detector_model)
        except ValueError as e:
            logger.error(f"Invalid detector model: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        text_bytes = request.text.encode('utf-8')
        analysis_result = await detector.detect(text_bytes)
        
        logger.info(f"Text analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=detector_model,
            content_type="text",
        )
    
    elif isinstance(request, ImageAnalysisRequest):
        detector_model = request.model or settings.DEFAULT_DETECTOR_MODEL
        logger.info(f"Received image analysis request for URL: {request.image_url}, model: {detector_model}")
        
        try:
            detector = get_detector(detector_model)
        except ValueError as e:
            logger.error(f"Invalid detector model: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        try:
            image_bytes = await download_file(str(request.image_url))
            if not image_bytes:
                raise HTTPException(status_code=500, detail="Failed to download image")
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await detector.detect(image_bytes)
        
        logger.info(f"Image analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=detector_model,
            content_type="image",
        )
    
    elif isinstance(request, VideoAnalysisRequest):
        detector_model = request.model or settings.DEFAULT_DETECTOR_MODEL
        logger.info(f"Received video analysis request for URL: {request.video_url}, model: {detector_model}")
        
        try:
            detector = get_detector(detector_model)
        except ValueError as e:
            logger.error(f"Invalid detector model: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        try:
            video_bytes = await download_file(str(request.video_url))
            if not video_bytes:
                raise HTTPException(status_code=500, detail="Failed to download video")
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await detector.detect(video_bytes)
        
        logger.info(f"Video analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=detector_model,
            content_type="video",
        )
    
    elif isinstance(request, FileAnalysisRequest):
        detector_model = request.model or settings.DEFAULT_DETECTOR_MODEL
        logger.info(f"Received file analysis request for URL: {request.file_url}, model: {detector_model}")
        
        try:
            detector = get_detector(detector_model)
        except ValueError as e:
            logger.error(f"Invalid detector model: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        try:
            file_bytes = await download_file(str(request.file_url))
            if not file_bytes:
                raise HTTPException(status_code=500, detail="Failed to download file")
        except DeepfakeDetectionError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        
        analysis_result = await detector.detect(file_bytes)
        
        logger.info(f"File analysis completed. Result: {analysis_result}")
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=detector_model,
            content_type="file",
        )
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
