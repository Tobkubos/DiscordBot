import logging
from typing import Optional, Any, Dict
import json
import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class QueueService:
    """
    Queue service for managing asynchronous analysis tasks.
    
    Currently uses in-memory queue, can be extended to use Redis.
    """
    
    def __init__(self):
        """Initialize the queue service."""
        self.settings = get_settings()
        self.redis_client = Optional[redis.Redis] = None
        
        if self.settings.REDIS_ENABLED:
            self._initialize_redis()
    
    def _initialize_redis(self):
        
        try:
            self.redis_client = redis.from_url(
                self.settings.REDIS_URL, decode_responses=True
            )
            logger.info(
                f"Redis queue service initialized successfully: {self.settings.REDIS_URL}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.redis_client = None
    
    async def enqueue_analysis(
        self,
        file_url: str,
        model: str,
        task_id: str,
    ) -> bool:
        """
        Enqueue an analysis task (future background worker implementation).
        """
        task_data = {
            "task_id": task_id,
            "file_url": file_url,
            "model": model,
        }
        
        logger.info(f"Enqueuing analysis task: {task_id}")
        
        if self.settings.REDIS_ENABLED and self.redis_client:
            await self.redis_client.lpush(
                self.settings.REDIS_QUEUE_NAME,
                json.dumps(task_data)
            )
            return True
        
        return False
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis result for a task.
        """
        logger.info(f"Retrieving result for task: {task_id}")
        
        if self.settings.REDIS_ENABLED and self.redis_client:
            result = await self.redis_client.get(f"result:{task_id}")
            return json.loads(result) if result else None
        
        return None


# Singleton instance
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Get or create the queue service singleton."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
