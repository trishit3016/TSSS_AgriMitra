"""Geospatial Agent for satellite and weather data integration"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging

from app.db.supabase_client import get_supabase_client
from app.config.settings import settings

logger = logging.getLogger(__name__)


class GeospatialAgent:
    """
    Geospatial Agent responsible for:
    - Fetching and processing satellite data (NDVI, soil moisture, rainfall)
    - Integrating weather forecasts
    - Assessing crop readiness
    - Managing caching layer with 7-day TTL
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.cache_ttl_days = settings.CACHE_TTL_DAYS
    
    def generate_cache_key(self, latitude: float, longitude: float, date: datetime) -> str:
        """
        Generate cache key in format: lat_lon_date
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date: Date for the data
            
        Returns:
            Cache key string
        """
        date_str = date.strftime("%Y-%m-%d")
        return f"{latitude:.8f}_{longitude:.8f}_{date_str}"
    
    def is_cache_expired(self, cached_data: Dict[str, Any]) -> bool:
        """
        Check if cached data has expired (>7 days old)
        
        Args:
            cached_data: Cached data dictionary with 'created_at' field
            
        Returns:
            True if expired, False otherwise
        """
        if not cached_data or 'created_at' not in cached_data:
            return True
        
        created_at = datetime.fromisoformat(cached_data['created_at'].replace('Z', '+00:00'))
        age = datetime.now(timezone.utc) - created_at
        
        return age.days >= self.cache_ttl_days
    
    async def get_cached_data(
        self,
        latitude: float,
        longitude: float,
        date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached satellite data from Supabase.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date: Date for the data (defaults to today)
            
        Returns:
            Cached data dictionary or None if not found/expired
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        try:
            # Query cache by location and date
            response = self.supabase.table('satellite_cache').select('*').eq(
                'latitude', Decimal(str(latitude))
            ).eq(
                'longitude', Decimal(str(longitude))
            ).eq(
                'date', date.date()
            ).execute()
            
            if response.data and len(response.data) > 0:
                cached_data = response.data[0]
                
                # Check if expired
                if self.is_cache_expired(cached_data):
                    logger.info(f"Cache expired for location ({latitude}, {longitude})")
                    return None
                
                logger.info(f"Cache hit for location ({latitude}, {longitude})")
                return cached_data
            
            logger.info(f"Cache miss for location ({latitude}, {longitude})")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached data: {e}")
            return None
    
    async def update_cache(
        self,
        latitude: float,
        longitude: float,
        date: datetime,
        ndvi: float,
        soil_moisture: float,
        rainfall_mm: float,
        data_sources: Dict[str, Any]
    ) -> bool:
        """
        Update cache with new satellite data.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date: Date for the data
            ndvi: NDVI value (0.0-1.0)
            soil_moisture: Soil moisture percentage (0-100)
            rainfall_mm: Rainfall in millimeters
            data_sources: Dictionary of data source metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.cache_ttl_days)
            
            cache_data = {
                'latitude': Decimal(str(latitude)),
                'longitude': Decimal(str(longitude)),
                'date': date.date().isoformat(),
                'ndvi': Decimal(str(ndvi)),
                'soil_moisture': Decimal(str(soil_moisture)),
                'rainfall_mm': Decimal(str(rainfall_mm)),
                'data_sources': data_sources,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            # Upsert: insert or update if exists
            self.supabase.table('satellite_cache').upsert(
                cache_data,
                on_conflict='latitude,longitude,date'
            ).execute()
            
            logger.info(f"Cache updated for location ({latitude}, {longitude})")
            return True
            
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            return False
    
    async def get_geospatial_data(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Get geospatial data with cache-first retrieval pattern.
        
        This is the main entry point for the Geospatial Agent.
        It checks cache first, then triggers async fetch if needed.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            Dictionary containing geospatial data
        """
        # Check cache first
        cached_data = await self.get_cached_data(latitude, longitude)
        
        if cached_data:
            return {
                'ndvi': float(cached_data['ndvi']),
                'soil_moisture': float(cached_data['soil_moisture']),
                'rainfall_mm': float(cached_data['rainfall_mm']),
                'data_sources': cached_data['data_sources'],
                'cached': True,
                'cache_age_days': (
                    datetime.now(timezone.utc) - 
                    datetime.fromisoformat(cached_data['created_at'].replace('Z', '+00:00'))
                ).days
            }
        
        # If not cached, return placeholder and trigger async fetch
        # In production, this would trigger a Celery task
        logger.warning(
            f"No cached data for location ({latitude}, {longitude}). "
            "Async fetch should be triggered."
        )
        
        return {
            'ndvi': None,
            'soil_moisture': None,
            'rainfall_mm': None,
            'data_sources': {},
            'cached': False,
            'message': 'Data fetch in progress'
        }
