"""Base task classes with error handling and result storage"""

from celery import Task
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """
    Base task class with error handling and result storage in Supabase.
    
    All Celery tasks should inherit from this class to get:
    - Automatic error handling and logging
    - Result storage in Supabase celery_tasks table
    - Retry logic with exponential backoff
    - Task status tracking
    """
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def before_start(self, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        Called before task execution starts.
        Creates task record in Supabase with 'processing' status.
        """
        try:
            supabase = get_supabase_client()
            
            task_data = {
                "task_id": task_id,
                "task_type": self.name,
                "status": "processing",
                "params": {
                    "args": list(args),
                    "kwargs": kwargs
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("celery_tasks").insert(task_data).execute()
            logger.info(f"Task {task_id} started: {self.name}")
            
        except Exception as e:
            logger.error(f"Failed to create task record for {task_id}: {e}")
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        Called when task completes successfully.
        Updates task record in Supabase with 'completed' status and result.
        """
        try:
            supabase = get_supabase_client()
            
            update_data = {
                "status": "completed",
                "result": retval if isinstance(retval, dict) else {"value": str(retval)},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("celery_tasks").update(update_data).eq("task_id", task_id).execute()
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to update task record for {task_id}: {e}")
    
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any
    ) -> None:
        """
        Called when task fails after all retries.
        Updates task record in Supabase with 'failed' status and error details.
        """
        try:
            supabase = get_supabase_client()
            
            update_data = {
                "status": "failed",
                "error": str(exc),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table("celery_tasks").update(update_data).eq("task_id", task_id).execute()
            logger.error(f"Task {task_id} failed: {exc}")
            
        except Exception as e:
            logger.error(f"Failed to update task record for {task_id}: {e}")
    
    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any
    ) -> None:
        """
        Called when task is retried after a failure.
        Logs retry attempt.
        """
        logger.warning(f"Task {task_id} retrying due to: {exc}")


class SatelliteTask(BaseTask):
    """
    Specialized task class for satellite data processing.
    
    Includes additional error handling for:
    - Google Earth Engine API failures
    - Timeout errors
    - Data validation errors
    """
    
    # Longer timeout for satellite data fetching
    time_limit = 300  # 5 minutes
    soft_time_limit = 240  # 4 minutes
    
    def run(self, *args, **kwargs) -> Any:
        """
        Override run method to add satellite-specific error handling.
        """
        raise NotImplementedError("Subclasses must implement run method")


class CacheTask(BaseTask):
    """
    Specialized task class for cache operations.
    
    Lower priority and more lenient error handling since
    cache operations are not critical to system functionality.
    """
    
    # Shorter timeout for cache operations
    time_limit = 60  # 1 minute
    soft_time_limit = 45  # 45 seconds
    
    # Don't retry cache operations as aggressively
    retry_kwargs = {"max_retries": 1}
    
    def run(self, *args, **kwargs) -> Any:
        """
        Override run method to add cache-specific error handling.
        """
        raise NotImplementedError("Subclasses must implement run method")


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve task status from Supabase.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status dictionary or None if not found
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("celery_tasks").select("*").eq("task_id", task_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to retrieve task status for {task_id}: {e}")
        return None


def get_task_result(task_id: str) -> Optional[Any]:
    """
    Retrieve task result from Supabase.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task result or None if not found or not completed
    """
    task_status = get_task_status(task_id)
    
    if task_status and task_status.get("status") == "completed":
        return task_status.get("result")
    
    return None
