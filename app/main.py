"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config.settings import settings
from app.db import (
    get_neo4j_driver,
    close_neo4j_driver,
    get_supabase_client,
    get_redis_client,
)
from app.db.neo4j_client import verify_neo4j_connection
from app.db.supabase_client import verify_supabase_connection
from app.db.redis_client import verify_redis_connection
from app.routers import recommendations, cache, biological_rules, gemini

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting AgriChain Harvest Optimizer...")
    
    # Initialize database connections
    try:
        # Neo4j connection
        if settings.NEO4J_URI:
            logger.info("Initializing Neo4j connection...")
            if verify_neo4j_connection():
                logger.info("✓ Neo4j connection successful")
            else:
                logger.warning("✗ Neo4j connection failed")
        else:
            logger.warning("Neo4j credentials not configured")
        
        # Supabase connection
        if settings.SUPABASE_URL:
            logger.info("Initializing Supabase connection...")
            if verify_supabase_connection():
                logger.info("✓ Supabase connection successful")
            else:
                logger.warning("✗ Supabase connection failed")
        else:
            logger.warning("Supabase credentials not configured")
        
        # Redis connection
        if settings.REDIS_URL:
            logger.info("Initializing Redis connection...")
            if verify_redis_connection():
                logger.info("✓ Redis connection successful")
            else:
                logger.warning("✗ Redis connection failed")
        else:
            logger.warning("Redis URL not configured")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Continue startup even if some connections fail (graceful degradation)
    
    yield
    
    # Shutdown
    logger.info("Shutting down AgriChain Harvest Optimizer...")
    close_neo4j_driver()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="AgriChain Harvest Optimizer",
    description="XAI Trust Engine for harvest timing and market recommendations",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register routers
app.include_router(recommendations.router)
app.include_router(cache.router)
app.include_router(biological_rules.router)
app.include_router(gemini.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agrichain-harvest-optimizer",
        "version": "0.1.0",
    }


@app.get("/health/db")
async def database_health_check():
    """Database connections health check endpoint"""
    status = {
        "neo4j": "not_configured",
        "supabase": "not_configured",
        "redis": "not_configured",
    }
    
    # Check Neo4j
    if settings.NEO4J_URI:
        status["neo4j"] = "healthy" if verify_neo4j_connection() else "unhealthy"
    
    # Check Supabase
    if settings.SUPABASE_URL:
        status["supabase"] = "healthy" if verify_supabase_connection() else "unhealthy"
    
    # Check Redis
    if settings.REDIS_URL:
        status["redis"] = "healthy" if verify_redis_connection() else "unhealthy"
    
    overall_healthy = all(
        v in ["healthy", "not_configured"] for v in status.values()
    )
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "databases": status,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AgriChain Harvest Optimizer API",
        "docs": "/docs",
        "health": "/health",
        "database_health": "/health/db",
    }
