import logging
from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    HealthResponse,
    TextAnalysisRequest,
    ImageAnalysisRequest,
)
from app.services.download import download_file
from app.services.text_analyzer import analyze_text
from app.services.image_analyzer import analyze_image
from app.core.config import get_settings
from app.utils.exceptions import DeepfakeDetectionError
from backend.app.services.fact_checker import verify_facts
from app.core.limiter import limiter

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
    
    handlers = {
        "text": analyze_text,
        "image": analyze_image,
    }
    
    models_status = {}
    is_healthy = True
    
    for content_type in settings.AVAILABLE_MODELS.keys():
        handler = handlers.get(content_type)
        
        if handler is not None and callable(handler):
            models_status[content_type] = "ready"
        else:
            models_status[content_type] = "error_not_callable"
            is_healthy = False
            logger.error(f"Krytyczny brak! Handler dla typu '{content_type}' nie jest callable.")

    overall_status = "ok" if is_healthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        service="Deepfake Detection Service",
        version=settings.APP_VERSION,
        available_models=settings.AVAILABLE_MODELS,
        supported_types=list(settings.AVAILABLE_MODELS.keys()),
    )

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        429: {"model": ErrorResponse, "description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["Analysis"],
    summary="Analyze content for deepfake detection",
)
@limiter.limit("1/5seconds")
async def analyze(request: Request, payload: AnalysisRequest) -> AnalysisResponse:
    if isinstance(payload, TextAnalysisRequest):
        content_type = "text"
    elif isinstance(payload, ImageAnalysisRequest):
        content_type = "image"
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
    


    settings = get_settings()
    models = settings.AVAILABLE_MODELS.get(content_type)
    if not models:
        raise HTTPException(status_code=400, detail=f"No model available for {content_type} analysis")
    
    model = models[0]
    logger.info(f"Received {content_type} analysis request, model: {model}")

    try:
        if content_type == "text":
            if len(payload.text) > settings.MAX_CONTENT_SIZES["text"]:
                raise ValueError(f"Text content exceeds maximum length of {settings.MAX_CONTENT_SIZES['text']} characters")
            if len(payload.text) < 50:
                raise ValueError("Text content must be at least 50 characters")
            
            analysis_result = await analyze_text(payload.text)

        elif content_type == "image":
            image_bytes = await download_file(str(payload.image_url))
            if not image_bytes:
                raise ValueError("Failed to download image")
            if len(image_bytes) > settings.MAX_CONTENT_SIZES["image"]:
                raise ValueError(f"Image size exceeds maximum of {settings.MAX_CONTENT_SIZES['image']} bytes")
            
            analysis_result = await analyze_image(image_bytes)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DeepfakeDetectionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"{content_type.capitalize()} analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze {content_type}")

    logger.info(f"{content_type.capitalize()} analysis completed. Result: {analysis_result}")
    
    return AnalysisResponse(
        is_deepfake=analysis_result["is_deepfake"],
        confidence=analysis_result["confidence"],
        analysis_time=analysis_result["analysis_time"],
        used_model=model,
        content_type=content_type,
    )


@router.post("/factcheck", tags=["Fact Checking"])
async def factcheck_route(request: TextAnalysisRequest):
    return await verify_facts(request.text)