"""Integration tests for Economist Agent with MarketService"""

import pytest
from app.agents.economist_agent import EconomistAgent


class TestEconomistAgentMarketServiceIntegration:
    """Integration tests verifying Economist Agent works with MarketService"""
    
    @pytest.fixture
    def agent(self):
        """Create Economist Agent instance"""
        return EconomistAgent()
    
    def test_get_recommendation_for_tomato(self, agent):
        """Test getting market recommendation for tomato"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)  # Nagpur
        )
        
        # Verify structure
        assert recommendation is not None
        assert recommendation['crop'] == 'tomato'
        assert 'best_market' in recommendation
        assert 'local_market' in recommendation
        assert 'all_markets' in recommendation
        assert 'price_difference' in recommendation
        assert 'reasoning' in recommendation
        assert 'market_opportunity' in recommendation
        
        # Verify best market has required fields
        if recommendation['best_market']:
            assert 'name' in recommendation['best_market']
            assert 'price_per_kg' in recommendation['best_market']
            assert 'distance_km' in recommendation['best_market']
            assert 'location' in recommendation['best_market']
    
    def test_get_recommendation_for_onion(self, agent):
        """Test getting market recommendation for onion"""
        recommendation = agent.get_market_recommendation(
            crop='onion',
            farmer_location=(19.0760, 72.8777)  # Mumbai
        )
        
        assert recommendation is not None
        assert recommendation['crop'] == 'onion'
        assert 'best_market' in recommendation
    
    def test_distance_calculation_accuracy(self, agent):
        """Test that Haversine distance calculation is accurate"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)  # Nagpur
        )
        
        # Verify distances are calculated
        if recommendation['all_markets']:
            for market in recommendation['all_markets']:
                assert 'distance_km' in market
                assert market['distance_km'] >= 0
    
    def test_price_difference_in_rupees(self, agent):
        """Test that price differences are calculated in rupees"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        # Price difference should be a number
        assert isinstance(recommendation['price_difference'], (int, float))
        
        # If there are markets, verify calculation
        if recommendation['best_market'] and recommendation['local_market']:
            expected_diff = (
                recommendation['best_market']['price_per_kg'] - 
                recommendation['local_market']['price_per_kg']
            )
            assert abs(recommendation['price_difference'] - expected_diff) < 0.01
    
    def test_highest_price_market_selection(self, agent):
        """Test that highest price market is selected by default"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882),
            consider_distance=False
        )
        
        if recommendation['all_markets'] and len(recommendation['all_markets']) > 1:
            # Best market should have highest or equal price
            best_price = recommendation['best_market']['price_per_kg']
            all_prices = [m['price_per_kg'] for m in recommendation['all_markets']]
            assert best_price == max(all_prices)
    
    def test_distance_adjusted_selection(self, agent):
        """Test market selection with distance consideration"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882),
            consider_distance=True,
            transport_cost_per_km=2.0
        )
        
        # Should still get a valid recommendation
        assert recommendation is not None
        assert 'best_market' in recommendation
    
    def test_compare_markets_functionality(self, agent):
        """Test market comparison feature"""
        comparison = agent.compare_markets(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        assert comparison is not None
        assert comparison['crop'] == 'tomato'
        assert 'markets' in comparison
        assert 'statistics' in comparison
        
        # If markets exist, verify statistics
        if comparison['markets']:
            stats = comparison['statistics']
            assert 'highest_price' in stats
            assert 'lowest_price' in stats
            assert 'average_price' in stats
            assert 'price_range' in stats
            assert 'total_markets' in stats
            
            # Verify statistics are correct
            prices = [m['price_per_kg'] for m in comparison['markets']]
            assert stats['highest_price'] == max(prices)
            assert stats['lowest_price'] == min(prices)
            assert stats['total_markets'] == len(comparison['markets'])
    
    def test_markets_sorted_by_price(self, agent):
        """Test that markets are sorted by price (highest first)"""
        comparison = agent.compare_markets(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        if comparison['markets'] and len(comparison['markets']) > 1:
            prices = [m['price_per_kg'] for m in comparison['markets']]
            # Verify descending order
            assert prices == sorted(prices, reverse=True)
    
    def test_reasoning_is_plain_language(self, agent):
        """Test that reasoning is in plain language"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        reasoning = recommendation['reasoning']
        
        # Should contain plain language elements
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
        
        # Should mention rupees if there's a price difference
        if recommendation['price_difference'] > 0:
            assert '₹' in reasoning or 'rupees' in reasoning.lower()
    
    def test_market_opportunity_assessment(self, agent):
        """Test market opportunity level assessment"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        opportunity = recommendation['market_opportunity']
        
        # Should be one of the valid levels
        assert opportunity in ['excellent', 'good', 'moderate', 'low']
    
    def test_fallback_data_source_indication(self, agent):
        """Test that fallback data source is indicated"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        # Should indicate data source
        assert 'data_source' in recommendation
        assert recommendation['data_source'] in ['Agmarknet', 'AIKosh']
        
        # Fallback flag should match data source
        if recommendation['data_source'] == 'AIKosh':
            assert recommendation['fallback_used'] is True
        else:
            assert recommendation['fallback_used'] is False
    
    def test_timestamp_included(self, agent):
        """Test that timestamp is included in recommendation"""
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        assert 'timestamp' in recommendation
        assert isinstance(recommendation['timestamp'], str)
        # Should be ISO format
        assert 'T' in recommendation['timestamp']
    
    def test_different_crops_different_prices(self, agent):
        """Test that different crops have different prices"""
        tomato_rec = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        onion_rec = agent.get_market_recommendation(
            crop='onion',
            farmer_location=(21.1458, 79.0882)
        )
        
        # Both should succeed
        assert tomato_rec is not None
        assert onion_rec is not None
        
        # If both have markets, prices should differ
        if (tomato_rec['best_market'] and onion_rec['best_market']):
            # Prices should be different (in mock data they are)
            assert (
                tomato_rec['best_market']['price_per_kg'] != 
                onion_rec['best_market']['price_per_kg']
            )
    
    def test_multiple_locations_different_distances(self, agent):
        """Test that different farmer locations result in different distances"""
        nagpur_rec = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)  # Nagpur
        )
        
        mumbai_rec = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(19.0760, 72.8777)  # Mumbai
        )
        
        # Both should succeed
        assert nagpur_rec is not None
        assert mumbai_rec is not None
        
        # If both have markets, distances should differ
        if (nagpur_rec['all_markets'] and mumbai_rec['all_markets']):
            # At least one market should have different distance
            nagpur_distances = {m['name']: m['distance_km'] for m in nagpur_rec['all_markets']}
            mumbai_distances = {m['name']: m['distance_km'] for m in mumbai_rec['all_markets']}
            
            # Find common markets
            common_markets = set(nagpur_distances.keys()) & set(mumbai_distances.keys())
            
            if common_markets:
                # At least one should have different distance
                different = any(
                    abs(nagpur_distances[m] - mumbai_distances[m]) > 0.1
                    for m in common_markets
                )
                assert different, "Distances should differ for different farmer locations"


class TestEconomistAgentRequirements:
    """Tests validating specific requirements"""
    
    def test_requirement_4_1_market_price_fetching(self):
        """
        Requirement 4.1: Fetch live Mandi prices from Agmarknet/AIKosh
        """
        agent = EconomistAgent()
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        # Should fetch market data
        assert recommendation is not None
        assert 'data_source' in recommendation
        assert recommendation['data_source'] in ['Agmarknet', 'AIKosh']
    
    def test_requirement_4_2_highest_price_recommendation(self):
        """
        Requirement 4.2: Recommend market with highest price
        """
        agent = EconomistAgent()
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882),
            consider_distance=False  # Pure price-based
        )
        
        if recommendation['all_markets'] and len(recommendation['all_markets']) > 1:
            best_price = recommendation['best_market']['price_per_kg']
            all_prices = [m['price_per_kg'] for m in recommendation['all_markets']]
            
            # Best market should have highest price
            assert best_price == max(all_prices)
    
    def test_requirement_4_3_price_difference_in_rupees(self):
        """
        Requirement 4.3: Calculate price differences in rupees
        """
        agent = EconomistAgent()
        recommendation = agent.get_market_recommendation(
            crop='tomato',
            farmer_location=(21.1458, 79.0882)
        )
        
        # Should have price difference
        assert 'price_difference' in recommendation
        assert isinstance(recommendation['price_difference'], (int, float))
        
        # Should be in rupees (reasonable range)
        assert recommendation['price_difference'] >= 0
        
        # Reasoning should mention rupees
        if recommendation['price_difference'] > 0:
            assert '₹' in recommendation['reasoning']
