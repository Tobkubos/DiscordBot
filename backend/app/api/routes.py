"""API route handlers."""

import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    HealthResponse,
)
from app.services.download import download_file
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
    """
    Health check endpoint to verify service is running.
    
    Returns:
        Service status and version information
    """
    settings = get_settings()
    logger.info("Health check endpoint accessed")
    
    available_models = ["mock"]  # Add more as you implement them
    
    return HealthResponse(
        status="ok",
        service="Deepfake Detection Service",
        version=settings.APP_VERSION,
        available_models=available_models,
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
    summary="Analyze file for deepfake detection",
)
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyze a file for deepfake detection.
    
    Args:
        request: AnalysisRequest containing file_url and optional model selection
        
    Returns:
        AnalysisResponse with detection results
        
    Raises:
        HTTPException: For various error conditions during processing
    """
    settings = get_settings()
    detector_model = request.model or settings.DEFAULT_DETECTOR_MODEL
    
    logger.info(
        f"Received analysis request for URL: {request.file_url} "
        f"using model: {detector_model}"
    )
    
    
    try:
        try:
            detector = get_detector(detector_model)
        except ValueError as e:
            logger.error(f"Invalid detector model: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )
        
        file_bytes = await download_file(str(request.file_url))
        
        if not file_bytes:
            logger.error("File download returned empty bytes")
            raise HTTPException(
                status_code=500,
                detail="Failed to download and process file",
            )
        
        analysis_result = await detector.detect(file_bytes)
        
        logger.info(
            f"Analysis request completed successfully. "
            f"File URL: {request.file_url}, Model: {detector_model}, "
            f"Result: {analysis_result}"
        )
        
        return AnalysisResponse(
            is_deepfake=analysis_result["is_deepfake"],
            confidence=analysis_result["confidence"],
            analysis_time=analysis_result["analysis_time"],
            model_used=detector_model,
        )
        
    except HTTPException:
        raise
    except DeepfakeDetectionError as e:
        logger.error(f"Detection error: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during analysis. Please try again later.",
        )
