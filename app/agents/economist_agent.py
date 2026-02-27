"""Economist Agent for market price analysis and recommendations"""

from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, UTC
import logging

from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


class EconomistAgent:
    """
    Economist Agent responsible for:
    - Fetching live Mandi prices from Agmarknet/AIKosh
    - Calculating distances using Haversine formula
    - Recommending best markets based on price or price-distance adjustment
    - Calculating price differences in rupees
    - Providing market intelligence for farmer decisions
    
    Requirements: 4.1, 4.2, 4.3
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Economist Agent.
        
        Args:
            api_key: Agmarknet API key (optional)
        """
        self.market_service = MarketService(api_key=api_key)
    
    def get_market_recommendation(
        self,
        crop: str,
        farmer_location: Tuple[float, float],
        consider_distance: bool = False,
        transport_cost_per_km: float = 2.0
    ) -> Dict[str, Any]:
        """
        Get market recommendation with price analysis.
        
        This is the main entry point for the Economist Agent.
        Fetches market data, calculates distances, and recommends best market.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            farmer_location: Tuple of (latitude, longitude)
            consider_distance: Whether to adjust for transport costs
            transport_cost_per_km: Cost per km for transport (rupees)
            
        Returns:
            Dictionary containing market recommendation and analysis
            
        Validates: Requirements 4.1, 4.2, 4.3
        """
        try:
            # Fetch market data with distances
            market_data = self.market_service.get_market_data(
                crop=crop,
                farmer_location=farmer_location
            )
            
            markets = market_data['markets']
            
            if not markets:
                logger.warning(f"No market data available for {crop}")
                return {
                    'crop': crop,
                    'best_market': None,
                    'markets': [],
                    'price_difference': 0.0,
                    'reasoning': 'No market data available',
                    'fallback_used': market_data.get('fallback_used', False),
                    'timestamp': datetime.now(UTC).isoformat()
                }
            
            # Select best market based on strategy
            if consider_distance:
                best_market = self._select_best_market_with_distance(
                    markets,
                    transport_cost_per_km
                )
            else:
                best_market = self._select_highest_price_market(markets)
            
            # Find local market (closest)
            local_market = min(markets, key=lambda m: m['distance_km'])
            
            # Calculate price difference
            price_diff = best_market['price_per_kg'] - local_market['price_per_kg']
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                best_market,
                local_market,
                price_diff,
                consider_distance
            )
            
            # Build recommendation
            recommendation = {
                'crop': crop,
                'best_market': {
                    'name': best_market['name'],
                    'location': best_market['location'],
                    'price_per_kg': best_market['price_per_kg'],
                    'distance_km': best_market['distance_km'],
                    'last_updated': best_market['last_updated']
                },
                'local_market': {
                    'name': local_market['name'],
                    'location': local_market['location'],
                    'price_per_kg': local_market['price_per_kg'],
                    'distance_km': local_market['distance_km']
                },
                'all_markets': self._format_markets_for_display(markets),
                'price_difference': round(price_diff, 2),
                'reasoning': reasoning,
                'market_opportunity': self._assess_market_opportunity(price_diff),
                'fallback_used': market_data.get('fallback_used', False),
                'data_source': 'AIKosh' if market_data.get('fallback_used') else 'Agmarknet',
                'timestamp': datetime.now(UTC).isoformat()
            }
            
            logger.info(
                f"Market recommendation for {crop}: "
                f"{best_market['name']} at ₹{best_market['price_per_kg']}/kg "
                f"(₹{price_diff:.2f} more than local)"
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating market recommendation: {e}")
            return {
                'crop': crop,
                'best_market': None,
                'markets': [],
                'price_difference': 0.0,
                'reasoning': f'Error fetching market data: {str(e)}',
                'fallback_used': False,
                'timestamp': datetime.now(UTC).isoformat()
            }
    
    def _select_highest_price_market(
        self,
        markets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select market with highest price per kg.
        
        Args:
            markets: List of market dictionaries
            
        Returns:
            Market with highest price
            
        Validates: Requirements 4.2 (highest-paying market recommendation)
        """
        return max(markets, key=lambda m: m['price_per_kg'])
    
    def _select_best_market_with_distance(
        self,
        markets: List[Dict[str, Any]],
        transport_cost_per_km: float
    ) -> Dict[str, Any]:
        """
        Select market with best net price after transport costs.
        
        Calculates: net_price = price_per_kg - (distance_km * transport_cost_per_km)
        
        Args:
            markets: List of market dictionaries
            transport_cost_per_km: Cost per km for transport
            
        Returns:
            Market with best net price
            
        Validates: Requirements 4.3 (price-distance adjusted recommendation)
        """
        def net_price(market):
            return market['price_per_kg'] - (market['distance_km'] * transport_cost_per_km)
        
        return max(markets, key=net_price)
    
    def _generate_reasoning(
        self,
        best_market: Dict[str, Any],
        local_market: Dict[str, Any],
        price_diff: float,
        consider_distance: bool
    ) -> str:
        """
        Generate plain-language reasoning for market recommendation.
        
        Args:
            best_market: Recommended market
            local_market: Closest market
            price_diff: Price difference in rupees
            consider_distance: Whether distance was considered
            
        Returns:
            Plain-language reasoning string
        """
        if price_diff <= 0:
            return (
                f"Your local market {local_market['name']} offers the best price. "
                f"No need to travel further."
            )
        
        if best_market['name'] == local_market['name']:
            return (
                f"Your local market {local_market['name']} offers the best price "
                f"at ₹{best_market['price_per_kg']}/kg."
            )
        
        distance_text = f" ({best_market['distance_km']:.1f} km away)" if consider_distance else ""
        
        return (
            f"Selling at {best_market['name']}{distance_text} gives you "
            f"₹{price_diff:.2f} more per kg compared to your local market "
            f"{local_market['name']}. "
            f"For a typical harvest, this could mean significant additional income."
        )
    
    def _assess_market_opportunity(self, price_diff: float) -> str:
        """
        Assess market opportunity level based on price difference.
        
        Args:
            price_diff: Price difference in rupees
            
        Returns:
            Opportunity level: 'excellent', 'good', 'moderate', or 'low'
        """
        if price_diff >= 10:
            return 'excellent'
        elif price_diff >= 5:
            return 'good'
        elif price_diff >= 2:
            return 'moderate'
        else:
            return 'low'
    
    def _format_markets_for_display(
        self,
        markets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format markets for UI display, sorted by price (highest first).
        
        Args:
            markets: List of market dictionaries
            
        Returns:
            Formatted and sorted market list
        """
        # Sort by price (highest first)
        sorted_markets = sorted(
            markets,
            key=lambda m: m['price_per_kg'],
            reverse=True
        )
        
        # Format for display
        formatted = []
        for market in sorted_markets:
            formatted.append({
                'name': market['name'],
                'price_per_kg': market['price_per_kg'],
                'distance_km': market['distance_km'],
                'last_updated': market['last_updated']
            })
        
        return formatted
    
    def compare_markets(
        self,
        crop: str,
        farmer_location: Tuple[float, float]
    ) -> Dict[str, Any]:
        """
        Get detailed comparison of all available markets.
        
        Useful for displaying market intelligence to farmers.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            farmer_location: Tuple of (latitude, longitude)
            
        Returns:
            Dictionary with detailed market comparison
        """
        try:
            market_data = self.market_service.get_market_data(
                crop=crop,
                farmer_location=farmer_location
            )
            
            markets = market_data['markets']
            
            if not markets:
                return {
                    'crop': crop,
                    'markets': [],
                    'statistics': None,
                    'timestamp': datetime.now(UTC).isoformat()
                }
            
            # Calculate statistics
            prices = [m['price_per_kg'] for m in markets]
            distances = [m['distance_km'] for m in markets]
            
            statistics = {
                'highest_price': max(prices),
                'lowest_price': min(prices),
                'average_price': round(sum(prices) / len(prices), 2),
                'price_range': round(max(prices) - min(prices), 2),
                'closest_market': min(distances),
                'farthest_market': max(distances),
                'total_markets': len(markets)
            }
            
            return {
                'crop': crop,
                'markets': self._format_markets_for_display(markets),
                'statistics': statistics,
                'fallback_used': market_data.get('fallback_used', False),
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing markets: {e}")
            return {
                'crop': crop,
                'markets': [],
                'statistics': None,
                'error': str(e),
                'timestamp': datetime.now(UTC).isoformat()
            }
