-- ============================================
-- Add nodes_visited and technique_quality_counts to user_progress
-- This enables proper progress tracking and quality-based scoring
-- ============================================

-- Add nodes_visited column (tracks all nodes the user has reached)
ALTER TABLE public.user_progress 
ADD COLUMN IF NOT EXISTS nodes_visited TEXT[] DEFAULT '{}';

-- Add technique_quality_counts column (tracks distribution of technique quality)
ALTER TABLE public.user_progress 
ADD COLUMN IF NOT EXISTS technique_quality_counts JSONB DEFAULT '{"excellent": 0, "good": 0, "acceptable": 0, "poor": 0}';

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_user_progress_status ON public.user_progress(status);

-- Add comment
COMMENT ON COLUMN public.user_progress.nodes_visited IS 'Array of node IDs the user has visited (regardless of technique quality)';
COMMENT ON COLUMN public.user_progress.technique_quality_counts IS 'JSON object tracking counts of each technique quality level: excellent, good, acceptable, poor';
