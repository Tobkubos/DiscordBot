import logging
from fastapi import APIRouter, HTTPException, Request, status
from slowapi.errors import RateLimitExceeded
from limits import parse

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    GuildConfigSchema,
    HealthResponse,
    TextAnalysisRequest,
    ImageAnalysisRequest,
)
from app.services.download import download_file
from app.services.text_analyzer import analyze_text
from app.services.image_analyzer import analyze_image
from app.core.config import get_settings
from app.utils.exceptions import DeepfakeDetectionError, SetupRequiredError
from app.core.limiter import limiter
from app.config_manager import _load_all_configs, save_guild_config

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
        models_status=models_status,
    )

# Endpoint do zapisywania konfiguracji (wywoływany przez bota)
@router.post("/guilds/{guild_id}/setup", tags=["Setup"])
async def save_discord_guild_setup(guild_id: str, payload: GuildConfigSchema):
    # Walidacja modeli z pliku ustawień
    settings = get_settings()
    allowed_text_models = settings.AVAILABLE_MODELS.get("text", [])
    allowed_image_models = settings.AVAILABLE_MODELS.get("image", [])
    
    # Walidujemy tylko wtedy, gdy model nie jest ustawiony na "none"
    if payload.active_text_model and payload.active_text_model.lower() != "none":
        if payload.active_text_model not in allowed_text_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{payload.active_text_model}' nie jest dozwolony. Wybierz z: {allowed_text_models}"
            )
            
    if payload.active_image_model and payload.active_image_model.lower() != "none":
        if payload.active_image_model not in allowed_image_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{payload.active_image_model}' nie jest dozwolony. Wybierz z: {allowed_image_models}"
            )
            
    # Zapis konfiguracji przez config_manager
    config_dict = payload.dict()
    save_guild_config(guild_id, config_dict)
    
    logger.info(f"Zapisano nową konfigurację dla serwera Discord {guild_id}")
    return {
        "status": "success",
        "message": f"Konfiguracja dla serwera {guild_id} została zapisana.",
        "config": config_dict
    }

@router.get("/guilds/{guild_id}/config", tags=["Setup"])
async def get_discord_guild_config(guild_id: str):
    """Zwraca zapisaną konfigurację dla konkretnego serwera Discord."""
    configs = _load_all_configs()
    guild_config = configs.get(guild_id, {})
    
    return {
        "active_text_model": guild_config.get("active_text_model", "none"),
        "active_image_model": guild_config.get("active_image_model", "none"),
        "log_channel_id": guild_config.get("log_channel_id", None)
    }

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
async def analyze(request: Request, payload: AnalysisRequest) -> AnalysisResponse:
    guild_id = payload.guild_id
    limit_item = parse("1/5seconds")
    
    if not limiter.limiter.hit(limit_item, f"analyze:{guild_id}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for this guild")
    
    if isinstance(payload, TextAnalysisRequest):
        content_type = "text"
    elif isinstance(payload, ImageAnalysisRequest):
        content_type = "image"
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail="Unsupported file/content type. Only text and image are currently supported."
        )

    settings = get_settings()

    try:
        if content_type == "text":
            if len(payload.text) > settings.MAX_CONTENT_SIZES["text"]:
                raise ValueError(f"Text content exceeds maximum length of {settings.MAX_CONTENT_SIZES['text']} characters")
            if len(payload.text) < 50:
                raise ValueError("Text content must be at least 50 characters")
            
            analysis_result = await analyze_text(payload.text, guild_id)

        elif content_type == "image":
            image_bytes = await download_file(str(payload.image_url))
            if not image_bytes:
                raise ValueError("Failed to download image")
            if len(image_bytes) > settings.MAX_CONTENT_SIZES["image"]:
                raise ValueError(f"Image size exceeds maximum of {settings.MAX_CONTENT_SIZES['image']} bytes")
            
            analysis_result = await analyze_image(image_bytes, guild_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SetupRequiredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DeepfakeDetectionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"{content_type.capitalize()} analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze {content_type}")

    logger.info(f"{content_type.capitalize()} analysis completed. Result: {analysis_result}")
    used_model = analysis_result.get("used_model", settings.AVAILABLE_MODELS.get(content_type)[0])
    
    return AnalysisResponse(
        is_deepfake=analysis_result["is_deepfake"],
        confidence=analysis_result["confidence"],
        analysis_time=analysis_result["analysis_time"],
        used_model=used_model,
        content_type=content_type,
    )