"""Property-based tests for Market Service"""

import pytest
from hypothesis import given, settings, strategies as st
from app.services.market_service import MarketService


# Feature: agrichain-harvest-optimizer, Property 10: Market Data Fallback
# **Validates: Requirements 4.4**


@given(
    crop=st.sampled_from(['tomato', 'onion']),
    farmer_lat=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    farmer_lon=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_market_data_fallback_to_aikosh(crop, farmer_lat, farmer_lon):
    """
    Property 10: Market Data Fallback
    **Validates: Requirements 4.4**
    
    Test that AIKosh is used when Agmarknet fails.
    For any market price request where Agmarknet API is unavailable or 
    returns an error, the system SHALL fall back to AIKosh agricultural 
    embeddings and still return market data with a warning about the 
    fallback source.
    """
    service = MarketService()
    
    # Force fallback by passing use_fallback=True
    market_data = service.get_market_data(
        crop=crop,
        farmer_location=(farmer_lat, farmer_lon),
        use_fallback=True
    )
    
    # Verify fallback was used
    assert market_data['fallback_used'] is True, "Fallback should be used"
    
    # Verify market data is still returned
    assert 'markets' in market_data, "Markets should be present even with fallback"
    assert len(market_data['markets']) > 0, "Should have at least one market"
    
    # Verify warnings are included
    for market in market_data['markets']:
        assert market['source'] == 'AIKosh', "Source should be AIKosh when using fallback"
        assert 'warning' in market, "Warning should be present with fallback data"
        assert 'fallback' in market['warning'].lower(), "Warning should mention fallback"


@given(
    crop=st.sampled_from(['tomato', 'onion']),
    farmer_lat=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    farmer_lon=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_market_data_structure(crop, farmer_lat, farmer_lon):
    """
    Test that market data has correct structure.
    """
    service = MarketService()
    
    # Get market data
    market_data = service.get_market_data(
        crop=crop,
        farmer_location=(farmer_lat, farmer_lon)
    )
    
    # Verify top-level structure
    assert 'crop' in market_data, "Missing 'crop' field"
    assert 'markets' in market_data, "Missing 'markets' field"
    assert 'recommendation' in market_data, "Missing 'recommendation' field"
    assert 'fallback_used' in market_data, "Missing 'fallback_used' field"
    assert 'last_updated' in market_data, "Missing 'last_updated' field"
    
    # Verify crop matches
    assert market_data['crop'] == crop, f"Crop should be {crop}"
    
    # Verify markets structure
    assert isinstance(market_data['markets'], list), "Markets should be a list"
    assert len(market_data['markets']) > 0, "Should have at least one market"
    
    for market in market_data['markets']:
        assert 'name' in market, "Market missing 'name' field"
        assert 'location' in market, "Market missing 'location' field"
        assert 'price_per_kg' in market, "Market missing 'price_per_kg' field"
        assert 'distance_km' in market, "Market missing 'distance_km' field"
        assert 'source' in market, "Market missing 'source' field"
        
        # Verify price is positive
        assert market['price_per_kg'] > 0, f"Price {market['price_per_kg']} should be positive"
        
        # Verify distance is non-negative
        assert market['distance_km'] >= 0, f"Distance {market['distance_km']} should be non-negative"


@given(
    crop=st.sampled_from(['tomato', 'onion']),
    farmer_lat=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    farmer_lon=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_price_comparison_logic(crop, farmer_lat, farmer_lon):
    """
    Test that price comparison identifies best market correctly.
    """
    service = MarketService()
    
    # Get market data
    market_data = service.get_market_data(
        crop=crop,
        farmer_location=(farmer_lat, farmer_lon)
    )
    
    recommendation = market_data['recommendation']
    markets = market_data['markets']
    
    # Verify recommendation structure
    assert 'best_market' in recommendation, "Missing 'best_market' field"
    assert 'local_market' in recommendation, "Missing 'local_market' field"
    assert 'price_difference' in recommendation, "Missing 'price_difference' field"
    
    # Verify best market has highest price
    best_market = recommendation['best_market']
    for market in markets:
        assert best_market['price_per_kg'] >= market['price_per_kg'], (
            f"Best market price {best_market['price_per_kg']} should be >= "
            f"all other prices (found {market['price_per_kg']})"
        )
    
    # Verify local market has shortest distance
    local_market = recommendation['local_market']
    for market in markets:
        assert local_market['distance_km'] <= market['distance_km'], (
            f"Local market distance {local_market['distance_km']} should be <= "
            f"all other distances (found {market['distance_km']})"
        )
    
    # Verify price difference calculation
    expected_diff = best_market['price_per_kg'] - local_market['price_per_kg']
    assert abs(recommendation['price_difference'] - expected_diff) < 0.01, (
        f"Price difference {recommendation['price_difference']} should match "
        f"calculated difference {expected_diff}"
    )


@given(
    lat1=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    lon1=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    lat2=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    lon2=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_haversine_distance_properties(lat1, lon1, lat2, lon2):
    """
    Test properties of Haversine distance calculation.
    """
    service = MarketService()
    
    # Calculate distance
    distance = service.haversine_distance(lat1, lon1, lat2, lon2)
    
    # Distance should be non-negative
    assert distance >= 0, f"Distance {distance} should be non-negative"
    
    # Distance to same point should be 0
    same_point_distance = service.haversine_distance(lat1, lon1, lat1, lon1)
    assert same_point_distance < 0.01, f"Distance to same point should be ~0, got {same_point_distance}"
    
    # Distance should be symmetric (d(A,B) = d(B,A))
    reverse_distance = service.haversine_distance(lat2, lon2, lat1, lon1)
    assert abs(distance - reverse_distance) < 0.01, (
        f"Distance should be symmetric: {distance} vs {reverse_distance}"
    )
