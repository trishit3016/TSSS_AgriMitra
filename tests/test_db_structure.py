"""Tests for database structure and configuration"""

import pytest
from pathlib import Path


class TestDatabaseStructure:
    """Tests for database module structure"""
    
    def test_db_module_exists(self):
        """Test that db module exists"""
        db_path = Path("app/db")
        assert db_path.exists()
        assert db_path.is_dir()
    
    def test_db_init_file_exists(self):
        """Test that db __init__.py exists"""
        init_file = Path("app/db/__init__.py")
        assert init_file.exists()
    
    def test_neo4j_client_exists(self):
        """Test that neo4j_client.py exists"""
        neo4j_file = Path("app/db/neo4j_client.py")
        assert neo4j_file.exists()
    
    def test_supabase_client_exists(self):
        """Test that supabase_client.py exists"""
        supabase_file = Path("app/db/supabase_client.py")
        assert supabase_file.exists()
    
    def test_redis_client_exists(self):
        """Test that redis_client.py exists"""
        redis_file = Path("app/db/redis_client.py")
        assert redis_file.exists()


class TestMigrations:
    """Tests for database migrations"""
    
    def test_migrations_directory_exists(self):
        """Test that migrations directory exists"""
        migrations_path = Path("app/db/migrations")
        assert migrations_path.exists()
        assert migrations_path.is_dir()
    
    def test_satellite_cache_migration_exists(self):
        """Test that satellite_cache migration exists"""
        migration_file = Path("app/db/migrations/001_create_satellite_cache.sql")
        assert migration_file.exists()
        
        # Verify it contains expected table creation
        content = migration_file.read_text()
        assert "CREATE TABLE" in content
        assert "satellite_cache" in content
        assert "ndvi" in content
        assert "soil_moisture" in content
        assert "rainfall_mm" in content
    
    def test_recommendation_history_migration_exists(self):
        """Test that recommendation_history migration exists"""
        migration_file = Path("app/db/migrations/002_create_recommendation_history.sql")
        assert migration_file.exists()
        
        # Verify it contains expected table creation
        content = migration_file.read_text()
        assert "CREATE TABLE" in content
        assert "recommendation_history" in content
        assert "farmer_id" in content
        assert "recommendation" in content
        assert "confidence" in content
    
    def test_celery_tasks_migration_exists(self):
        """Test that celery_tasks migration exists"""
        migration_file = Path("app/db/migrations/003_create_celery_tasks.sql")
        assert migration_file.exists()
        
        # Verify it contains expected table creation
        content = migration_file.read_text()
        assert "CREATE TABLE" in content
        assert "celery_tasks" in content
        assert "task_id" in content
        assert "status" in content
    
    def test_migrations_readme_exists(self):
        """Test that migrations README exists"""
        readme_file = Path("app/db/migrations/README.md")
        assert readme_file.exists()
        
        # Verify it contains instructions
        content = readme_file.read_text()
        assert "Migration Files" in content
        assert "Running Migrations" in content


class TestSettings:
    """Tests for database settings configuration"""
    
    def test_settings_has_database_config(self):
        """Test that settings.py includes database configuration"""
        settings_file = Path("app/config/settings.py")
        content = settings_file.read_text()
        
        # Check for Neo4j settings
        assert "NEO4J_URI" in content
        assert "NEO4J_USER" in content
        assert "NEO4J_PASSWORD" in content
        
        # Check for Supabase settings
        assert "SUPABASE_URL" in content
        assert "SUPABASE_ANON_KEY" in content
        assert "SUPABASE_SERVICE_KEY" in content
        
        # Check for Redis settings
        assert "REDIS_URL" in content
        
        # Check for Celery settings
        assert "CELERY_BROKER_URL" in content
        assert "CELERY_RESULT_BACKEND" in content
    
    def test_env_example_has_database_config(self):
        """Test that .env.example includes database configuration"""
        env_file = Path(".env.example")
        content = env_file.read_text()
        
        # Check for Neo4j configuration
        assert "NEO4J_URI" in content
        assert "NEO4J_USERNAME" in content or "NEO4J_USER" in content
        assert "NEO4J_PASSWORD" in content
        
        # Check for Supabase configuration
        assert "SUPABASE_URL" in content
        assert "SUPABASE_ANON_KEY" in content or "SUPABASE_SERVICE_KEY" in content
        
        # Check for Redis configuration
        assert "REDIS" in content
