"""Tests for Pydantic models"""

import pytest
from pydantic import ValidationError

from app.models.requests import Location, RecommendationRequest


def test_location_valid():
    """Test valid location coordinates"""
    location = Location(latitude=21.1458, longitude=79.0882)
    assert location.latitude == 21.1458
    assert location.longitude == 79.0882


def test_location_invalid_latitude():
    """Test invalid latitude raises validation error"""
    with pytest.raises(ValidationError):
        Location(latitude=100, longitude=79.0882)


def test_location_invalid_longitude():
    """Test invalid longitude raises validation error"""
    with pytest.raises(ValidationError):
        Location(latitude=21.1458, longitude=200)


def test_recommendation_request_valid():
    """Test valid recommendation request"""
    request = RecommendationRequest(
        farmer_id="test_farmer_1",
        location=Location(latitude=21.1458, longitude=79.0882),
        crop="tomato",
        field_size=2.5,
        language="en"
    )
    assert request.farmer_id == "test_farmer_1"
    assert request.crop == "tomato"
    assert request.field_size == 2.5


def test_recommendation_request_india_bounds():
    """Test location must be within India"""
    with pytest.raises(ValidationError) as exc_info:
        RecommendationRequest(
            farmer_id="test_farmer_1",
            location=Location(latitude=50.0, longitude=79.0882),  # Outside India
            crop="tomato",
            field_size=2.5
        )
    assert "India" in str(exc_info.value)


def test_recommendation_request_invalid_crop():
    """Test invalid crop type raises validation error"""
    with pytest.raises(ValidationError):
        RecommendationRequest(
            farmer_id="test_farmer_1",
            location=Location(latitude=21.1458, longitude=79.0882),
            crop="wheat",  # Not supported
            field_size=2.5
        )


def test_recommendation_request_invalid_field_size():
    """Test invalid field size raises validation error"""
    with pytest.raises(ValidationError):
        RecommendationRequest(
            farmer_id="test_farmer_1",
            location=Location(latitude=21.1458, longitude=79.0882),
            crop="tomato",
            field_size=0  # Must be > 0
        )
