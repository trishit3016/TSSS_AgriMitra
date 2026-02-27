"""Tests for POST /api/recommendations endpoint"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_endpoint_exists():
    """Test that the endpoint is registered"""
    response = client.post("/api/recommendations", json={})
    assert response.status_code == 422


def test_location_bounds_latitude_too_low():
    """Test location validation - latitude below India bounds"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 5.0, "longitude": 79.0882},
        "crop": "tomato",
        "field_size": 2.5,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422
    assert "India" in str(response.json())


def test_location_bounds_latitude_too_high():
    """Test location validation - latitude above India bounds"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 40.0, "longitude": 79.0882},
        "crop": "tomato",
        "field_size": 2.5,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422
    assert "India" in str(response.json())


def test_location_bounds_longitude_too_low():
    """Test location validation - longitude below India bounds"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 21.1458, "longitude": 60.0},
        "crop": "tomato",
        "field_size": 2.5,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422
    assert "India" in str(response.json())


def test_location_bounds_longitude_too_high():
    """Test location validation - longitude above India bounds"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 21.1458, "longitude": 100.0},
        "crop": "tomato",
        "field_size": 2.5,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422
    assert "India" in str(response.json())


def test_invalid_crop():
    """Test request validation with invalid crop type"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 21.1458, "longitude": 79.0882},
        "crop": "wheat",
        "field_size": 2.5,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422


def test_field_size_zero():
    """Test field size validation - zero is invalid"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 21.1458, "longitude": 79.0882},
        "crop": "tomato",
        "field_size": 0.0,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422


def test_field_size_too_large():
    """Test field size validation - over 1000 hectares is invalid"""
    request_data = {
        "farmer_id": "test_farmer",
        "location": {"latitude": 21.1458, "longitude": 79.0882},
        "crop": "tomato",
        "field_size": 1500.0,
    }
    response = client.post("/api/recommendations", json=request_data)
    assert response.status_code == 422
