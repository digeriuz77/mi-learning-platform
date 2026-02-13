-- Migration: Add time-on-task tracking for node visits
-- Date: 2026-02-13
-- Description: Enables learning analytics by tracking when users visit each node

-- Add timestamp columns to user_progress to track when user entered current node
ALTER TABLE user_progress ADD COLUMN IF NOT EXISTS node_started_at TIMESTAMPTZ DEFAULT NOW();

-- Add timestamp columns to dialogue_attempts for time-on-task tracking
ALTER TABLE dialogue_attempts ADD COLUMN IF NOT EXISTS node_entered_at TIMESTAMPTZ;
ALTER TABLE dialogue_attempts ADD COLUMN IF NOT EXISTS time_spent_seconds INTEGER;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_dialogue_attempts_node_entered_at ON dialogue_attempts(node_entered_at);
