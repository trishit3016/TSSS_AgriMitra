"""Tests for cache status endpoint"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    with patch('app.agents.geospatial_agent.get_supabase_client') as mock:
        yield mock.return_value


def test_cache_status_cached_data(mock_supabase_client):
    """Test cache status endpoint with cached data"""
    # Setup mock response
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=12)
    expires_at = now + timedelta(days=6, hours=12)
    
    mock_response = MagicMock()
    mock_response.data = [{
        'id': 'test-id',
        'latitude': Decimal('21.14580000'),
        'longitude': Decimal('79.08820000'),
        'date': now.date().isoformat(),
        'ndvi': Decimal('0.75'),
        'soil_moisture': Decimal('65.0'),
        'rainfall_mm': Decimal('12.5'),
        'data_sources': {'sentinel': 'test'},
        'created_at': created_at.isoformat(),
        'expires_at': expires_at.isoformat(),
    }]
    
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    # Make request
    response = client.get("/api/cache/status?latitude=21.1458&longitude=79.0882")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['cached'] is True
    assert data['last_updated'] is not None
    assert data['data_age'] is not None
    assert data['expires_in'] is not None
    
    # Verify age is approximately 12 hours
    assert 11.5 <= data['data_age'] <= 12.5
    
    # Verify expires_in is approximately 156 hours (6.5 days)
    assert 155 <= data['expires_in'] <= 157


def test_cache_status_no_cached_data(mock_supabase_client):
    """Test cache status endpoint with no cached data"""
    # Setup mock response with empty data
    mock_response = MagicMock()
    mock_response.data = []
    
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    # Make request
    response = client.get("/api/cache/status?latitude=21.1458&longitude=79.0882")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['cached'] is False
    assert data['last_updated'] is None
    assert data['data_age'] is None
    assert data['expires_in'] is None


def test_cache_status_expired_data(mock_supabase_client):
    """Test cache status endpoint with expired cached data"""
    # Setup mock response with expired data (8 days old)
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(days=8)
    expires_at = created_at + timedelta(days=7)
    
    mock_response = MagicMock()
    mock_response.data = [{
        'id': 'test-id',
        'latitude': Decimal('21.14580000'),
        'longitude': Decimal('79.08820000'),
        'date': (now - timedelta(days=8)).date().isoformat(),
        'ndvi': Decimal('0.75'),
        'soil_moisture': Decimal('65.0'),
        'rainfall_mm': Decimal('12.5'),
        'data_sources': {'sentinel': 'test'},
        'created_at': created_at.isoformat(),
        'expires_at': expires_at.isoformat(),
    }]
    
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    # Make request
    response = client.get("/api/cache/status?latitude=21.1458&longitude=79.0882")
    
    # Verify response - expired data should be treated as no cache
    assert response.status_code == 200
    data = response.json()
    
    assert data['cached'] is False
    assert data['last_updated'] is None
    assert data['data_age'] is None
    assert data['expires_in'] is None


def test_cache_status_invalid_latitude():
    """Test cache status endpoint with invalid latitude"""
    response = client.get("/api/cache/status?latitude=100&longitude=79.0882")
    
    assert response.status_code == 422  # Validation error


def test_cache_status_invalid_longitude():
    """Test cache status endpoint with invalid longitude"""
    response = client.get("/api/cache/status?latitude=21.1458&longitude=200")
    
    assert response.status_code == 422  # Validation error


def test_cache_status_missing_parameters():
    """Test cache status endpoint with missing parameters"""
    response = client.get("/api/cache/status")
    
    assert response.status_code == 422  # Validation error


def test_cache_status_database_error(mock_supabase_client):
    """Test cache status endpoint with database error"""
    # Setup mock to raise exception
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("Database error")
    
    # Make request
    response = client.get("/api/cache/status?latitude=21.1458&longitude=79.0882")
    
    # Verify response - GeospatialAgent catches exceptions and returns None,
    # so endpoint treats it as "no cache" (graceful degradation)
    assert response.status_code == 200
    data = response.json()
    assert data['cached'] is False


def test_cache_status_boundary_coordinates(mock_supabase_client):
    """Test cache status endpoint with boundary coordinates"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = []
    
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    # Test minimum valid coordinates
    response = client.get("/api/cache/status?latitude=-90&longitude=-180")
    assert response.status_code == 200
    
    # Test maximum valid coordinates
    response = client.get("/api/cache/status?latitude=90&longitude=180")
    assert response.status_code == 200


def test_cache_status_india_coordinates(mock_supabase_client):
    """Test cache status endpoint with India-specific coordinates"""
    # Setup mock response
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=6)
    expires_at = now + timedelta(days=6, hours=18)
    
    mock_response = MagicMock()
    mock_response.data = [{
        'id': 'test-id',
        'latitude': Decimal('19.07600000'),
        'longitude': Decimal('72.87770000'),
        'date': now.date().isoformat(),
        'ndvi': Decimal('0.68'),
        'soil_moisture': Decimal('72.0'),
        'rainfall_mm': Decimal('8.3'),
        'data_sources': {'sentinel': 'test'},
        'created_at': created_at.isoformat(),
        'expires_at': expires_at.isoformat(),
    }]
    
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    # Test Mumbai coordinates
    response = client.get("/api/cache/status?latitude=19.0760&longitude=72.8777")
    
    assert response.status_code == 200
    data = response.json()
    assert data['cached'] is True



# Tests for POST /api/cache/prefetch endpoint

@pytest.fixture
def mock_celery_task():
    """Mock Celery task"""
    with patch('app.routers.cache.fetch_satellite_data') as mock:
        yield mock


def test_prefetch_success_high_priority(mock_celery_task):
    """Test prefetch endpoint with high priority"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Make request
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 21.1458,
            "longitude": 79.0882,
            "priority": "high"
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['task_id'] == "test-task-id-123"
    assert data['status'] == "queued"
    assert data['estimated_time'] == 30
    
    # Verify task was queued with correct parameters
    mock_celery_task.apply_async.assert_called_once()
    call_args = mock_celery_task.apply_async.call_args
    assert call_args.kwargs['args'] == [21.1458, 79.0882, "high"]
    assert call_args.kwargs['queue'] == "high"
    assert call_args.kwargs['priority'] == 10


def test_prefetch_success_normal_priority(mock_celery_task):
    """Test prefetch endpoint with normal priority"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-456"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Make request
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 19.0760,
            "longitude": 72.8777,
            "priority": "normal"
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['task_id'] == "test-task-id-456"
    assert data['status'] == "queued"
    assert data['estimated_time'] == 60
    
    # Verify task was queued with correct parameters
    mock_celery_task.apply_async.assert_called_once()
    call_args = mock_celery_task.apply_async.call_args
    assert call_args.kwargs['args'] == [19.0760, 72.8777, "normal"]
    assert call_args.kwargs['queue'] == "normal"
    assert call_args.kwargs['priority'] == 5


def test_prefetch_success_low_priority(mock_celery_task):
    """Test prefetch endpoint with low priority"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-789"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Make request
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "priority": "low"
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['task_id'] == "test-task-id-789"
    assert data['status'] == "queued"
    assert data['estimated_time'] == 120
    
    # Verify task was queued with correct parameters
    mock_celery_task.apply_async.assert_called_once()
    call_args = mock_celery_task.apply_async.call_args
    assert call_args.kwargs['args'] == [28.6139, 77.2090, "low"]
    assert call_args.kwargs['queue'] == "low"
    assert call_args.kwargs['priority'] == 1


def test_prefetch_default_priority(mock_celery_task):
    """Test prefetch endpoint with default priority (normal)"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-id-default"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Make request without priority (should default to normal)
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 21.1458,
            "longitude": 79.0882
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['task_id'] == "test-task-id-default"
    assert data['status'] == "queued"
    assert data['estimated_time'] == 60  # Normal priority default
    
    # Verify task was queued with normal priority
    call_args = mock_celery_task.apply_async.call_args
    assert call_args.kwargs['queue'] == "normal"
    assert call_args.kwargs['priority'] == 5


def test_prefetch_invalid_latitude(mock_celery_task):
    """Test prefetch endpoint with invalid latitude"""
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 100,
            "longitude": 79.0882,
            "priority": "high"
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Verify task was not queued
    mock_celery_task.apply_async.assert_not_called()


def test_prefetch_invalid_longitude(mock_celery_task):
    """Test prefetch endpoint with invalid longitude"""
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 21.1458,
            "longitude": 200,
            "priority": "high"
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Verify task was not queued
    mock_celery_task.apply_async.assert_not_called()


def test_prefetch_invalid_priority(mock_celery_task):
    """Test prefetch endpoint with invalid priority"""
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 21.1458,
            "longitude": 79.0882,
            "priority": "urgent"  # Invalid priority
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Verify task was not queued
    mock_celery_task.apply_async.assert_not_called()


def test_prefetch_missing_coordinates(mock_celery_task):
    """Test prefetch endpoint with missing coordinates"""
    response = client.post(
        "/api/cache/prefetch",
        json={
            "priority": "high"
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Verify task was not queued
    mock_celery_task.apply_async.assert_not_called()


def test_prefetch_celery_error(mock_celery_task):
    """Test prefetch endpoint when Celery task queueing fails"""
    # Setup mock to raise exception
    mock_celery_task.apply_async.side_effect = Exception("Celery connection error")
    
    # Make request
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 21.1458,
            "longitude": 79.0882,
            "priority": "high"
        }
    )
    
    # Verify response
    assert response.status_code == 500
    data = response.json()
    assert "Failed to queue prefetch task" in data['detail']


def test_prefetch_boundary_coordinates(mock_celery_task):
    """Test prefetch endpoint with boundary coordinates"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-boundary"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Test minimum valid coordinates
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": -90,
            "longitude": -180,
            "priority": "normal"
        }
    )
    assert response.status_code == 200
    
    # Test maximum valid coordinates
    response = client.post(
        "/api/cache/prefetch",
        json={
            "latitude": 90,
            "longitude": 180,
            "priority": "normal"
        }
    )
    assert response.status_code == 200


def test_prefetch_india_coordinates(mock_celery_task):
    """Test prefetch endpoint with India-specific coordinates"""
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "test-task-india"
    mock_celery_task.apply_async.return_value = mock_task
    
    # Test various India locations
    india_locations = [
        (21.1458, 79.0882),  # Nagpur
        (19.0760, 72.8777),  # Mumbai
        (28.6139, 77.2090),  # Delhi
        (13.0827, 80.2707),  # Chennai
    ]
    
    for lat, lon in india_locations:
        response = client.post(
            "/api/cache/prefetch",
            json={
                "latitude": lat,
                "longitude": lon,
                "priority": "normal"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == "queued"
        assert data['estimated_time'] == 60
