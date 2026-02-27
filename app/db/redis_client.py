"""Redis connection client for Celery"""

from typing import Optional
import redis
from redis.connection import ConnectionPool
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

_pool: Optional[ConnectionPool] = None
_client: Optional[redis.Redis] = None


def get_redis_pool() -> ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Returns:
        Redis connection pool
    """
    global _pool
    
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
        logger.info("Redis connection pool created")
    
    return _pool


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance with connection pooling.
    
    Returns:
        Redis client instance
        
    Raises:
        ValueError: If Redis URL is not configured
        Exception: If connection fails
    """
    global _client
    
    if _client is None:
        if not settings.REDIS_URL:
            raise ValueError(
                "Redis URL not configured. Please set REDIS_URL environment variable."
            )
        
        try:
            pool = get_redis_pool()
            _client = redis.Redis(connection_pool=pool)
            
            # Verify connectivity
            _client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    return _client


def close_redis_client() -> None:
    """Close Redis client and cleanup connections"""
    global _client, _pool
    
    if _client is not None:
        _client.close()
        _client = None
    
    if _pool is not None:
        _pool.disconnect()
        _pool = None
        logger.info("Redis connection closed")


def verify_redis_connection() -> bool:
    """
    Verify Redis connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection verification failed: {e}")
        return False
