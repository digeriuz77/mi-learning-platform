-- Migration: Add Personas Table
-- Date: 2026-02-11
-- Description: Creates table for storing persona metadata. Full persona content is stored
--              in the service layer for efficiency and prompt construction.

-- ============================================
-- Table: personas
-- Stores metadata for MI practice personas
-- ============================================
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    avatar TEXT NOT NULL,
    topic TEXT NOT NULL CHECK (topic IN ('smoking_cessation', 'weight_loss', 'both')),
    stage_of_change TEXT NOT NULL CHECK (stage_of_change IN ('precontemplation', 'contemplation', 'preparation', 'action', 'maintenance', 'ambivalent')),
    age INTEGER,
    initial_mood TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Enable RLS on personas
ALTER TABLE personas ENABLE ROW LEVEL SECURITY;

-- RLS Policies for personas
-- Everyone (including anonymous) can read active personas
CREATE POLICY "Anyone can view active personas"
    ON personas FOR SELECT
    TO anon, authenticated
    USING (is_active = TRUE);

CREATE POLICY "Admins can view all personas"
    ON personas FOR SELECT
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'));

CREATE POLICY "Admins can insert personas"
    ON personas FOR INSERT
    TO authenticated
    WITH CHECK (auth.jwt()->>'role' IN ('admin', 'moderator'));

CREATE POLICY "Admins can update personas"
    ON personas FOR UPDATE
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'))
    WITH CHECK (auth.jwt()->>'role' IN ('admin', 'moderator'));

CREATE POLICY "Admins can delete personas"
    ON personas FOR DELETE
    TO authenticated
    USING (auth.jwt()->>'role' IN ('admin', 'moderator'));

-- ============================================
-- Indexes for performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_personas_topic ON personas(topic);
CREATE INDEX IF NOT EXISTS idx_personas_is_active ON personas(is_active);
CREATE INDEX IF NOT EXISTS idx_personas_display_order ON personas(display_order);

-- ============================================
-- Function: Update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_personas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW
    EXECUTE FUNCTION update_personas_updated_at();

-- ============================================
-- Insert initial personas
-- ============================================
INSERT INTO personas (id, name, title, description, avatar, topic, stage_of_change, age, initial_mood, display_order) VALUES
    ('smoking_cessation', 'Marcus', 'Smoking Cessation Client', 'A 42-year-old who has been smoking for 20 years and is considering quitting.', '🚬', 'smoking_cessation', 'contemplation', 42, 'cautiously open', 1),
    ('weight_loss', 'Jennifer', 'Physical Activity & Weight Loss Client', 'A 35-year-old looking to become more active and lose weight after having children.', '🏃‍♀️', 'weight_loss', 'contemplation', 35, 'overwhelmed but willing to talk', 2),
    ('daniel_smoking', 'Daniel', 'Automotive Technician - Smoking Cessation', 'A 37-year-old father who wants to quit smoking for his kids but struggles with stress and workplace culture.', '🔧', 'smoking_cessation', 'contemplation', 37, 'conflicted but hopeful', 3),
    ('aisha_smoking', 'Aisha', 'Graduate Student - Smoking Cessation', 'A 24-year-old social work student who smokes secretly and wants to align her actions with her values.', '📚', 'smoking_cessation', 'preparation', 24, 'motivated but anxious', 4),
    ('maggie_smoking', 'Maggie', 'Librarian - Smoking Cessation', 'A 62-year-old widow who has smoked for 44 years and questions whether quitting is worth it at her age.', '📖', 'smoking_cessation', 'contemplation', 62, 'ambivalent and tired', 5),
    ('mark_weight', 'Mark', 'Sales Manager - Weight Loss', 'A 46-year-old father whose job involves driving and client meals, leading to weight gain and health concerns.', '🚗', 'weight_loss', 'contemplation', 46, 'overwhelmed and skeptical', 6),
    ('nadia_weight', 'Nadia', 'Accounts Assistant - Weight Loss', 'A 39-year-old mother from a Bangladeshi background where food is central to culture and hospitality.', '👩‍💼', 'weight_loss', 'contemplation', 39, 'torn between culture and health', 7),
    ('tom_weight', 'Tom', 'Facilities Manager - Weight Loss', 'A 52-year-old who has started making changes but is worried about maintaining momentum.', '🏫', 'weight_loss', 'preparation', 52, 'motivated but fragile', 8)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- Function: Get personas by topic
-- Returns personas filtered by topic
-- ============================================
CREATE OR REPLACE FUNCTION get_personas_by_topic(p_topic TEXT DEFAULT NULL)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    title TEXT,
    description TEXT,
    avatar TEXT,
    topic TEXT,
    stage_of_change TEXT,
    age INTEGER,
    initial_mood TEXT,
    display_order INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.title,
        p.description,
        p.avatar,
        p.topic,
        p.stage_of_change,
        p.age,
        p.initial_mood,
        p.display_order
    FROM personas p
    WHERE
        p.is_active = TRUE
        AND (p_topic IS NULL OR p.topic = p_topic OR p.topic = 'both')
    ORDER BY p.display_order, p.name;
END;
$$;
