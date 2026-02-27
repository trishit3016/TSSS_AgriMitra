"""Neo4j AuraDB connection client"""

from typing import Optional
from neo4j import GraphDatabase, Driver
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """
    Get or create Neo4j driver instance with connection pooling.
    
    Returns:
        Neo4j driver instance
        
    Raises:
        ValueError: If Neo4j credentials are not configured
        Exception: If connection fails
    """
    global _driver
    
    if _driver is None:
        neo4j_user = settings.neo4j_user
        
        if not settings.NEO4J_URI or not neo4j_user or not settings.NEO4J_PASSWORD:
            raise ValueError(
                "Neo4j credentials not configured. Please set NEO4J_URI, "
                "NEO4J_USERNAME (or NEO4J_USER), and NEO4J_PASSWORD environment variables."
            )
        
        try:
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(neo4j_user, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
            
            # Verify connectivity
            _driver.verify_connectivity()
            logger.info("Neo4j connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    return _driver


def close_neo4j_driver() -> None:
    """Close Neo4j driver and cleanup connections"""
    global _driver
    
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j connection closed")


def verify_neo4j_connection() -> bool:
    """
    Verify Neo4j connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        return True
    except Exception as e:
        logger.error(f"Neo4j connection verification failed: {e}")
        return False
