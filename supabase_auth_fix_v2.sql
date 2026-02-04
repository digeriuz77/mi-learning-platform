-- Supabase Auth Fix Script
-- Run this in Supabase SQL Editor to fix registration issues

-- 1. Clear orphaned user_profiles from failed registrations
DELETE FROM user_profiles WHERE user_id NOT IN (SELECT id FROM auth.users);

-- 2. Backfill missing users from auth.users
INSERT INTO public.users (id, email, display_name)
SELECT
    au.id,
    au.email,
    au.raw_user_meta_data->>'display_name'
FROM auth.users au
LEFT JOIN public.users u ON u.id = au.id
WHERE u.id IS NULL
ON CONFLICT (id) DO NOTHING;

-- 3. Fix the FK in user_profiles to reference auth.users directly
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_user_id_fkey;
ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 4. Create a trigger to auto-populate users table when new auth user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'display_name'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if any, then create
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 5. Refresh Supabase schema cache
NOTIFY pgrst, 'RELOAD SCHEMA';

-- 6. Verify the fix
SELECT
    (SELECT COUNT(*) FROM auth.users) as auth_users,
    (SELECT COUNT(*) FROM public.users) as app_users,
    (SELECT COUNT(*) FROM user_profiles) as profiles;
