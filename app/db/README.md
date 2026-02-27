# Database Connections and Schema

This directory contains database connection clients and schema migrations for the AgriChain Harvest Optimizer.

## Overview

The application uses three databases:

1. **Neo4j AuraDB** - Graph database for biological rules and AGROVOC ontology
2. **Supabase PostgreSQL** - Relational database for caching and recommendation history
3. **Redis** - In-memory data store for Celery task queue

## Connection Clients

### Neo4j Client (`neo4j_client.py`)

Manages connections to Neo4j AuraDB with connection pooling.

**Features:**
- Singleton driver pattern for connection reuse
- Connection pooling (max 50 connections)
- Automatic connection verification
- Graceful error handling

**Usage:**
```python
from app.db import get_neo4j_driver

driver = get_neo4j_driver()
with driver.session() as session:
    result = session.run("MATCH (n:Crop) RETURN n LIMIT 10")
    for record in result:
        print(record)
```

**Configuration:**
- `NEO4J_URI` - Neo4j connection URI (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
- `NEO4J_USER` - Neo4j username (usually `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password

### Supabase Client (`supabase_client.py`)

Manages connections to Supabase PostgreSQL with the Supabase Python client.

**Features:**
- Singleton client pattern
- Built-in connection pooling via Supabase client
- Automatic authentication with service key
- RESTful API interface

**Usage:**
```python
from app.db import get_supabase_client

client = get_supabase_client()
response = client.table('satellite_cache').select('*').limit(10).execute()
print(response.data)
```

**Configuration:**
- `SUPABASE_URL` - Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- `SUPABASE_SERVICE_KEY` - Supabase service role key (for backend use)

### Redis Client (`redis_client.py`)

Manages connections to Redis with connection pooling for Celery.

**Features:**
- Connection pooling (max 50 connections)
- Automatic reconnection
- Ping-based health checks
- Decode responses enabled

**Usage:**
```python
from app.db import get_redis_client

client = get_redis_client()
client.set('key', 'value')
value = client.get('key')
print(value)
```

**Configuration:**
- `REDIS_URL` - Redis connection URL (e.g., `redis://localhost:6379` or `redis://:password@host:port`)

## Database Schema

### Supabase Tables

#### 1. satellite_cache

Stores cached satellite data from Google Earth Engine.

**Columns:**
- `id` (UUID) - Primary key
- `latitude` (DECIMAL) - Location latitude
- `longitude` (DECIMAL) - Location longitude
- `date` (DATE) - Data collection date
- `ndvi` (DECIMAL) - Normalized Difference Vegetation Index (0.0-1.0)
- `soil_moisture` (DECIMAL) - Soil moisture percentage (0-100)
- `rainfall_mm` (DECIMAL) - Rainfall in millimeters
- `data_sources` (JSONB) - Source metadata
- `created_at` (TIMESTAMP) - Record creation time
- `expires_at` (TIMESTAMP) - Cache expiration time (7 days)

**Indexes:**
- Location-based: `(latitude, longitude)`
- Expiration: `(expires_at)`
- Composite: `(latitude, longitude, date)`
- Active cache: `(latitude, longitude) WHERE expires_at > NOW()`

**Unique Constraint:** `(latitude, longitude, date)`

#### 2. recommendation_history

Stores historical recommendations for farmers.

**Columns:**
- `id` (UUID) - Primary key
- `farmer_id` (VARCHAR) - Pseudonymized farmer identifier
- `latitude` (DECIMAL) - Location latitude
- `longitude` (DECIMAL) - Location longitude
- `crop` (VARCHAR) - Crop type (tomato, onion)
- `recommendation` (JSONB) - Full recommendation object
- `confidence` (DECIMAL) - Confidence level (0-100)
- `data_quality` (VARCHAR) - Data quality indicator
- `created_at` (TIMESTAMP) - Record creation time

**Indexes:**
- Farmer: `(farmer_id)`
- Date: `(created_at DESC)`
- Farmer + Date: `(farmer_id, created_at DESC)`
- Crop: `(crop)`

#### 3. celery_tasks

Tracks Celery async task execution.

**Columns:**
- `id` (UUID) - Primary key
- `task_id` (VARCHAR) - Celery task UUID
- `task_type` (VARCHAR) - Task type identifier
- `status` (VARCHAR) - Task status (queued, processing, completed, failed)
- `params` (JSONB) - Task input parameters
- `result` (JSONB) - Task result data
- `error` (TEXT) - Error message if failed
- `created_at` (TIMESTAMP) - Task creation time
- `updated_at` (TIMESTAMP) - Last update time (auto-updated)

**Indexes:**
- Task ID: `(task_id)` - Unique
- Status: `(status)`
- Type + Status: `(task_type, status)`
- Created: `(created_at DESC)`

**Triggers:**
- Auto-update `updated_at` on record modification

### Neo4j Graph Schema

The Neo4j schema will be created in a later task (Task 4.1). It will include:

**Node Types:**
- `Crop` - Crop information (tomato, onion)
- `SpoilageRule` - Post-harvest spoilage rules
- `Condition` - Environmental conditions
- `Source` - Data sources (ICAR, AGROVOC)

**Relationships:**
- `HAS_RULE` - Crop to SpoilageRule
- `REQUIRES` - Crop to Condition
- `CITES` - SpoilageRule to Source
- `RELATED_TO` - Crop to Crop
- `BELONGS_TO` - Crop to Category

## Migrations

Database migrations are located in `app/db/migrations/`.

### Running Migrations

See [migrations/README.md](migrations/README.md) for detailed instructions.

**Quick Start:**

1. Copy SQL files to Supabase Dashboard SQL Editor
2. Execute in order: 001, 002, 003
3. Verify tables were created

### Migration Files

- `001_create_satellite_cache.sql` - Satellite data cache table
- `002_create_recommendation_history.sql` - Recommendation history table
- `003_create_celery_tasks.sql` - Celery task tracking table

## Health Checks

The application includes database health check endpoints:

### GET /health/db

Returns the health status of all database connections.

**Response:**
```json
{
  "status": "healthy",
  "databases": {
    "neo4j": "healthy",
    "supabase": "healthy",
    "redis": "healthy"
  }
}
```

**Status Values:**
- `healthy` - Connection successful
- `unhealthy` - Connection failed
- `not_configured` - Credentials not set

## Connection Lifecycle

### Startup

Database connections are initialized when the FastAPI application starts:

1. Neo4j driver is created and verified
2. Supabase client is initialized
3. Redis connection pool is created
4. Health checks are logged

### Runtime

Connections are reused throughout the application lifecycle:

- Neo4j: Driver maintains connection pool
- Supabase: Client handles connection pooling internally
- Redis: Connection pool manages connections

### Shutdown

Connections are gracefully closed when the application shuts down:

1. Neo4j driver is closed
2. Redis connection pool is disconnected
3. Supabase client cleanup (automatic)

## Error Handling

All database clients include error handling:

**Missing Credentials:**
```python
ValueError: "Database credentials not configured"
```

**Connection Failures:**
- Logged as errors
- Application continues with graceful degradation
- Health check endpoints report status

**Query Failures:**
- Caught and logged
- Appropriate error responses returned
- Fallback mechanisms activated

## Testing

Database connection tests are in `tests/test_db_connections.py` and `tests/test_db_structure.py`.

**Run tests:**
```bash
pytest tests/test_db_structure.py -v
```

**Test Coverage:**
- Connection client initialization
- Credential validation
- Health check verification
- Migration file structure
- Configuration completeness

## Security Considerations

**Credentials:**
- Never commit credentials to version control
- Use environment variables for all secrets
- Rotate credentials regularly

**Connections:**
- Use TLS/SSL for all database connections
- Neo4j: `neo4j+s://` protocol
- Supabase: HTTPS by default
- Redis: Use `rediss://` for TLS in production

**Access Control:**
- Use service keys for backend access
- Limit connection pool sizes
- Implement rate limiting
- Monitor connection usage

## Performance Optimization

**Connection Pooling:**
- Neo4j: 50 max connections, 1-hour lifetime
- Redis: 50 max connections
- Supabase: Managed by client

**Caching:**
- Satellite data: 7-day TTL
- Query results: Application-level caching
- Redis: In-memory caching for Celery

**Indexes:**
- All tables have appropriate indexes
- Composite indexes for common queries
- Partial indexes for filtered queries

## Troubleshooting

**Connection Refused:**
- Check credentials in `.env`
- Verify network connectivity
- Check firewall rules

**Slow Queries:**
- Review query execution plans
- Check index usage
- Monitor connection pool saturation

**Cache Misses:**
- Verify cache expiration settings
- Check cache warming jobs
- Monitor cache hit rates

## Next Steps

After setting up database connections:

1. Run Supabase migrations (see migrations/README.md)
2. Set up Neo4j graph schema (Task 4.1)
3. Configure Celery workers (Task 1.3)
4. Implement data integration agents (Task 2.x)
