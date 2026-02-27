"""Property-based tests for Geospatial Agent"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime, timedelta, timezone
from app.agents.geospatial_agent import GeospatialAgent


# Feature: agrichain-harvest-optimizer, Property 5: Cache-First Retrieval with Update
# **Validates: Requirements 2.6, 8.2, 8.5, 8.6**


@given(
    lat1=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    lon1=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    lat2=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    lon2=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    date=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 12, 31))
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution, no deadline
def test_cache_key_uniqueness_for_different_locations(lat1, lon1, lat2, lon2, date):
    """
    Property 5: Cache-First Retrieval with Update
    **Validates: Requirements 2.6, 8.2, 8.5, 8.6**
    
    Test that different locations generate unique cache keys.
    For any two different locations, their cache keys must be different.
    """
    agent = GeospatialAgent()
    
    key1 = agent.generate_cache_key(lat1, lon1, date)
    key2 = agent.generate_cache_key(lat2, lon2, date)
    
    # Round coordinates to 8 decimal places for comparison (same as cache key format)
    lat1_rounded = round(lat1, 8)
    lon1_rounded = round(lon1, 8)
    lat2_rounded = round(lat2, 8)
    lon2_rounded = round(lon2, 8)
    
    # If locations are different after rounding, keys must be different
    if (lat1_rounded, lon1_rounded) != (lat2_rounded, lon2_rounded):
        assert key1 != key2, (
            f"Different locations generated same cache key: "
            f"({lat1_rounded}, {lon1_rounded}) and ({lat2_rounded}, {lon2_rounded}) both produced {key1}"
        )
    else:
        # Same location should produce same key
        assert key1 == key2


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    days_old=st.integers(min_value=0, max_value=14)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution, no deadline
def test_cache_expiration_after_7_days(latitude, longitude, days_old):
    """
    Property 5: Cache-First Retrieval with Update
    **Validates: Requirements 2.6, 8.2, 8.5, 8.6**
    
    Test that cache expiration is enforced after 7 days.
    Data older than 7 days should be considered expired.
    """
    agent = GeospatialAgent()
    
    # Create mock cached data with specific age
    created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    cached_data = {
        'created_at': created_at.isoformat(),
        'latitude': latitude,
        'longitude': longitude
    }
    
    is_expired = agent.is_cache_expired(cached_data)
    
    # Data should be expired if >= 7 days old
    if days_old >= 7:
        assert is_expired, f"Data {days_old} days old should be expired"
    else:
        assert not is_expired, f"Data {days_old} days old should not be expired"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    date1=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 12, 31)),
    date2=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 12, 31))
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution, no deadline
def test_cache_key_includes_date(latitude, longitude, date1, date2):
    """
    Property 5: Cache-First Retrieval with Update
    **Validates: Requirements 2.6, 8.2, 8.5, 8.6**
    
    Test that cache keys include date component.
    Same location on different dates should have different cache keys.
    """
    agent = GeospatialAgent()
    
    key1 = agent.generate_cache_key(latitude, longitude, date1)
    key2 = agent.generate_cache_key(latitude, longitude, date2)
    
    # If dates are different (by day), keys must be different
    if date1.date() != date2.date():
        assert key1 != key2, (
            f"Same location on different dates generated same cache key: "
            f"{date1.date()} and {date2.date()} both produced {key1}"
        )
    else:
        # Same date should produce same key
        assert key1 == key2
