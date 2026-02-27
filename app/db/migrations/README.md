# Database Migrations

This directory contains SQL migration scripts for setting up the Supabase PostgreSQL database schema.

## Migration Files

1. **001_create_satellite_cache.sql** - Creates the `satellite_cache` table for storing cached satellite data (NDVI, soil moisture, rainfall) with 7-day TTL
2. **002_create_recommendation_history.sql** - Creates the `recommendation_history` table for storing historical recommendations
3. **003_create_celery_tasks.sql** - Creates the `celery_tasks` table for tracking async task status and results

## Running Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Log in to your [Supabase Dashboard](https://app.supabase.com)
2. Navigate to your project
3. Go to **SQL Editor**
4. Copy the content of each migration file in order (001, 002, 003)
5. Paste and execute each migration

### Option 2: PostgreSQL Client

If you have direct PostgreSQL access:

```bash
# Using psql
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f 001_create_satellite_cache.sql
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f 002_create_recommendation_history.sql
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f 003_create_celery_tasks.sql
```

### Option 3: Python Script

```bash
python app/db/migrations/run_migrations.py
```

Note: This will prepare the migrations but you'll need to execute them manually via the Supabase Dashboard.

## Schema Overview

### satellite_cache

Stores cached satellite data from Google Earth Engine:
- NDVI (Normalized Difference Vegetation Index)
- Soil moisture percentage
- Rainfall in millimeters
- Data source metadata
- 7-day expiration

**Indexes:**
- Location-based lookups (latitude, longitude)
- Date-based queries
- Active cache entries (non-expired)

### recommendation_history

Stores historical recommendations for farmers:
- Farmer ID (pseudonymized)
- Location and crop type
- Full recommendation JSON
- Confidence level and data quality
- Timestamp

**Indexes:**
- Farmer-based lookups
- Date-based queries
- Crop-based queries

### celery_tasks

Tracks async task execution:
- Task ID and type
- Status (queued, processing, completed, failed)
- Input parameters and results
- Error messages
- Timestamps with auto-update trigger

**Indexes:**
- Task ID lookups
- Status-based queries
- Task type + status combinations

## Verification

After running migrations, verify the tables were created:

```sql
-- Check tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('satellite_cache', 'recommendation_history', 'celery_tasks');

-- Check indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('satellite_cache', 'recommendation_history', 'celery_tasks');
```

## Rollback

To rollback migrations (use with caution):

```sql
DROP TABLE IF EXISTS celery_tasks CASCADE;
DROP TABLE IF EXISTS recommendation_history CASCADE;
DROP TABLE IF EXISTS satellite_cache CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```
