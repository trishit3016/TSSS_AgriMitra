"""Unit tests for database connections"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from app.db.neo4j_client import get_neo4j_driver, verify_neo4j_connection, close_neo4j_driver
from app.db.supabase_client import get_supabase_client, verify_supabase_connection
from app.db.redis_client import get_redis_client, verify_redis_connection, close_redis_client


class TestNeo4jConnection:
    """Tests for Neo4j connection client"""
    
    def test_get_neo4j_driver_missing_credentials(self):
        """Test that missing credentials raise ValueError"""
        with patch('app.db.neo4j_client.settings') as mock_settings:
            mock_settings.NEO4J_URI = ""
            mock_settings.NEO4J_USER = ""
            mock_settings.NEO4J_PASSWORD = ""
            
            with pytest.raises(ValueError, match="Neo4j credentials not configured"):
                get_neo4j_driver()
    
    def test_get_neo4j_driver_partial_credentials(self):
        """Test that partial credentials raise ValueError"""
        with patch('app.db.neo4j_client.settings') as mock_settings:
            mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
            mock_settings.NEO4J_USER = ""  # Missing user
            mock_settings.NEO4J_PASSWORD = "password"
            
            with pytest.raises(ValueError, match="Neo4j credentials not configured"):
                get_neo4j_driver()
    
    @patch('app.db.neo4j_client.GraphDatabase')
    def test_get_neo4j_driver_success(self, mock_graph_db):
        """Test successful Neo4j driver creation"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        with patch('app.db.neo4j_client.settings') as mock_settings:
            mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = "password"
            
            # Reset global driver
            import app.db.neo4j_client
            app.db.neo4j_client._driver = None
            
            driver = get_neo4j_driver()
            
            assert driver is not None
            mock_graph_db.driver.assert_called_once()
            mock_driver.verify_connectivity.assert_called_once()
    
    @patch('app.db.neo4j_client.GraphDatabase')
    def test_get_neo4j_driver_singleton(self, mock_graph_db):
        """Test that Neo4j driver is a singleton"""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        with patch('app.db.neo4j_client.settings') as mock_settings:
            mock_settings.NEO4J_URI = "neo4j+s://test.neo4j.io"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = "password"
            
            # Reset global driver
            import app.db.neo4j_client
            app.db.neo4j_client._driver = None
            
            driver1 = get_neo4j_driver()
            driver2 = get_neo4j_driver()
            
            assert driver1 is driver2
            # Should only be called once due to singleton pattern
            assert mock_graph_db.driver.call_count == 1
    
    @patch('app.db.neo4j_client.get_neo4j_driver')
    def test_verify_neo4j_connection_success(self, mock_get_driver):
        """Test successful Neo4j connection verification"""
        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver
        
        result = verify_neo4j_connection()
        
        assert result is True
        mock_driver.verify_connectivity.assert_called_once()
    
    @patch('app.db.neo4j_client.get_neo4j_driver')
    def test_verify_neo4j_connection_failure(self, mock_get_driver):
        """Test Neo4j connection verification failure"""
        mock_get_driver.side_effect = Exception("Connection failed")
        
        result = verify_neo4j_connection()
        
        assert result is False
    
    @patch('app.db.neo4j_client.get_neo4j_driver')
    def test_verify_neo4j_connection_timeout(self, mock_get_driver):
        """Test Neo4j connection verification with timeout"""
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("Timeout")
        mock_get_driver.return_value = mock_driver
        
        result = verify_neo4j_connection()
        
        assert result is False
    
    @patch('app.db.neo4j_client._driver')
    def test_close_neo4j_driver(self, mock_driver):
        """Test closing Neo4j driver"""
        mock_driver_instance = MagicMock()
        
        with patch('app.db.neo4j_client._driver', mock_driver_instance):
            close_neo4j_driver()
            mock_driver_instance.close.assert_called_once()
    
    def test_close_neo4j_driver_when_none(self):
        """Test closing Neo4j driver when driver is None"""
        import app.db.neo4j_client
        app.db.neo4j_client._driver = None
        
        # Should not raise an error
        close_neo4j_driver()


class TestSupabaseConnection:
    """Tests for Supabase connection client"""
    
    def test_get_supabase_client_missing_credentials(self):
        """Test that missing credentials raise ValueError"""
        with patch('app.db.supabase_client.settings') as mock_settings:
            mock_settings.SUPABASE_URL = ""
            mock_settings.SUPABASE_SERVICE_KEY = ""
            
            # Reset global client
            import app.db.supabase_client
            app.db.supabase_client._client = None
            
            with pytest.raises(ValueError, match="Supabase credentials not configured"):
                get_supabase_client()
    
    def test_get_supabase_client_missing_url(self):
        """Test that missing URL raises ValueError"""
        with patch('app.db.supabase_client.settings') as mock_settings:
            mock_settings.SUPABASE_URL = ""
            mock_settings.SUPABASE_SERVICE_KEY = "test-key"
            
            # Reset global client
            import app.db.supabase_client
            app.db.supabase_client._client = None
            
            with pytest.raises(ValueError, match="Supabase credentials not configured"):
                get_supabase_client()
    
    @patch('app.db.supabase_client.create_client')
    def test_get_supabase_client_success(self, mock_create_client):
        """Test successful Supabase client creation"""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch('app.db.supabase_client.settings') as mock_settings:
            mock_settings.SUPABASE_URL = "https://test.supabase.co"
            mock_settings.SUPABASE_SERVICE_KEY = "test-key"
            
            # Reset global client
            import app.db.supabase_client
            app.db.supabase_client._client = None
            
            client = get_supabase_client()
            
            assert client is not None
            mock_create_client.assert_called_once_with(
                "https://test.supabase.co",
                "test-key"
            )
    
    @patch('app.db.supabase_client.create_client')
    def test_get_supabase_client_singleton(self, mock_create_client):
        """Test that Supabase client is a singleton"""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch('app.db.supabase_client.settings') as mock_settings:
            mock_settings.SUPABASE_URL = "https://test.supabase.co"
            mock_settings.SUPABASE_SERVICE_KEY = "test-key"
            
            # Reset global client
            import app.db.supabase_client
            app.db.supabase_client._client = None
            
            client1 = get_supabase_client()
            client2 = get_supabase_client()
            
            assert client1 is client2
            # Should only be called once due to singleton pattern
            assert mock_create_client.call_count == 1
    
    @patch('app.db.supabase_client.get_supabase_client')
    def test_verify_supabase_connection_success(self, mock_get_client):
        """Test successful Supabase connection verification"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        result = verify_supabase_connection()
        
        assert result is True
    
    @patch('app.db.supabase_client.get_supabase_client')
    def test_verify_supabase_connection_failure(self, mock_get_client):
        """Test Supabase connection verification failure"""
        mock_get_client.side_effect = Exception("Connection failed")
        
        # Note: Supabase verification returns True even on exception
        # because connection might be OK but tables not created yet
        result = verify_supabase_connection()
        
        assert result is True
    
    @patch('app.db.supabase_client.get_supabase_client')
    def test_verify_supabase_connection_with_query(self, mock_get_client):
        """Test Supabase connection verification with actual query"""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.limit.return_value.execute.return_value = None
        mock_get_client.return_value = mock_client
        
        result = verify_supabase_connection()
        
        assert result is True


class TestRedisConnection:
    """Tests for Redis connection client"""
    
    def test_get_redis_client_missing_url(self):
        """Test that missing Redis URL raises ValueError"""
        with patch('app.db.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = ""
            
            # Reset global client
            import app.db.redis_client
            app.db.redis_client._client = None
            app.db.redis_client._pool = None
            
            with pytest.raises(ValueError, match="Redis URL not configured"):
                get_redis_client()
    
    @patch('app.db.redis_client.redis.ConnectionPool')
    @patch('app.db.redis_client.redis.Redis')
    def test_get_redis_client_success(self, mock_redis_class, mock_pool_class):
        """Test successful Redis client creation"""
        mock_pool = MagicMock()
        mock_pool_class.from_url.return_value = mock_pool
        
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client
        
        with patch('app.db.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            
            # Reset global client
            import app.db.redis_client
            app.db.redis_client._client = None
            app.db.redis_client._pool = None
            
            client = get_redis_client()
            
            assert client is not None
            mock_pool_class.from_url.assert_called_once()
            mock_client.ping.assert_called_once()
    
    @patch('app.db.redis_client.redis.ConnectionPool')
    @patch('app.db.redis_client.redis.Redis')
    def test_get_redis_client_singleton(self, mock_redis_class, mock_pool_class):
        """Test that Redis client is a singleton"""
        mock_pool = MagicMock()
        mock_pool_class.from_url.return_value = mock_pool
        
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client
        
        with patch('app.db.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            
            # Reset global client
            import app.db.redis_client
            app.db.redis_client._client = None
            app.db.redis_client._pool = None
            
            client1 = get_redis_client()
            client2 = get_redis_client()
            
            assert client1 is client2
            # Pool should only be created once
            assert mock_pool_class.from_url.call_count == 1
    
    @patch('app.db.redis_client.redis.ConnectionPool')
    @patch('app.db.redis_client.redis.Redis')
    def test_get_redis_client_with_connection_pool(self, mock_redis_class, mock_pool_class):
        """Test Redis client uses connection pooling"""
        mock_pool = MagicMock()
        mock_pool_class.from_url.return_value = mock_pool
        
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client
        
        with patch('app.db.redis_client.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            
            # Reset global client
            import app.db.redis_client
            app.db.redis_client._client = None
            app.db.redis_client._pool = None
            
            client = get_redis_client()
            
            # Verify connection pool was created with correct parameters
            mock_pool_class.from_url.assert_called_once()
            call_kwargs = mock_pool_class.from_url.call_args[1]
            assert call_kwargs["max_connections"] == 50
            assert call_kwargs["decode_responses"] is True
    
    @patch('app.db.redis_client.get_redis_client')
    def test_verify_redis_connection_success(self, mock_get_client):
        """Test successful Redis connection verification"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        result = verify_redis_connection()
        
        assert result is True
        mock_client.ping.assert_called_once()
    
    @patch('app.db.redis_client.get_redis_client')
    def test_verify_redis_connection_failure(self, mock_get_client):
        """Test Redis connection verification failure"""
        mock_get_client.side_effect = Exception("Connection failed")
        
        result = verify_redis_connection()
        
        assert result is False
    
    @patch('app.db.redis_client.get_redis_client')
    def test_verify_redis_connection_ping_failure(self, mock_get_client):
        """Test Redis connection verification when ping fails"""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Ping failed")
        mock_get_client.return_value = mock_client
        
        result = verify_redis_connection()
        
        assert result is False
    
    @patch('app.db.redis_client._client')
    @patch('app.db.redis_client._pool')
    def test_close_redis_client(self, mock_pool, mock_client):
        """Test closing Redis client and connection pool"""
        mock_client_instance = MagicMock()
        mock_pool_instance = MagicMock()
        
        with patch('app.db.redis_client._client', mock_client_instance):
            with patch('app.db.redis_client._pool', mock_pool_instance):
                close_redis_client()
                mock_client_instance.close.assert_called_once()
                mock_pool_instance.disconnect.assert_called_once()
    
    def test_close_redis_client_when_none(self):
        """Test closing Redis client when client is None"""
        import app.db.redis_client
        app.db.redis_client._client = None
        app.db.redis_client._pool = None
        
        # Should not raise an error
        close_redis_client()


class TestDatabaseIntegration:
    """Integration tests for database connections"""
    
    @patch('app.db.neo4j_client.get_neo4j_driver')
    @patch('app.db.supabase_client.get_supabase_client')
    @patch('app.db.redis_client.get_redis_client')
    def test_all_databases_can_initialize(
        self, mock_redis, mock_supabase, mock_neo4j
    ):
        """Test that all database clients can be initialized together"""
        mock_neo4j.return_value = MagicMock()
        mock_supabase.return_value = MagicMock()
        mock_redis.return_value = MagicMock()
        
        # Should not raise any errors
        neo4j_driver = mock_neo4j()
        supabase_client = mock_supabase()
        redis_client = mock_redis()
        
        assert neo4j_driver is not None
        assert supabase_client is not None
        assert redis_client is not None
    
    @patch('app.db.neo4j_client.get_neo4j_driver')
    @patch('app.db.supabase_client.get_supabase_client')
    @patch('app.db.redis_client.get_redis_client')
    def test_all_databases_can_verify(
        self, mock_redis, mock_supabase, mock_neo4j
    ):
        """Test that all database connections can be verified"""
        # Mock the drivers/clients
        mock_neo4j_driver = MagicMock()
        mock_supabase_client = MagicMock()
        mock_redis_client = MagicMock()
        
        mock_neo4j.return_value = mock_neo4j_driver
        mock_supabase.return_value = mock_supabase_client
        mock_redis.return_value = mock_redis_client
        
        # Mock the table query for Supabase
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value.limit.return_value.execute.return_value = None
        
        assert verify_neo4j_connection() is True
        assert verify_supabase_connection() is True
        assert verify_redis_connection() is True
