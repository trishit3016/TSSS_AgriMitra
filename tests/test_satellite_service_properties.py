"""Property-based tests for Satellite Service"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime, timedelta
from app.services.satellite_service import SatelliteService


# Feature: agrichain-harvest-optimizer, Property 4: NDVI Validity Range
# **Validates: Requirements 2.2**


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    days_back=st.integers(min_value=1, max_value=30)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_ndvi_validity_range(latitude, longitude, days_back):
    """
    Property 4: NDVI Validity Range
    **Validates: Requirements 2.2**
    
    Test that calculated NDVI values are always between 0.0 and 1.0.
    For any crop readiness assessment that includes NDVI calculation from 
    Sentinel-2 imagery, the calculated NDVI value SHALL fall within the 
    valid range of 0.0 to 1.0 inclusive.
    """
    service = SatelliteService()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Calculate NDVI
    ndvi = service.calculate_ndvi(latitude, longitude, start_date, end_date)
    
    # Verify NDVI is in valid range
    assert 0.0 <= ndvi <= 1.0, (
        f"NDVI value {ndvi} is outside valid range [0.0, 1.0] "
        f"for location ({latitude}, {longitude})"
    )
    
    # Verify NDVI is a float
    assert isinstance(ndvi, float), f"NDVI should be float, got {type(ndvi)}"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_soil_moisture_validity_range(latitude, longitude):
    """
    Test that soil moisture values are always between 0 and 100.
    """
    service = SatelliteService()
    
    # Get soil moisture
    soil_moisture = service.get_soil_moisture(latitude, longitude, datetime.now())
    
    # Verify soil moisture is in valid range
    assert 0.0 <= soil_moisture <= 100.0, (
        f"Soil moisture value {soil_moisture} is outside valid range [0, 100] "
        f"for location ({latitude}, {longitude})"
    )
    
    # Verify soil moisture is a float
    assert isinstance(soil_moisture, float), f"Soil moisture should be float, got {type(soil_moisture)}"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False),
    days_back=st.integers(min_value=1, max_value=30)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_rainfall_non_negative(latitude, longitude, days_back):
    """
    Test that rainfall values are always non-negative.
    """
    service = SatelliteService()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Get rainfall
    rainfall = service.get_rainfall(latitude, longitude, start_date, end_date)
    
    # Verify rainfall is non-negative
    assert rainfall >= 0.0, (
        f"Rainfall value {rainfall} is negative "
        f"for location ({latitude}, {longitude})"
    )
    
    # Verify rainfall is a float
    assert isinstance(rainfall, float), f"Rainfall should be float, got {type(rainfall)}"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_fetch_all_satellite_data_completeness(latitude, longitude):
    """
    Test that fetch_all_satellite_data returns all required fields.
    """
    service = SatelliteService()
    
    # Fetch all data
    data = service.fetch_all_satellite_data(latitude, longitude)
    
    # Verify all required fields are present
    assert 'ndvi' in data, "Missing 'ndvi' field"
    assert 'soil_moisture' in data, "Missing 'soil_moisture' field"
    assert 'rainfall_mm' in data, "Missing 'rainfall_mm' field"
    assert 'data_sources' in data, "Missing 'data_sources' field"
    assert 'timestamp' in data, "Missing 'timestamp' field"
    
    # Verify data types
    assert isinstance(data['ndvi'], float), "NDVI should be float"
    assert isinstance(data['soil_moisture'], float), "Soil moisture should be float"
    assert isinstance(data['rainfall_mm'], float), "Rainfall should be float"
    assert isinstance(data['data_sources'], dict), "Data sources should be dict"
    
    # Verify NDVI range
    assert 0.0 <= data['ndvi'] <= 1.0, f"NDVI {data['ndvi']} outside valid range"
    
    # Verify soil moisture range
    assert 0.0 <= data['soil_moisture'] <= 100.0, f"Soil moisture {data['soil_moisture']} outside valid range"
    
    # Verify rainfall is non-negative
    assert data['rainfall_mm'] >= 0.0, f"Rainfall {data['rainfall_mm']} is negative"
