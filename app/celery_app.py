"""Celery application configuration for async task processing"""

from celery import Celery
from kombu import Queue, Exchange
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app instance
celery_app = Celery(
    "agrichain",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.satellite_tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Task routing and priority queues
    task_default_queue="normal",
    task_default_exchange="tasks",
    task_default_exchange_type="direct",
    task_default_routing_key="normal",
    
    # Define priority queues
    task_queues=(
        Queue(
            "high",
            Exchange("tasks", type="direct"),
            routing_key="high",
            queue_arguments={"x-max-priority": 10},
            priority=10
        ),
        Queue(
            "normal",
            Exchange("tasks", type="direct"),
            routing_key="normal",
            queue_arguments={"x-max-priority": 10},
            priority=5
        ),
        Queue(
            "low",
            Exchange("tasks", type="direct"),
            routing_key="low",
            queue_arguments={"x-max-priority": 10},
            priority=1
        ),
    ),
    
    # Task execution limits
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Error handling
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    task_retry_jitter=True,
)

# Task routes - map tasks to specific queues
celery_app.conf.task_routes = {
    "app.tasks.satellite_tasks.fetch_satellite_data": {"queue": "high"},
    "app.tasks.satellite_tasks.process_ndvi": {"queue": "normal"},
    "app.tasks.satellite_tasks.process_soil_moisture": {"queue": "normal"},
    "app.tasks.satellite_tasks.process_rainfall": {"queue": "normal"},
    "app.tasks.satellite_tasks.update_cache": {"queue": "low"},
}

logger.info("Celery app configured with priority queues: high, normal, low")
