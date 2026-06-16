import asyncio
from collections import defaultdict
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app import verify_api_key
from app.services.queue import get_queue_service
from slowapi.errors import RateLimitExceeded
from limits import parse
from redis.exceptions import LockError

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
local_guild_locks = defaultdict(asyncio.Lock)

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

@router.post("/guilds/{guild_id}/setup", tags=["Setup"], dependencies=[Depends(verify_api_key)])
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
        "config": config_dict,
    }

@router.get("/guilds/{guild_id}/config", tags=["Setup"], dependencies=[Depends(verify_api_key)])
async def get_discord_guild_config(guild_id: str):
    """Zwraca zapisaną konfigurację dla konkretnego serwera Discord."""
    configs = _load_all_configs()
    guild_config = configs.get(guild_id, {})
    
    return {
        "active_text_model": guild_config.get("active_text_model", "none"),
        "active_image_model": guild_config.get("active_image_model", "none"),
        "log_channel_id": guild_config.get("log_channel_id", None),
        "multi_model_workflow": guild_config.get("multi_model_workflow", False)
    }

async def _execute_analysis(payload: AnalysisRequest, guild_id: str, settings) -> dict:
    """Funkcja pomocnicza wykonująca właściwy proces pobierania i analizy."""
    if isinstance(payload, TextAnalysisRequest):
        content_type = "text"
    elif isinstance(payload, ImageAnalysisRequest):
        content_type = "image"
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail="Unsupported file/content type."
        )

    try:
        if content_type == "text":
            if len(payload.text) > settings.MAX_CONTENT_SIZES["text"]:
                raise ValueError(f"Text content exceeds maximum length.")
            if len(payload.text) < 50:
                raise ValueError("Text content must be at least 50 characters")
            
            result = await analyze_text(payload.text, guild_id)

        elif content_type == "image":
            image_bytes = await download_file(str(payload.image_url))
            if not image_bytes:
                raise ValueError("Failed to download image")
            if len(image_bytes) > settings.MAX_CONTENT_SIZES["image"]:
                raise ValueError(f"Image size exceeds maximum.")
            
            result = await analyze_image(image_bytes, guild_id)
            
        result["content_type"] = content_type
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SetupRequiredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DeepfakeDetectionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze {content_type}")
    
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
    dependencies=[Depends(verify_api_key)]
)
async def analyze(request: Request, payload: AnalysisRequest) -> AnalysisResponse:
    guild_id = payload.guild_id
    user_id = payload.user_id
    
    limit_item = parse("1/5seconds")
    if not limiter.limiter.hit(limit_item, f"analyze:user:{user_id}"):
        logger.warning(f"Użytkownik {user_id} przekroczył limit zapytań (1/5s).")
        raise HTTPException(
            status_code=429, 
            detail="Przekroczyłeś limit zapytań. Możesz wykonać tylko 1 analizę na 5 sekund."
        )
    
    settings = get_settings()
    queue_service = get_queue_service()
    
    # 2. Sprawdzamy, czy Redis jest aktywny w pliku konfiguracyjnym oraz czy klient został zainicjalizowany
    if settings.REDIS_ENABLED and queue_service.redis_client is not None:
        logger.info(f"Używam rozproszonej blokady Redis dla użytkownika {user_id}")
        
        # Tworzymy blokadę przy użyciu klienta z QueueService [1.2.6]
        redis_lock = queue_service.redis_client.lock(
            "global_analysis_queue_lock", timeout=60, blocking_timeout=120
        )
        try:
            async with redis_lock:
                analysis_result = await _execute_analysis(payload, guild_id, settings)
        except LockError:
            logger.error(f"Użytkownik {user_id} odrzucony z kolejki Redis z powodu timeoutu.")
            raise HTTPException(
                status_code=503, 
                detail="Serwer jest zbyt zajęty (kolejka Redis przepełniona). Spróbuj ponownie za chwilę."
            )
    else:
        # FALLBACK: Jeśli Redis jest wyłączony, aplikacja automatycznie używa kolejki in-memory
        logger.info(f"Redis jest wyłączony. Używam lokalnej blokady in-memory dla gildii {guild_id}")
        
        local_lock = local_guild_locks[guild_id]
        async with local_lock:
            analysis_result = await _execute_analysis(payload, guild_id, settings)

    # 3. Zwrócenie wyniku analizy
    content_type = analysis_result["content_type"]
    logger.info(f"{content_type.capitalize()} analysis completed. Result: {analysis_result}")
    
    used_model = analysis_result.get("used_model", settings.AVAILABLE_MODELS.get(content_type)[0])
    
    return AnalysisResponse(
        is_deepfake=analysis_result["is_deepfake"],
        confidence=analysis_result["confidence"],
        analysis_time=analysis_result["analysis_time"],
        used_model=used_model,
        content_type=content_type,
        details=analysis_result.get("details"),
    )

from app.api.factcheck_router import router as factcheck_router
router.include_router(factcheck_router) #kupczak tu był 
