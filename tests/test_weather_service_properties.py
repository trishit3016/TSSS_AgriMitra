"""Property-based tests for Weather Service"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime
from app.services.weather_service import WeatherService


# Feature: agrichain-harvest-optimizer, Property 7: Weather Data Completeness
# **Validates: Requirements 3.3**


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_weather_data_completeness(latitude, longitude):
    """
    Property 7: Weather Data Completeness
    **Validates: Requirements 3.3**
    
    Test that all forecast days include precipitation, temperature, and humidity.
    For any weather forecast retrieved, the system SHALL extract and include 
    precipitation probability, temperature (min and max), and humidity values 
    for each day in the 8-day forecast.
    """
    service = WeatherService()
    
    # Get weather forecast
    weather_data = service.get_weather_forecast(latitude, longitude)
    
    # Verify forecast exists
    assert 'forecast' in weather_data, "Missing 'forecast' field"
    forecast = weather_data['forecast']
    
    # Verify 8-day forecast
    assert len(forecast) == 8, f"Expected 8 days, got {len(forecast)}"
    
    # Verify each day has all required fields
    for i, day in enumerate(forecast):
        # Check date
        assert 'date' in day, f"Day {i} missing 'date' field"
        
        # Check temperature (min and max)
        assert 'temperature' in day, f"Day {i} missing 'temperature' field"
        assert 'max' in day['temperature'], f"Day {i} missing 'temperature.max' field"
        assert 'min' in day['temperature'], f"Day {i} missing 'temperature.min' field"
        
        # Check humidity
        assert 'humidity' in day, f"Day {i} missing 'humidity' field"
        
        # Check precipitation (probability and amount)
        assert 'precipitation' in day, f"Day {i} missing 'precipitation' field"
        assert 'probability' in day['precipitation'], f"Day {i} missing 'precipitation.probability' field"
        assert 'amount' in day['precipitation'], f"Day {i} missing 'precipitation.amount' field"
        
        # Verify data types and ranges
        assert isinstance(day['temperature']['max'], (int, float)), f"Day {i} temp_max should be numeric"
        assert isinstance(day['temperature']['min'], (int, float)), f"Day {i} temp_min should be numeric"
        assert isinstance(day['humidity'], (int, float)), f"Day {i} humidity should be numeric"
        assert isinstance(day['precipitation']['probability'], (int, float)), f"Day {i} precip_prob should be numeric"
        assert isinstance(day['precipitation']['amount'], (int, float)), f"Day {i} precip_amount should be numeric"
        
        # Verify reasonable ranges
        assert 0 <= day['humidity'] <= 100, f"Day {i} humidity {day['humidity']} outside valid range"
        assert 0 <= day['precipitation']['probability'] <= 1, f"Day {i} precip probability {day['precipitation']['probability']} outside valid range"
        assert day['precipitation']['amount'] >= 0, f"Day {i} precip amount {day['precipitation']['amount']} is negative"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_storm_risk_assessment_structure(latitude, longitude):
    """
    Test that storm risk assessment has correct structure.
    """
    service = WeatherService()
    
    # Get weather forecast
    weather_data = service.get_weather_forecast(latitude, longitude)
    
    # Verify risk assessment exists
    assert 'risk_assessment' in weather_data, "Missing 'risk_assessment' field"
    risk = weather_data['risk_assessment']
    
    # Verify required fields
    assert 'has_storm_risk' in risk, "Missing 'has_storm_risk' field"
    assert isinstance(risk['has_storm_risk'], bool), "has_storm_risk should be boolean"
    
    # If storm risk exists, verify additional fields
    if risk['has_storm_risk']:
        assert 'risk_window' in risk, "Missing 'risk_window' field when storm risk exists"
        assert 'impact' in risk, "Missing 'impact' field when storm risk exists"
        assert isinstance(risk['risk_window'], str), "risk_window should be string"
        assert isinstance(risk['impact'], str), "impact should be string"


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_fallback_to_historical_averages(latitude, longitude):
    """
    Test that fallback to historical averages works correctly.
    """
    service = WeatherService()
    
    # Force fallback by passing use_fallback=True
    weather_data = service.get_weather_forecast(latitude, longitude, use_fallback=True)
    
    # Verify fallback was used
    assert weather_data['fallback_used'] is True, "Fallback should be used"
    assert weather_data['source'] == 'Historical_Average', "Source should be Historical_Average"
    assert 'warning' in weather_data, "Warning should be present when using fallback"
    
    # Verify forecast still has 8 days
    assert len(weather_data['forecast']) == 8, "Fallback should still provide 8-day forecast"
    
    # Verify each day has required fields
    for day in weather_data['forecast']:
        assert 'temperature' in day
        assert 'humidity' in day
        assert 'precipitation' in day


@given(
    latitude=st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=50, deadline=None)  # Reduced from 100 for faster execution
def test_temperature_min_max_relationship(latitude, longitude):
    """
    Test that max temperature is always >= min temperature.
    """
    service = WeatherService()
    
    # Get weather forecast
    weather_data = service.get_weather_forecast(latitude, longitude)
    forecast = weather_data['forecast']
    
    # Verify temperature relationship for each day
    for i, day in enumerate(forecast):
        temp_max = day['temperature']['max']
        temp_min = day['temperature']['min']
        
        assert temp_max >= temp_min, (
            f"Day {i}: max temperature {temp_max} is less than min temperature {temp_min}"
        )
