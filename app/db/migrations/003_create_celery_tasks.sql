-- Migration: Create celery_tasks table
-- Description: Stores Celery task status and results

CREATE TABLE IF NOT EXISTS celery_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    params JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for fast task lookups
CREATE INDEX IF NOT EXISTS idx_celery_task_id 
    ON celery_tasks(task_id);

CREATE INDEX IF NOT EXISTS idx_celery_status 
    ON celery_tasks(status);

-- Composite index for task type + status queries
CREATE INDEX IF NOT EXISTS idx_celery_type_status 
    ON celery_tasks(task_type, status);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_celery_created 
    ON celery_tasks(created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE celery_tasks IS 'Celery async task tracking and results';
COMMENT ON COLUMN celery_tasks.task_id IS 'Celery task UUID';
COMMENT ON COLUMN celery_tasks.task_type IS 'Task type: fetch_satellite_data, process_ndvi, etc.';
COMMENT ON COLUMN celery_tasks.status IS 'Task status: queued, processing, completed, failed';
COMMENT ON COLUMN celery_tasks.params IS 'Task input parameters as JSON';
COMMENT ON COLUMN celery_tasks.result IS 'Task result data as JSON';
COMMENT ON COLUMN celery_tasks.error IS 'Error message if task failed';

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_celery_tasks_updated_at 
    BEFORE UPDATE ON celery_tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
