"""Market data service for Agmarknet and AIKosh integration"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import math
import time

logger = logging.getLogger(__name__)


class MarketService:
    """
    Service for fetching market price data from:
    - Agmarknet API (primary source)
    - AIKosh (fallback source)
    
    Features:
    - Live Mandi price fetching
    - Price comparison across markets
    - Distance calculation from farmer location
    - Retry logic with exponential backoff
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize market service.
        
        Args:
            api_key: Agmarknet API key
        """
        self.api_key = api_key
        self.agmarknet_url = "https://api.data.gov.in/resource/agmarknet"
        self.aikosh_url = "https://aikosh.gov.in/api"
    
    def haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2
            
        Returns:
            Distance in kilometers
        """
        # Earth radius in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def fetch_agmarknet_prices(
        self,
        crop: str,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fetch Mandi prices from Agmarknet with retry logic.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of market price dictionaries
            
        Raises:
            Exception: If all retries fail
        """
        # Placeholder implementation with retry logic
        # In production, this would make HTTP requests to Agmarknet API
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching Agmarknet prices for {crop} (attempt {attempt + 1})")
                
                # Simulate API call
                # In production: response = requests.get(self.agmarknet_url, params={...})
                
                # Mock data for Maharashtra markets
                markets = [
                    {
                        'name': 'Nagpur Mandi',
                        'location': {'latitude': 21.1458, 'longitude': 79.0882},
                        'price_per_kg': 25.0 if crop == 'tomato' else 30.0,
                        'last_updated': datetime.now().isoformat(),
                        'source': 'Agmarknet'
                    },
                    {
                        'name': 'Mumbai APMC',
                        'location': {'latitude': 19.0760, 'longitude': 72.8777},
                        'price_per_kg': 30.0 if crop == 'tomato' else 35.0,
                        'last_updated': datetime.now().isoformat(),
                        'source': 'Agmarknet'
                    },
                    {
                        'name': 'Pune Market Yard',
                        'location': {'latitude': 18.5204, 'longitude': 73.8567},
                        'price_per_kg': 28.0 if crop == 'tomato' else 32.0,
                        'last_updated': datetime.now().isoformat(),
                        'source': 'Agmarknet'
                    }
                ]
                
                return markets
                
            except Exception as e:
                logger.warning(f"Agmarknet attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Agmarknet API failed after {max_retries} attempts")
    
    def fetch_aikosh_prices(
        self,
        crop: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch market prices from AIKosh as fallback.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            
        Returns:
            List of market price dictionaries
        """
        # Placeholder implementation
        # In production, this would query AIKosh agricultural embeddings
        
        logger.info(f"Fetching AIKosh prices for {crop} (fallback)")
        
        # Mock data with slightly lower prices (fallback data may be less current)
        markets = [
            {
                'name': 'Nagpur Mandi',
                'location': {'latitude': 21.1458, 'longitude': 79.0882},
                'price_per_kg': 23.0 if crop == 'tomato' else 28.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'AIKosh',
                'warning': 'Fallback data - may not reflect current prices'
            },
            {
                'name': 'Mumbai APMC',
                'location': {'latitude': 19.0760, 'longitude': 72.8777},
                'price_per_kg': 28.0 if crop == 'tomato' else 33.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'AIKosh',
                'warning': 'Fallback data - may not reflect current prices'
            }
        ]
        
        return markets
    
    def calculate_distances(
        self,
        markets: List[Dict[str, Any]],
        farmer_location: Tuple[float, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate distance from farmer location to each market.
        
        Args:
            markets: List of market dictionaries
            farmer_location: Tuple of (latitude, longitude)
            
        Returns:
            Markets with added 'distance' field
        """
        farmer_lat, farmer_lon = farmer_location
        
        for market in markets:
            market_lat = market['location']['latitude']
            market_lon = market['location']['longitude']
            
            distance = self.haversine_distance(
                farmer_lat, farmer_lon,
                market_lat, market_lon
            )
            
            market['distance_km'] = round(distance, 2)
        
        return markets
    
    def compare_prices(
        self,
        markets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare prices across markets and find best option.
        
        Args:
            markets: List of market dictionaries with prices and distances
            
        Returns:
            Dictionary with best market and price comparison
        """
        if not markets:
            return {
                'best_market': None,
                'price_difference': 0.0,
                'reasoning': 'No market data available'
            }
        
        # Find highest price market
        best_market = max(markets, key=lambda m: m['price_per_kg'])
        
        # Find local market (closest)
        local_market = min(markets, key=lambda m: m['distance_km'])
        
        # Calculate price difference
        price_diff = best_market['price_per_kg'] - local_market['price_per_kg']
        
        return {
            'best_market': best_market,
            'local_market': local_market,
            'price_difference': round(price_diff, 2),
            'reasoning': (
                f"Selling at {best_market['name']} gives ₹{price_diff:.2f} more per kg "
                f"compared to local market {local_market['name']}"
            )
        }
    
    def get_market_data(
        self,
        crop: str,
        farmer_location: Tuple[float, float],
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Get complete market data with price comparison.
        
        This is the main entry point for market data.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            farmer_location: Tuple of (latitude, longitude)
            use_fallback: Whether to force fallback (for testing)
            
        Returns:
            Dictionary containing market data and recommendations
        """
        try:
            if use_fallback:
                raise Exception("Using fallback for testing")
            
            # Fetch from Agmarknet
            markets = self.fetch_agmarknet_prices(crop)
            fallback_used = False
            
        except Exception as e:
            logger.warning(f"Agmarknet unavailable: {e}. Using AIKosh fallback.")
            
            # Fallback to AIKosh
            markets = self.fetch_aikosh_prices(crop)
            fallback_used = True
        
        # Calculate distances
        markets_with_distance = self.calculate_distances(markets, farmer_location)
        
        # Compare prices
        comparison = self.compare_prices(markets_with_distance)
        
        return {
            'crop': crop,
            'markets': markets_with_distance,
            'recommendation': comparison,
            'fallback_used': fallback_used,
            'last_updated': datetime.now().isoformat()
        }
