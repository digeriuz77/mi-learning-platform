-- Migration: Add max_points_available column to learning_modules table
-- This fixes the issue where completion_score was calculated incorrectly
-- because the max points per module wasn't being tracked

-- Add max_points_available column to learning_modules table
ALTER TABLE learning_modules ADD COLUMN IF NOT EXISTS max_points_available INTEGER;

-- Create a function to calculate max points from dialogue content
CREATE OR REPLACE FUNCTION calculate_max_points_from_dialogue(dialogue_content JSONB)
RETURNS INTEGER AS $$
DECLARE
    max_points INTEGER := 0;
    nodes JSONB;
    node_data JSONB;
    choice_data JSONB;
    choice_points INTEGER;
    best_choice_points INTEGER;
    node_id TEXT;
    next_node_id TEXT;
    start_node_id TEXT;
    
    -- Recursive path finding variables
    current_path_points INTEGER;
    best_path_points INTEGER;
    visited_nodes TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Handle null or empty dialogue
    IF dialogue_content IS NULL OR dialogue_content = 'null'::JSONB THEN
        RETURN 0;
    END IF;
    
    -- Get start node
    start_node_id := dialogue_content->>'start_node';
    IF start_node_id IS NULL THEN
        start_node_id := 'node_1';
    END IF;
    
    -- Build node map and process each node to find best path
    -- For now, use a simplified calculation:
    -- Count total choice nodes and multiply by max points per excellent choice
    
    max_points := 0;
    
    -- Iterate through all nodes
    FOR node_data IN SELECT * FROM jsonb_array_elements(dialogue_content->'nodes')
    LOOP
        node_id := node_data->>'id';
        
        -- Skip ending nodes (they add completion bonus only)
        IF node_data->>'is_ending' = 'true' THEN
            max_points := max_points + 200; -- MODULE_COMPLETION_BONUS
        ELSE
            -- Find the best choice in this node
            best_choice_points := 0;
            
            FOR choice_data IN SELECT * FROM jsonb_array_elements(node_data->'practitioner_choices')
            LOOP
                -- Calculate points for this choice
                choice_points := 150; -- EXCELLENT_POINTS
                
                -- Add first attempt bonus
                choice_points := choice_points + 50; -- FIRST_ATTEMPT_BONUS
                
                -- Add change talk bonus
                choice_points := choice_points + 50; -- CHANGE_TALK_BONUS
                
                IF choice_points > best_choice_points THEN
                    best_choice_points := choice_points;
                END IF;
            END LOOP;
            
            max_points := max_points + best_choice_points;
        END IF;
    END LOOP;
    
    RETURN max_points;
END;
$$ LANGUAGE plpgsql;

-- Update all existing modules to calculate their max_points_available
UPDATE learning_modules 
SET max_points_available = calculate_max_points_from_dialogue(dialogue_content)
WHERE max_points_available IS NULL;

-- Create a function to recalculate completion_score based on points
CREATE OR REPLACE FUNCTION recalculate_completion_score(
    p_points_earned INTEGER,
    p_max_points_available INTEGER
)
RETURNS INTEGER AS $$
BEGIN
    IF p_max_points_available IS NULL OR p_max_points_available = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN LEAST(100, (p_points_earned * 100) / p_max_points_available);
END;
$$ LANGUAGE plpgsql;

-- Update user_progress completion_score based on points and max_points_available
UPDATE user_progress up
SET completion_score = recalculate_completion_score(
    up.points_earned,
    lm.max_points_available
)
FROM learning_modules lm
WHERE up.module_id = lm.id
AND lm.max_points_available IS NOT NULL
AND up.points_earned > 0
AND up.status = 'completed';

COMMENT ON COLUMN learning_modules.max_points_available IS 
'Maximum points achievable in this module, calculated from the dialogue structure. Used for accurate completion percentage.';
