"""Cache management API endpoints"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query

from app.models.requests import CachePrefetchRequest
from app.models.responses import CacheStatusResponse, CachePrefetchResponse
from app.agents.geospatial_agent import GeospatialAgent
from app.tasks.satellite_tasks import fetch_satellite_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get(
    "/status",
    response_model=CacheStatusResponse,
    summary="Check cache status for a location",
    description="""
    Check if satellite data is cached for a specific location and when it expires.
    
    This endpoint queries the Supabase satellite_cache table and returns:
    - Whether data is cached for the location
    - When the data was last updated
    - Age of the cached data in hours
    - Time until cache expiration in hours
    
    Requirements: 8.2
    """,
    responses={
        200: {
            "description": "Cache status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "cached": True,
                        "last_updated": "2024-01-15T10:30:00Z",
                        "data_age": 12.5,
                        "expires_in": 155.5
                    }
                }
            },
        },
        400: {"description": "Invalid location coordinates"},
        500: {"description": "Internal server error"},
    },
)
async def get_cache_status(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
):
    """
    Get cache status for a specific location.
    
    Args:
        latitude: Location latitude (-90 to 90)
        longitude: Location longitude (-180 to 180)
        
    Returns:
        CacheStatusResponse with cache metadata
        
    Raises:
        HTTPException: If query fails or invalid coordinates
    """
    try:
        logger.info(f"Checking cache status for location ({latitude}, {longitude})")
        
        # Use GeospatialAgent to check cache
        agent = GeospatialAgent()
        cached_data = await agent.get_cached_data(latitude, longitude)
        
        if cached_data:
            # Parse timestamps
            created_at = datetime.fromisoformat(
                cached_data['created_at'].replace('Z', '+00:00')
            )
            expires_at = datetime.fromisoformat(
                cached_data['expires_at'].replace('Z', '+00:00')
            )
            now = datetime.now(timezone.utc)
            
            # Calculate age and expiration time in hours
            data_age_hours = (now - created_at).total_seconds() / 3600
            expires_in_hours = (expires_at - now).total_seconds() / 3600
            
            response = CacheStatusResponse(
                cached=True,
                last_updated=created_at.isoformat(),
                data_age=round(data_age_hours, 2),
                expires_in=round(expires_in_hours, 2),
            )
            
            logger.info(
                f"Cache found: age={data_age_hours:.1f}h, expires_in={expires_in_hours:.1f}h"
            )
        else:
            # No cached data found
            response = CacheStatusResponse(
                cached=False,
                last_updated=None,
                data_age=None,
                expires_in=None,
            )
            
            logger.info("No cached data found")
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid coordinates: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid coordinates: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error checking cache status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check cache status",
        )



@router.post(
    "/prefetch",
    response_model=CachePrefetchResponse,
    summary="Trigger async satellite data prefetch",
    description="""
    Trigger asynchronous prefetch of satellite data for a specific location.
    
    This endpoint queues a Celery task to fetch satellite data from Google Earth Engine
    and cache it in Supabase. The task is queued with the specified priority level:
    - high: Real-time farmer requests (priority 10)
    - normal: Demo location prefetch (priority 5)
    - low: Background cache refresh (priority 1)
    
    Returns a task ID that can be used to track the progress of the prefetch operation.
    
    Requirements: 8.5
    """,
    responses={
        200: {
            "description": "Prefetch task queued successfully",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "status": "queued",
                        "estimated_time": 30
                    }
                }
            },
        },
        400: {"description": "Invalid location coordinates"},
        500: {"description": "Internal server error"},
    },
)
async def prefetch_satellite_data(request: CachePrefetchRequest):
    """
    Trigger async satellite data prefetch for a location.
    
    Args:
        request: CachePrefetchRequest with latitude, longitude, and priority
        
    Returns:
        CachePrefetchResponse with task ID, status, and estimated time
        
    Raises:
        HTTPException: If task queueing fails or invalid coordinates
    """
    try:
        logger.info(
            f"Queueing prefetch task for location ({request.latitude}, {request.longitude}) "
            f"with priority: {request.priority}"
        )
        
        # Queue Celery task with priority
        # The task routing is configured in celery_app.py to use the appropriate queue
        task = fetch_satellite_data.apply_async(
            args=[request.latitude, request.longitude, request.priority],
            queue=request.priority,  # Route to high/normal/low queue
            priority={"high": 10, "normal": 5, "low": 1}[request.priority]
        )
        
        # Estimate time based on priority and typical processing time
        # High priority: ~15-30 seconds
        # Normal priority: ~30-60 seconds
        # Low priority: ~60-120 seconds
        estimated_times = {
            "high": 30,
            "normal": 60,
            "low": 120
        }
        estimated_time = estimated_times[request.priority]
        
        response = CachePrefetchResponse(
            task_id=task.id,
            status="queued",
            estimated_time=estimated_time
        )
        
        logger.info(
            f"Prefetch task queued successfully: task_id={task.id}, "
            f"priority={request.priority}, estimated_time={estimated_time}s"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid coordinates: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid coordinates: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error queueing prefetch task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue prefetch task",
        )
