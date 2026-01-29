# MI Learning Platform

A modern FastAPI-based web application for learning Motivational Interviewing (MI) techniques through interactive dialogue scenarios, real-time feedback, and gamification.

## Overview

The MI Learning Platform provides healthcare professionals, counselors, and students with an interactive environment to practice and master Motivational Interviewing techniques. Users navigate through realistic client dialogue scenarios, receive immediate feedback on their technique choices, and track their progress through a gamified learning system.

## Tech Stack

- **Backend:** FastAPI 0.104.1 (Python 3.11)
- **Database:** PostgreSQL via Supabase
- **Authentication:** Supabase Auth with JWT tokens
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (SPA)
- **Containerization:** Docker with docker-compose
- **CI/CD:** GitHub Actions

## Features

- **Interactive Dialogue Trees** - Navigate branching client conversations with multiple response options
- **Real-time Feedback** - Immediate guidance on MI technique effectiveness (OARS techniques)
- **Progressive Learning** - 12-module curriculum covering stages of change
- **Gamification** - Points, levels, achievements, and leaderboards
- **Technique Mastery Tracking** - Monitor proficiency in reflections, open questions, affirmations, and summaries
- **Row-Level Security** - User data isolation enforced at the database level

## Project Structure

```
mi-learning-platform/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic settings management
│   ├── core/
│   │   └── supabase.py         # Supabase client initialization
│   ├── models/                 # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── modules.py
│   │   └── progress.py
│   ├── api/v1/                 # API endpoint routers
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── modules.py          # Module management
│   │   ├── dialogue.py         # Dialogue interaction
│   │   ├── progress.py         # Progress tracking
│   │   └── leaderboard.py      # Rankings
│   ├── services/
│   │   └── scoring_service.py  # Points and level calculations
│   └── db/
│       └── migrations/         # SQL migration files
│           └── 001_init_schema.sql
├── mi_modules/                 # Learning module JSON content
├── static/                     # Frontend assets
│   ├── css/style.css
│   └── js/app.js
├── templates/                  # Jinja2 HTML templates
├── tests/                      # pytest test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.11+
- A Supabase account (free tier available at [supabase.com](https://supabase.com))

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mi-learning-platform
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 3. Setup Supabase Database

See [SUPABASE_SETUP_GUIDE.md](./SUPABASE_SETUP_GUIDE.md) for detailed instructions on:
- Creating a Supabase project
- Running database migrations
- Configuring authentication
- Deploying to production

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Access the Application

- **Web App:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **OpenAPI Spec:** http://localhost:8000/openapi.json

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Authenticate user |
| GET | `/api/v1/auth/me` | Get current user profile |
| GET | `/api/v1/modules` | List all learning modules |
| GET | `/api/v1/modules/{id}` | Get module details |
| POST | `/api/v1/modules/{id}/start` | Start a module |
| GET | `/api/v1/dialogue/module/{id}/node/{node_id}` | Get dialogue node |
| POST | `/api/v1/dialogue/submit` | Submit dialogue choice |
| GET | `/api/v1/progress` | Get user progress stats |
| GET | `/api/v1/leaderboard` | Get top users ranking |

## Docker Deployment

### Build and Run

```bash
docker-compose up --build
```

### Production Build

```bash
docker build -t mi-learning-platform .
docker run -p 8000:8000 --env-file .env mi-learning-platform
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (backend only) |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret for token verification |
| `DEBUG` | No | Enable debug mode (default: false) |
| `CORS_ORIGINS` | No | Allowed CORS origins (comma-separated) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT token expiration (default: 10080) |

## Gamification System

### Scoring

- **Correct Technique:** 100 points
- **First Attempt Bonus:** +50 points
- **Change Talk Evoked:** +50 points
- **Module Completion:** +200 points

### Levels

| Level | Points Required |
|-------|-----------------|
| 1 | 0 |
| 2 | 500 |
| 3 | 1,500 |
| 4 | 3,000 |
| 5 | 5,000 |
| 6 | 8,000 |
| 7 | 12,000 |
| 8 | 18,000 |
| 9 | 25,000 |
| 10 | 30,000 |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api_auth.py -v
```

## Database Schema

The platform uses four main tables with row-level security:

- **user_profiles** - User data with gamification stats
- **learning_modules** - Module content and metadata
- **user_progress** - Individual module progress tracking
- **dialogue_attempts** - Detailed interaction logging

See `app/db/migrations/001_init_schema.sql` for the complete schema.

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests: `pytest`
4. Run linting: `flake8 app/`
5. Submit a pull request

## License

MIT License

## Support

For issues and feature requests, please use the GitHub Issues tracker.
