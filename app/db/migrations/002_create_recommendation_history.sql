-- Migration: Create recommendation_history table
-- Description: Stores historical recommendations for farmers

CREATE TABLE IF NOT EXISTS recommendation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id VARCHAR(255),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    crop VARCHAR(50) NOT NULL,
    recommendation JSONB NOT NULL,
    confidence DECIMAL(5, 2),
    data_quality VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for fast farmer and date lookups
CREATE INDEX IF NOT EXISTS idx_recommendation_farmer 
    ON recommendation_history(farmer_id);

CREATE INDEX IF NOT EXISTS idx_recommendation_created 
    ON recommendation_history(created_at DESC);

-- Composite index for farmer + date queries
CREATE INDEX IF NOT EXISTS idx_recommendation_farmer_date 
    ON recommendation_history(farmer_id, created_at DESC);

-- Index for crop-based queries
CREATE INDEX IF NOT EXISTS idx_recommendation_crop 
    ON recommendation_history(crop);

-- Add comments for documentation
COMMENT ON TABLE recommendation_history IS 'Historical recommendations generated for farmers';
COMMENT ON COLUMN recommendation_history.farmer_id IS 'Pseudonymized farmer identifier (no PII)';
COMMENT ON COLUMN recommendation_history.recommendation IS 'Full recommendation object with action, urgency, reasoning, etc.';
COMMENT ON COLUMN recommendation_history.confidence IS 'Confidence level (0-100)';
COMMENT ON COLUMN recommendation_history.data_quality IS 'Data quality indicator: excellent, good, fair, poor';
