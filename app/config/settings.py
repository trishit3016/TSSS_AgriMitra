"""Application settings and environment configuration"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "AgriChain Harvest Optimizer"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database settings
    NEO4J_URI: str = ""
    NEO4J_USER: str = ""
    NEO4J_USERNAME: str = ""  # Alias for NEO4J_USER
    NEO4J_PASSWORD: str = ""
    
    @property
    def neo4j_user(self) -> str:
        """Get Neo4j username from either NEO4J_USER or NEO4J_USERNAME"""
        return self.NEO4J_USER or self.NEO4J_USERNAME
    
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    
    REDIS_URL: str = "redis://localhost:6379"
    
    # External API keys
    GOOGLE_EARTH_ENGINE_KEY: str = ""
    OPENWEATHERMAP_API_KEY: str = ""
    AGMARKNET_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    # Cache settings
    CACHE_TTL_DAYS: int = 7
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
