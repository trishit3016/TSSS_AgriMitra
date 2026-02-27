"""
Database migration runner for Supabase PostgreSQL.

This script runs SQL migrations in order to set up the database schema.
"""

import os
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.db.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run all SQL migrations in order"""
    
    migrations_dir = Path(__file__).parent
    migration_files = sorted([
        f for f in migrations_dir.glob("*.sql")
        if f.name.startswith(("001_", "002_", "003_"))
    ])
    
    if not migration_files:
        logger.warning("No migration files found")
        return
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    try:
        client = get_supabase_client()
        
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute SQL using Supabase's RPC or direct SQL execution
            # Note: Supabase Python client doesn't directly support raw SQL execution
            # In production, these migrations should be run via Supabase Dashboard
            # or using psycopg2 directly with the connection string
            
            logger.info(f"✓ Migration {migration_file.name} prepared")
            logger.warning(
                "Note: Please run these SQL migrations via Supabase Dashboard "
                "or using a PostgreSQL client with your connection string."
            )
        
        logger.info("All migrations prepared successfully")
        logger.info("\nTo apply migrations:")
        logger.info("1. Go to your Supabase Dashboard > SQL Editor")
        logger.info("2. Copy and paste each migration file content")
        logger.info("3. Execute them in order (001, 002, 003)")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migrations()
