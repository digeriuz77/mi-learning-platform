-- ============================================
-- PROMOTE USER TO ADMIN
-- ============================================

-- STEP 1: Add role column (skip if already exists)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role text DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator'));

-- STEP 2: Update the user with email gstanyard@gmail.com to admin role
UPDATE public.users
SET role = 'admin'
WHERE email = 'gstanyard@gmail.com';

-- STEP 3: Verify the update
SELECT id, email, role, is_active 
FROM public.users 
WHERE email = 'gstanyard@gmail.com';
