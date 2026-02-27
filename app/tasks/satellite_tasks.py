"""Celery tasks for satellite data processing"""

from typing import Dict, Any
from datetime import datetime
import logging
from app.tasks.base import SatelliteTask, CacheTask
from app.celery_app import celery_app
from app.services.satellite_service import SatelliteService
from app.agents.geospatial_agent import GeospatialAgent

logger = logging.getLogger(__name__)


@celery_app.task(base=SatelliteTask, bind=True, name="app.tasks.satellite_tasks.fetch_satellite_data")
async def fetch_satellite_data(self, latitude: float, longitude: float, priority: str = "normal") -> Dict[str, Any]:
    """
    Fetch raw satellite imagery from Google Earth Engine.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        priority: Task priority (high, normal, low)
        
    Returns:
        Dictionary containing raw satellite data
        
    Priority: HIGH (real-time farmer requests)
    """
    logger.info(f"Fetching satellite data for location: ({latitude}, {longitude})")
    
    try:
        # Initialize services
        satellite_service = SatelliteService()
        geospatial_agent = GeospatialAgent()
        
        # Fetch all satellite data
        data = satellite_service.fetch_all_satellite_data(latitude, longitude)
        
        # Update cache
        await geospatial_agent.update_cache(
            latitude=latitude,
            longitude=longitude,
            date=datetime.now(),
            ndvi=data['ndvi'],
            soil_moisture=data['soil_moisture'],
            rainfall_mm=data['rainfall_mm'],
            data_sources=data['data_sources']
        )
        
        return {
            'status': 'success',
            'data': data,
            'cache_updated': True,
            'priority': priority
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch satellite data: {e}")
        raise


@celery_app.task(base=SatelliteTask, bind=True, name="app.tasks.satellite_tasks.process_ndvi")
def process_ndvi(self, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Calculate NDVI from Sentinel-2 bands.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing NDVI values
        
    Priority: NORMAL
    """
    logger.info("Processing NDVI calculation")
    
    try:
        satellite_service = SatelliteService()
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        ndvi = satellite_service.calculate_ndvi(latitude, longitude, start_date, end_date)
        return {'ndvi': ndvi, 'status': 'success'}
        
    except Exception as e:
        logger.error(f"Failed to process NDVI: {e}")
        raise


@celery_app.task(base=SatelliteTask, bind=True, name="app.tasks.satellite_tasks.process_soil_moisture")
def process_soil_moisture(self, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Extract soil moisture from NASA SMAP data.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing soil moisture values
        
    Priority: NORMAL
    """
    logger.info("Processing soil moisture data")
    
    try:
        satellite_service = SatelliteService()
        soil_moisture = satellite_service.get_soil_moisture(latitude, longitude, datetime.now())
        return {'soil_moisture': soil_moisture, 'status': 'success'}
        
    except Exception as e:
        logger.error(f"Failed to process soil moisture: {e}")
        raise


@celery_app.task(base=SatelliteTask, bind=True, name="app.tasks.satellite_tasks.process_rainfall")
def process_rainfall(self, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Aggregate rainfall from CHIRPS data.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing rainfall values
        
    Priority: NORMAL
    """
    logger.info("Processing rainfall data")
    
    try:
        satellite_service = SatelliteService()
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        rainfall = satellite_service.get_rainfall(latitude, longitude, start_date, end_date)
        return {'rainfall_mm': rainfall, 'status': 'success'}
        
    except Exception as e:
        logger.error(f"Failed to process rainfall: {e}")
        raise


@celery_app.task(base=CacheTask, bind=True, name="app.tasks.satellite_tasks.update_cache")
async def update_cache(self, latitude: float, longitude: float, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write processed satellite data to Supabase cache.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        data: Satellite data to cache
        
    Returns:
        Dictionary containing cache update status
        
    Priority: LOW (background cache refresh)
    """
    logger.info(f"Updating cache for location: {latitude}, {longitude}")
    
    try:
        geospatial_agent = GeospatialAgent()
        success = await geospatial_agent.update_cache(
            latitude=latitude,
            longitude=longitude,
            date=datetime.now(),
            ndvi=data.get('ndvi', 0.0),
            soil_moisture=data.get('soil_moisture', 0.0),
            rainfall_mm=data.get('rainfall_mm', 0.0),
            data_sources=data.get('data_sources', {})
        )
        return {'status': 'success' if success else 'failed'}
        
    except Exception as e:
        logger.error(f"Failed to update cache: {e}")
        raise
