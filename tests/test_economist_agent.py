"""Unit tests for Economist Agent"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.agents.economist_agent import EconomistAgent


class TestEconomistAgent:
    """Test suite for Economist Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create Economist Agent instance"""
        return EconomistAgent()
    
    @pytest.fixture
    def mock_markets(self):
        """Mock market data"""
        return [
            {
                'name': 'Nagpur Mandi',
                'location': {'latitude': 21.1458, 'longitude': 79.0882},
                'price_per_kg': 25.0,
                'distance_km': 10.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'Agmarknet'
            },
            {
                'name': 'Mumbai APMC',
                'location': {'latitude': 19.0760, 'longitude': 72.8777},
                'price_per_kg': 30.0,
                'distance_km': 150.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'Agmarknet'
            },
            {
                'name': 'Pune Market Yard',
                'location': {'latitude': 18.5204, 'longitude': 73.8567},
                'price_per_kg': 28.0,
                'distance_km': 120.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'Agmarknet'
            }
        ]
    
    def test_initialization(self, agent):
        """Test agent initialization"""
        assert agent is not None
        assert agent.market_service is not None
    
    def test_select_highest_price_market(self, agent, mock_markets):
        """Test selecting market with highest price"""
        best = agent._select_highest_price_market(mock_markets)
        
        assert best['name'] == 'Mumbai APMC'
        assert best['price_per_kg'] == 30.0
    
    def test_select_best_market_with_distance(self, agent, mock_markets):
        """Test selecting market with distance consideration"""
        # With transport cost of 0.1 per km:
        # Nagpur: 25.0 - (10.0 * 0.1) = 24.0
        # Mumbai: 30.0 - (150.0 * 0.1) = 15.0
        # Pune: 28.0 - (120.0 * 0.1) = 16.0
        # Best should be Nagpur
        
        best = agent._select_best_market_with_distance(mock_markets, 0.1)
        
        assert best['name'] == 'Nagpur Mandi'
        assert best['price_per_kg'] == 25.0
    
    def test_assess_market_opportunity(self, agent):
        """Test market opportunity assessment"""
        assert agent._assess_market_opportunity(15.0) == 'excellent'
        assert agent._assess_market_opportunity(7.0) == 'good'
        assert agent._assess_market_opportunity(3.0) == 'moderate'
        assert agent._assess_market_opportunity(1.0) == 'low'
    
    def test_format_markets_for_display(self, agent, mock_markets):
        """Test market formatting and sorting"""
        formatted = agent._format_markets_for_display(mock_markets)
        
        # Should be sorted by price (highest first)
        assert len(formatted) == 3
        assert formatted[0]['name'] == 'Mumbai APMC'
        assert formatted[0]['price_per_kg'] == 30.0
        assert formatted[1]['name'] == 'Pune Market Yard'
        assert formatted[1]['price_per_kg'] == 28.0
        assert formatted[2]['name'] == 'Nagpur Mandi'
        assert formatted[2]['price_per_kg'] == 25.0
    
    def test_generate_reasoning_best_is_local(self, agent):
        """Test reasoning when best market is local"""
        best_market = {
            'name': 'Local Mandi',
            'price_per_kg': 30.0,
            'distance_km': 5.0
        }
        local_market = best_market
        
        reasoning = agent._generate_reasoning(
            best_market,
            local_market,
            price_diff=0.0,
            consider_distance=False
        )
        
        assert 'Local Mandi' in reasoning
        assert 'best price' in reasoning
    
    def test_generate_reasoning_better_market_exists(self, agent):
        """Test reasoning when better market exists"""
        best_market = {
            'name': 'Mumbai APMC',
            'price_per_kg': 30.0,
            'distance_km': 150.0
        }
        local_market = {
            'name': 'Local Mandi',
            'price_per_kg': 25.0,
            'distance_km': 5.0
        }
        
        reasoning = agent._generate_reasoning(
            best_market,
            local_market,
            price_diff=5.0,
            consider_distance=False
        )
        
        assert 'Mumbai APMC' in reasoning
        assert '₹5.00' in reasoning
        assert 'Local Mandi' in reasoning
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_get_market_recommendation_success(self, mock_get_data, agent, mock_markets):
        """Test successful market recommendation"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': mock_markets,
            'fallback_used': False,
            'last_updated': datetime.now().isoformat()
        }
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert recommendation['crop'] == 'tomato'
        assert recommendation['best_market']['name'] == 'Mumbai APMC'
        assert recommendation['best_market']['price_per_kg'] == 30.0
        assert recommendation['price_difference'] == 5.0  # 30 - 25
        assert recommendation['market_opportunity'] == 'good'
        assert recommendation['fallback_used'] is False
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_get_market_recommendation_with_distance(self, mock_get_data, agent, mock_markets):
        """Test market recommendation with distance consideration"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': mock_markets,
            'fallback_used': False,
            'last_updated': datetime.now().isoformat()
        }
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.0, 79.0),
            consider_distance=True,
            transport_cost_per_km=0.1
        )
        
        # With distance, Nagpur should be best (25 - 1 = 24 vs Mumbai 30 - 15 = 15)
        assert recommendation['best_market']['name'] == 'Nagpur Mandi'
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_get_market_recommendation_no_markets(self, mock_get_data, agent):
        """Test recommendation when no markets available"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': [],
            'fallback_used': False,
            'last_updated': datetime.now().isoformat()
        }
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert recommendation['best_market'] is None
        assert recommendation['price_difference'] == 0.0
        assert 'No market data available' in recommendation['reasoning']
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_get_market_recommendation_with_fallback(self, mock_get_data, agent, mock_markets):
        """Test recommendation with fallback data source"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': mock_markets,
            'fallback_used': True,
            'last_updated': datetime.now().isoformat()
        }
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert recommendation['fallback_used'] is True
        assert recommendation['data_source'] == 'AIKosh'
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_get_market_recommendation_error_handling(self, mock_get_data, agent):
        """Test error handling in market recommendation"""
        mock_get_data.side_effect = Exception("API Error")
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert recommendation['best_market'] is None
        assert 'Error fetching market data' in recommendation['reasoning']
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_compare_markets_success(self, mock_get_data, agent, mock_markets):
        """Test market comparison functionality"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': mock_markets,
            'fallback_used': False,
            'last_updated': datetime.now().isoformat()
        }
        
        comparison = agent.compare_markets(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert comparison['crop'] == 'tomato'
        assert len(comparison['markets']) == 3
        assert comparison['statistics']['highest_price'] == 30.0
        assert comparison['statistics']['lowest_price'] == 25.0
        assert comparison['statistics']['average_price'] == 27.67
        assert comparison['statistics']['price_range'] == 5.0
        assert comparison['statistics']['total_markets'] == 3
    
    @patch('app.agents.economist_agent.MarketService.get_market_data')
    def test_compare_markets_no_data(self, mock_get_data, agent):
        """Test market comparison with no data"""
        mock_get_data.return_value = {
            'crop': 'tomato',
            'markets': [],
            'fallback_used': False,
            'last_updated': datetime.now().isoformat()
        }
        
        comparison = agent.compare_markets(
            crop='tomato',
            farmer_location=(21.0, 79.0)
        )
        
        assert comparison['markets'] == []
        assert comparison['statistics'] is None
    
    def test_price_difference_calculation(self, agent, mock_markets):
        """Test accurate price difference calculation in rupees"""
        best = agent._select_highest_price_market(mock_markets)
        local = min(mock_markets, key=lambda m: m['distance_km'])
        
        price_diff = best['price_per_kg'] - local['price_per_kg']
        
        # Mumbai (30) - Nagpur (25) = 5 rupees
        assert price_diff == 5.0
    
    def test_recommendation_includes_all_required_fields(self, agent):
        """Test that recommendation includes all required fields"""
        with patch.object(agent.market_service, 'get_market_data') as mock_get_data:
            mock_get_data.return_value = {
                'crop': 'tomato',
                'markets': [
                    {
                        'name': 'Test Mandi',
                        'location': {'latitude': 21.0, 'longitude': 79.0},
                        'price_per_kg': 25.0,
                        'distance_km': 10.0,
                        'last_updated': datetime.now().isoformat(),
                        'source': 'Agmarknet'
                    }
                ],
                'fallback_used': False,
                'last_updated': datetime.now().isoformat()
            }
            
            recommendation = agent.get_market_recommendation(
                crop='tomato',
                farmer_location=(21.0, 79.0)
            )
            
            # Verify all required fields
            required_fields = [
                'crop', 'best_market', 'local_market', 'all_markets',
                'price_difference', 'reasoning', 'market_opportunity',
                'fallback_used', 'data_source', 'timestamp'
            ]
            
            for field in required_fields:
                assert field in recommendation, f"Missing field: {field}"


class TestEconomistAgentIntegration:
    """Integration tests with real MarketService"""
    
    def test_full_recommendation_flow(self):
        """Test complete recommendation flow with real service"""
        agent = EconomistAgent()
        
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)  # Nagpur
        )
        
        # Should get recommendation even with mock data
        assert recommendation is not None
        assert recommendation['crop'] == 'tomato'
        assert 'best_market' in recommendation
        assert 'reasoning' in recommendation
    
    def test_compare_markets_integration(self):
        """Test market comparison with real service"""
        agent = EconomistAgent()
        
        comparison = agent.compare_markets(
            crop='onion',
            farmer_location=(19.0760, 72.8777)  # Mumbai
        )
        
        assert comparison is not None
        assert comparison['crop'] == 'onion'
        assert 'markets' in comparison
        assert 'statistics' in comparison
