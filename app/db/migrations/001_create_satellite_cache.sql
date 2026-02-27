-- Migration: Create satellite_cache table
-- Description: Stores cached satellite data (NDVI, soil moisture, rainfall) for locations
-- TTL: 7 days

CREATE TABLE IF NOT EXISTS satellite_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    date DATE NOT NULL,
    ndvi DECIMAL(5, 4),
    soil_moisture DECIMAL(5, 2),
    rainfall_mm DECIMAL(6, 2),
    data_sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '7 days',
    UNIQUE(latitude, longitude, date)
);

-- Create indexes for fast location lookups
CREATE INDEX IF NOT EXISTS idx_satellite_location 
    ON satellite_cache(latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_satellite_expires 
    ON satellite_cache(expires_at);

-- Composite index for location + date queries
CREATE INDEX IF NOT EXISTS idx_satellite_location_date 
    ON satellite_cache(latitude, longitude, date DESC);

-- Partial index for non-expired cache entries
CREATE INDEX IF NOT EXISTS idx_satellite_active 
    ON satellite_cache(latitude, longitude) 
    WHERE expires_at > NOW();

-- Add comments for documentation
COMMENT ON TABLE satellite_cache IS 'Cached satellite data from Google Earth Engine (NASA SMAP, Sentinel-2, CHIRPS)';
COMMENT ON COLUMN satellite_cache.ndvi IS 'Normalized Difference Vegetation Index (0.0-1.0)';
COMMENT ON COLUMN satellite_cache.soil_moisture IS 'Soil moisture percentage (0-100)';
COMMENT ON COLUMN satellite_cache.rainfall_mm IS 'Rainfall in millimeters';
COMMENT ON COLUMN satellite_cache.data_sources IS 'JSON object with source metadata: {smap: {...}, sentinel: {...}, chirps: {...}}';
