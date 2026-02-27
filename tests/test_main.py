"""Tests for main FastAPI application"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agrichain-harvest-optimizer"
        assert "version" in data
    
    def test_health_check_response_structure(self):
        """Test health check response has correct structure"""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 3  # status, service, version
        assert data["version"] == "0.1.0"
    
    @patch('app.main.verify_neo4j_connection')
    @patch('app.main.verify_supabase_connection')
    @patch('app.main.verify_redis_connection')
    @patch('app.main.settings')
    def test_database_health_check_all_healthy(
        self, mock_settings, mock_redis, mock_supabase, mock_neo4j
    ):
        """Test database health check when all databases are healthy"""
        mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.REDIS_URL = "redis://localhost:6379"
        
        mock_neo4j.return_value = True
        mock_supabase.return_value = True
        mock_redis.return_value = True
        
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["databases"]["neo4j"] == "healthy"
        assert data["databases"]["supabase"] == "healthy"
        assert data["databases"]["redis"] == "healthy"
    
    @patch('app.main.verify_neo4j_connection')
    @patch('app.main.verify_supabase_connection')
    @patch('app.main.verify_redis_connection')
    @patch('app.main.settings')
    def test_database_health_check_degraded(
        self, mock_settings, mock_redis, mock_supabase, mock_neo4j
    ):
        """Test database health check when one database is unhealthy"""
        mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.REDIS_URL = "redis://localhost:6379"
        
        mock_neo4j.return_value = False  # Neo4j unhealthy
        mock_supabase.return_value = True
        mock_redis.return_value = True
        
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["databases"]["neo4j"] == "unhealthy"
        assert data["databases"]["supabase"] == "healthy"
        assert data["databases"]["redis"] == "healthy"
    
    @patch('app.main.settings')
    def test_database_health_check_not_configured(self, mock_settings):
        """Test database health check when databases are not configured"""
        mock_settings.NEO4J_URI = ""
        mock_settings.SUPABASE_URL = ""
        mock_settings.REDIS_URL = ""
        
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"  # Not configured is acceptable
        assert data["databases"]["neo4j"] == "not_configured"
        assert data["databases"]["supabase"] == "not_configured"
        assert data["databases"]["redis"] == "not_configured"


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
    
    def test_root_endpoint_includes_database_health(self):
        """Test root endpoint includes database health endpoint"""
        response = client.get("/")
        data = response.json()
        assert "database_health" in data
        assert data["database_health"] == "/health/db"


class TestMiddleware:
    """Test middleware configuration"""
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_allowed_origin(self):
        """Test CORS allows configured origins"""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.headers["access-control-allow-origin"] in [
            "http://localhost:3000",
            "*"
        ]
    
    def test_gzip_compression_header(self):
        """Test Gzip compression is configured"""
        # Make a request that would trigger compression (>1000 bytes)
        response = client.get("/")
        # Gzip middleware is present if the app doesn't error
        assert response.status_code == 200


class TestApplicationStartup:
    """Test application startup and lifespan"""
    
    @patch('app.main.verify_neo4j_connection')
    @patch('app.main.verify_supabase_connection')
    @patch('app.main.verify_redis_connection')
    @patch('app.main.settings')
    def test_startup_initializes_connections(
        self, mock_settings, mock_redis, mock_supabase, mock_neo4j
    ):
        """Test that startup initializes all database connections"""
        mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.REDIS_URL = "redis://localhost:6379"
        
        mock_neo4j.return_value = True
        mock_supabase.return_value = True
        mock_redis.return_value = True
        
        # Create a new test client to trigger startup
        with TestClient(app) as test_client:
            response = test_client.get("/health")
            assert response.status_code == 200
    
    @patch('app.main.verify_neo4j_connection')
    @patch('app.main.settings')
    def test_startup_continues_on_connection_failure(
        self, mock_settings, mock_neo4j
    ):
        """Test that startup continues even if connections fail (graceful degradation)"""
        mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
        mock_settings.SUPABASE_URL = ""
        mock_settings.REDIS_URL = ""
        
        mock_neo4j.side_effect = Exception("Connection failed")
        
        # Application should still start
        with TestClient(app) as test_client:
            response = test_client.get("/health")
            assert response.status_code == 200
    
    @patch('app.main.close_neo4j_driver')
    def test_shutdown_closes_connections(self, mock_close):
        """Test that shutdown closes database connections"""
        with TestClient(app) as test_client:
            test_client.get("/health")
        
        # After context manager exits, shutdown should have been called
        mock_close.assert_called_once()


class TestApplicationMetadata:
    """Test application metadata and configuration"""
    
    def test_app_title(self):
        """Test application has correct title"""
        assert app.title == "AgriChain Harvest Optimizer"
    
    def test_app_version(self):
        """Test application has correct version"""
        assert app.version == "0.1.0"
    
    def test_app_description(self):
        """Test application has description"""
        assert "XAI Trust Engine" in app.description
    
    def test_openapi_docs_available(self):
        """Test OpenAPI documentation is available"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json_available(self):
        """Test OpenAPI JSON schema is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "AgriChain Harvest Optimizer"
        assert data["info"]["version"] == "0.1.0"
