# Supabase Setup and Hosting Guide

This guide walks you through setting up Supabase for the MI Learning Platform and deploying it to production.

## Table of Contents

1. [Create Supabase Project](#1-create-supabase-project)
2. [Configure Environment Variables](#2-configure-environment-variables)
3. [Run Database Migrations](#3-run-database-migrations)
4. [Seed Learning Modules](#4-seed-learning-modules)
5. [Configure Authentication](#5-configure-authentication)
6. [Test Locally](#6-test-locally)
7. [Hosting Options](#7-hosting-options)
8. [Production Checklist](#8-production-checklist)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Create Supabase Project

### Step 1: Sign Up

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign in with GitHub (recommended) or email

### Step 2: Create New Project

1. Click "New Project"
2. Select your organization (or create one)
3. Fill in project details:
   - **Name:** `mi-learning-platform`
   - **Database Password:** Generate a strong password and save it securely
   - **Region:** Choose the closest region to your users
   - **Pricing Plan:** Free tier is sufficient for development

4. Click "Create new project"
5. Wait for the project to provision (takes 1-2 minutes)

### Step 3: Gather Credentials

Once your project is ready, navigate to **Settings > API** to find:

| Credential | Location | Description |
|------------|----------|-------------|
| **Project URL** | `URL` field | Your Supabase project URL |
| **anon public** | `Project API keys` | Public key for client-side requests |
| **service_role** | `Project API keys` | Secret key for server-side operations |

Navigate to **Settings > API > JWT Settings** to find:

| Credential | Location | Description |
|------------|----------|-------------|
| **JWT Secret** | `JWT Secret` field | Used to verify JWT tokens |

---

## 2. Configure Environment Variables

### Create Your .env File

```bash
cp .env.example .env
```

### Edit .env with Your Credentials

```env
# Supabase Configuration (Required)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your-anon-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase

# Application Settings
APP_NAME=MI Learning Platform
APP_VERSION=1.0.0
DEBUG=true
API_V1_PREFIX=/api/v1

# CORS Settings (comma-separated)
CORS_ORIGINS=http://localhost:8000,http://localhost:3000

# JWT Settings
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### Security Notes

- Never commit `.env` to version control
- The `service_role` key has full database access - keep it secret
- Use different Supabase projects for development and production

---

## 3. Run Database Migrations

The database schema is defined in `app/db/migrations/001_init_schema.sql`.

### Option A: Supabase Dashboard (Recommended for First Setup)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Click "New query"
4. Copy the entire contents of `app/db/migrations/001_init_schema.sql`
5. Paste into the SQL editor
6. Click "Run" (or press Ctrl/Cmd + Enter)

### Option B: Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

### Verify Migration Success

After running the migration, verify tables were created:

1. Go to **Table Editor** in Supabase dashboard
2. You should see these tables:
   - `user_profiles`
   - `learning_modules`
   - `user_progress`
   - `dialogue_attempts`

3. Check **Authentication > Policies** to verify RLS policies are active

---

## 4. Seed Learning Modules

The learning content is stored in JSON files under `mi_modules/`. You need to import these into the database.

### Option A: Using the API (After Server is Running)

Create a script `scripts/seed_modules.py`:

```python
import json
import os
from pathlib import Path
from supabase import create_client

# Load environment
from dotenv import load_dotenv
load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

modules_dir = Path("mi_modules")

for module_file in sorted(modules_dir.glob("*.json")):
    with open(module_file) as f:
        module_data = json.load(f)

    # Transform to database format
    db_module = {
        "module_number": module_data["module_number"],
        "title": module_data["title"],
        "slug": module_data["slug"],
        "learning_objective": module_data["learning_objective"],
        "technique_focus": module_data["technique_focus"],
        "stage_of_change": module_data.get("stage_of_change", ""),
        "dialogue_content": module_data["dialogue"],
        "is_published": True,
        "display_order": module_data["module_number"]
    }

    # Upsert module
    result = supabase.table("learning_modules").upsert(
        db_module,
        on_conflict="module_number"
    ).execute()

    print(f"Imported: {module_data['title']}")

print("Done! All modules imported.")
```

Run it:

```bash
python scripts/seed_modules.py
```

### Option B: Direct SQL Insert

You can also insert modules directly via SQL Editor. See the module JSON files for the content structure.

---

## 5. Configure Authentication

Supabase Auth handles user registration and login.

### Enable Email Auth (Default)

1. Go to **Authentication > Providers**
2. Ensure "Email" provider is enabled
3. Configure settings:
   - **Enable email confirmations:** Disable for development, enable for production
   - **Secure email change:** Enable
   - **Secure password change:** Enable

### Configure Email Templates (Optional)

1. Go to **Authentication > Email Templates**
2. Customize templates for:
   - Confirm signup
   - Reset password
   - Magic link

### Configure Redirect URLs

1. Go to **Authentication > URL Configuration**
2. Add your application URLs:
   - **Site URL:** `http://localhost:8000` (dev) or your production URL
   - **Redirect URLs:** Add all valid callback URLs

---

## 6. Test Locally

### Start the Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn app.main:app --reload --port 8000
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123", "display_name": "Test User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'

# Get modules (with auth token)
curl http://localhost:8000/api/v1/modules \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Access the Web App

Open http://localhost:8000 in your browser.

---

## 7. Hosting Options

### Option A: Railway (Recommended for Simplicity)

Railway offers easy Docker deployment with automatic HTTPS.

1. **Create Railway Account:** [railway.app](https://railway.app)

2. **Create New Project:**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login
   railway login

   # Initialize project
   railway init
   ```

3. **Add Environment Variables:**
   - Go to your Railway project dashboard
   - Click on your service
   - Go to "Variables"
   - Add all variables from your `.env` file

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Get Your URL:**
   - Railway provides a URL like `your-app.up.railway.app`
   - Add this to your Supabase CORS settings

### Option B: Render

1. **Create Render Account:** [render.com](https://render.com)

2. **Create New Web Service:**
   - Connect your GitHub repository
   - Select "Docker" as the environment
   - Add environment variables in the dashboard

3. **Configure:**
   - **Build Command:** (auto-detected from Dockerfile)
   - **Start Command:** (auto-detected from Dockerfile)
   - **Health Check Path:** `/health`

### Option C: Fly.io

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (creates fly.toml)
fly launch

# Set secrets
fly secrets set SUPABASE_URL=https://your-project.supabase.co
fly secrets set SUPABASE_KEY=your-anon-key
fly secrets set SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
fly secrets set SUPABASE_JWT_SECRET=your-jwt-secret

# Deploy
fly deploy
```

### Option D: Self-Hosted (Docker)

For your own server (VPS, AWS EC2, etc.):

```bash
# Pull and run
docker pull ghcr.io/your-org/mi-learning-platform:latest
docker run -d \
  --name mi-learning-platform \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  mi-learning-platform

# Or use docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## 8. Production Checklist

### Security

- [ ] Set `DEBUG=false`
- [ ] Use strong, unique `SUPABASE_JWT_SECRET`
- [ ] Enable email confirmation in Supabase Auth
- [ ] Configure CORS to only allow your production domain
- [ ] Enable HTTPS (most platforms do this automatically)
- [ ] Review RLS policies are working correctly

### Supabase Configuration

- [ ] Enable Point-in-Time Recovery (paid plans)
- [ ] Set up database backups
- [ ] Configure rate limiting in Supabase dashboard
- [ ] Monitor database usage in Supabase dashboard

### Application

- [ ] Set correct `CORS_ORIGINS` for production URL
- [ ] Configure proper logging
- [ ] Set up error tracking (Sentry recommended)
- [ ] Test all API endpoints in production

### DNS and Domains

- [ ] Configure custom domain on your hosting platform
- [ ] Update Supabase redirect URLs
- [ ] Update CORS origins

### Monitoring

- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)
- [ ] Configure alerts for errors
- [ ] Monitor Supabase database metrics

---

## 9. Troubleshooting

### Common Issues

#### "Invalid API key" Error

- Verify your Supabase URL and keys are correct
- Check there are no extra spaces in your `.env` file
- Ensure you're using the correct key (anon vs service_role)

#### CORS Errors

- Add your frontend URL to `CORS_ORIGINS`
- Add your URL to Supabase dashboard > Authentication > URL Configuration

#### "JWT expired" Error

- Check `ACCESS_TOKEN_EXPIRE_MINUTES` setting
- Implement token refresh in your frontend

#### RLS Blocking Queries

- Ensure user is authenticated when accessing protected tables
- Check RLS policies in Supabase dashboard
- Use service_role key for admin operations

#### Database Connection Issues

- Verify your IP is allowed in Supabase (Settings > Database > Connection Pooling)
- Check if you've exceeded free tier limits
- Verify database password is correct

### Getting Help

- **Supabase Docs:** [supabase.com/docs](https://supabase.com/docs)
- **Supabase Discord:** [discord.supabase.com](https://discord.supabase.com)
- **FastAPI Docs:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

---

## Quick Reference

### Supabase Dashboard URLs

- **Dashboard:** `https://app.supabase.com/project/YOUR_PROJECT_REF`
- **SQL Editor:** `https://app.supabase.com/project/YOUR_PROJECT_REF/sql`
- **Table Editor:** `https://app.supabase.com/project/YOUR_PROJECT_REF/editor`
- **Auth:** `https://app.supabase.com/project/YOUR_PROJECT_REF/auth/users`
- **API Settings:** `https://app.supabase.com/project/YOUR_PROJECT_REF/settings/api`

### Useful Commands

```bash
# Start dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest -v

# Build Docker image
docker build -t mi-learning-platform .

# View logs
docker logs -f mi-learning-platform
```

### Environment Variable Quick Copy

```env
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
APP_NAME=MI Learning Platform
APP_VERSION=1.0.0
DEBUG=false
API_V1_PREFIX=/api/v1
CORS_ORIGINS=https://your-production-domain.com
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```
