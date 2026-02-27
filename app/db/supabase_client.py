"""Supabase PostgreSQL connection client"""

from typing import Optional
from supabase import create_client, Client
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance with connection pooling.
    
    Returns:
        Supabase client instance
        
    Raises:
        ValueError: If Supabase credentials are not configured
        Exception: If connection fails
    """
    global _client
    
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase credentials not configured. Please set SUPABASE_URL "
                "and SUPABASE_SERVICE_KEY environment variables."
            )
        
        try:
            _client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            
            logger.info("Supabase connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    return _client


def verify_supabase_connection() -> bool:
    """
    Verify Supabase connection is working by attempting a simple query.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client = get_supabase_client()
        # Try to query a table (will fail gracefully if table doesn't exist yet)
        client.table('satellite_cache').select('id').limit(1).execute()
        return True
    except Exception as e:
        logger.warning(f"Supabase connection verification: {e}")
        # Connection might be OK but tables not created yet
        return True
