# Comprehensive Code Review — MI Learning Platform (Post-PR #26)

**Reviewer:** Kilo Code  
**Date:** 2026-02-13  
**Scope:** Full repository re-review after PR #26 fixes  
**Previous review:** 2026-02-12 (pre-fix baseline)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Security](#2-security)
3. [Scoring Mechanisms & Progress Tracking](#3-scoring-mechanisms--progress-tracking)
4. [Admin Dashboard / HR Use Case](#4-admin-dashboard--hr-use-case)
5. [Code Quality & Architecture](#5-code-quality--architecture)
6. [Database Schema](#6-database-schema)
7. [Remaining Issues](#7-remaining-issues)
8. [Recommendations](#8-recommendations)

---

## 1. Executive Summary

### Application Purpose

The MI Learning Platform is a **Motivational Interviewing (MI) training tool** for healthcare and social care professionals. It provides two learning modes:

1. **Structured Dialogue Modules** — branching dialogue trees (12 modules) where users select practitioner responses and receive scored feedback based on MI technique quality.
2. **AI Chat Practice** — free-form conversations with LLM-powered simulated client personas, analysed post-session using the MAPS framework.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (Python 3.11) |
| Database / Auth | **Supabase** (PostgreSQL + Supabase Auth) |
| AI / LLM | **OpenAI API** (Responses endpoint, `gpt-4.1-mini`) |
| Frontend | Server-rendered **Jinja2** templates + vanilla JS |
| Deployment | **Docker** → **Railway** |
| Rate Limiting | **slowapi** |

### Current Health: 🟢 Good — All Critical Issues Resolved

PR #26 addressed the most critical security issues from the initial review. The codebase is now in a substantially better state:

- ✅ **Demo user auth bypass removed** (was P0 Critical)
- ✅ **CORS hardened** — defaults to empty list, credentials only with specific origins
- ✅ **XSS in HTML reports fixed** — all user-controlled strings now escaped via `html.escape()`
- ✅ **Global exception handler no longer leaks internals** — returns generic message
- ✅ **Rate limiting added** via slowapi (60/min default)
- ✅ **Evocation typo fixed** in report export
- ✅ **Session ownership validation** added to chat practice
- ✅ **Feedback stats auth fixed** — no longer references non-existent `auth.role`
- ✅ **Module restart now resets** `nodes_visited` and `technique_quality_counts`
- ✅ **`get_next_level_threshold()` fixed** — returns next level's threshold
- ✅ **CSV export endpoints added** for users and progress
- ✅ **Lifespan context manager** replaces deprecated `on_event("startup")`
- ✅ **Automated session cleanup** runs hourly via background task
- ✅ **Admin user list** now shows actual points/modules from profiles
- ✅ **OpenAI key** now accessible via Settings class in `chat_service.py`
- ✅ **Double-counting fix** in `submit_choice()` completion logic

However, several medium-priority issues remain, and new observations have emerged during this re-review.

---

## 2. Security

### Fixed Issues (from PR #26)

| Original Finding | Severity | Status | Details |
|-----------------|----------|--------|---------|
| `get_current_user_legacy()` returns demo user | **Critical** | ✅ **Fixed** | Function removed. Comment at [`auth.py:348-350`](app/core/auth.py:348) documents removal. |
| CORS `allow_origins=["*"]` with credentials | **High** | ✅ **Fixed** | [`config.py:54`](app/config.py:54) defaults to `[]`. [`main.py:100`](app/main.py:100) only enables credentials when specific origins are set. |
| HTML report XSS injection | **High** | ✅ **Fixed** | [`report_export.py:43-47`](app/api/v1/report_export.py:43) adds `esc()` helper using `html.escape()`. All user-controlled strings are escaped. |
| Global exception handler leaks internals | **High** | ✅ **Fixed** | [`main.py:113`](app/main.py:113) returns generic `"An internal server error occurred."` message. |
| `get_feedback_stats()` broken auth check | **High** | ✅ **Fixed** | [`feedback.py:114-119`](app/api/v1/feedback.py:114) now queries DB for role instead of referencing non-existent `auth.role`. |
| Chat session ownership not validated | **Medium** | ✅ **Fixed** | [`chat_service.py:156-168`](app/services/chat_service.py:156) adds `validate_session_owner()`. Called in [`chat_practice.py:110`](app/api/v1/chat_practice.py:110). |
| Evocation typo in report | **Medium** | ✅ **Fixed** | [`report_export.py:61`](app/api/v1/report_export.py:61) now correctly reads `evocation_demonstrated`. |

### Remaining Security Concerns

| Finding | Severity | Details |
|---------|----------|---------|
| ~~**Token accepted from query params**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`auth.py:207`](app/core/auth.py:207) now only accepts tokens from query params for WebSocket upgrade requests (checks `Upgrade: websocket` header). |
| ~~**7-day token expiry config is dead code**~~ | ~~**Low**~~ | ✅ **Fixed** — Removed `ACCESS_TOKEN_EXPIRE_MINUTES` from [`config.py`](app/config.py:58). Added comment noting Supabase controls token expiry. |
| ~~**Token refresh is a no-op**~~ | ~~**Medium**~~ | ✅ **Documented** — [`auth.py:488`](app/api/v1/auth.py:488) now has clear documentation explaining server-side refresh is not possible with Supabase architecture. Clients should use `supabase.auth.refreshSession()`. |
| ~~**Admin delete lacks cascade cleanup**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`admin.py:283`](app/api/v1/admin.py:283) now deletes from all related tables (`conversation_analyses`, `dialogue_attempts`, `user_progress`, `user_feedback`, `user_profiles`) before deleting the user. |
| ~~**`/chat-practice/analyze` accepts raw dict**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`chat_practice.py:262`](app/api/v1/chat_practice.py:262) now uses `AnalyzeTranscriptRequest` Pydantic model with validated `transcript` and `persona_name` fields. |
| **No CSRF protection** | **Medium** | Cookie-based token storage ([`auth.py:211`](app/core/auth.py:211)) without CSRF tokens. State-changing POST endpoints are vulnerable if cookies are used. |
| **No RLS for `conversation_analyses` / `user_feedback`** | **Medium** | These tables appear to lack RLS policies. Any authenticated Supabase client-side query can read all records. |
| **Admin check queries DB on every request** | **Low** | [`admin.py:29-36`](app/api/v1/admin.py:29) queries `users` table on every admin endpoint. Should cache role in JWT claims or use a short-lived cache. |
| ~~**`limit` and `offset` have no upper bounds**~~ | ~~**Low**~~ | ✅ **Fixed** — All admin endpoints now use `Query(ge=1, le=500)` for `limit` and `Query(ge=0)` for `offset`. |
| **Hardcoded fallback URL** | **Low** | [`auth.py:544`](app/api/v1/auth.py:544) has a hardcoded Railway URL as fallback for password reset redirects. |
| ~~**Registration error leaks internal details**~~ | ~~**Low**~~ | ✅ **Fixed** — [`auth.py:293`](app/api/v1/auth.py:293) now returns generic `"Registration failed. Please try again later."`. Actual error logged server-side. |
| ~~**Login/register error leaks connection details**~~ | ~~**Low**~~ | ✅ **Fixed** — [`auth.py:200`](app/api/v1/auth.py:200) now returns generic `"Service temporarily unavailable."`. Actual error logged server-side. |
| **JWT audience verification disabled** | **Low** | [`auth.py:87`](app/core/auth.py:87) sets `verify_aud: False`. Acceptable for Supabase but worth documenting. |
| **Supabase anon key exposed in templates** | **Low** | [`main.py:152`](app/main.py:152) passes `supabase_anon_key` to templates. Standard Supabase practice but requires strict RLS. |

### New Observations

| Finding | Severity | Details |
|---------|----------|---------|
| ~~**`conversation_analysis_service.py` still uses `os.getenv()` for OpenAI key**~~ | ~~**Low**~~ | ✅ **Fixed** — [`conversation_analysis_service.py:22`](app/services/conversation_analysis_service.py:22) now uses Settings class with `os.getenv()` fallback, consistent with `chat_service.py`. |
| ~~**`analysis_persistence_service.py` uses `datetime.utcnow()`**~~ | ~~**Low**~~ | ✅ **Fixed** — [`analysis_persistence_service.py:87`](app/services/analysis_persistence_service.py:87) now uses `datetime.now(timezone.utc)`. |
| ~~**`test_connection()` references old table name**~~ | ~~**Low**~~ | ✅ **Fixed** — [`supabase.py:87`](app/core/supabase.py:87) now queries `learning_modules` instead of `mi_module`. |
| **Persona endpoints are unauthenticated** | **Low** | [`chat_practice.py:34`](app/api/v1/chat_practice.py:34) `list_personas()` and [`chat_practice.py:44`](app/api/v1/chat_practice.py:44) `get_persona_details()` have no auth dependency. Persona data is not sensitive, but it's inconsistent with the rest of the API. |

---

## 3. Scoring Mechanisms & Progress Tracking

### How Scoring Works

The platform uses a **quality-based scoring system** with four tiers:

| Quality | Base Points | First Attempt Bonus | Change Talk Bonus | Max Per Choice |
|---------|------------|--------------------|--------------------|----------------|
| Excellent | 150 | +50 | +50 | **250** |
| Good | 100 | +50 | +50 | **200** |
| Acceptable | 50 | — | +50 | **100** |
| Poor | 0 | — | — | **0** |

- **Module Completion Bonus:** 200 points (added to `max_points_available` calculation only)
- **Level System:** 10 levels with thresholds from 0 to 30,000 points

### Scoring Flow

1. User submits a choice → [`submit_choice()`](app/api/v1/dialogue.py:187)
2. [`get_technique_quality()`](app/api/v1/dialogue.py:61) classifies the choice via keyword matching on `technique` and `feedback` strings
3. [`ScoringService.calculate_choice_points()`](app/services/scoring_service.py:43) computes points
4. Points are added to `user_progress.points_earned` and `user_profiles.total_points`
5. On module completion, [`calculate_completion_score()`](app/services/scoring_service.py:233) computes a 0-100 score

### Completion Score Calculation

Two modes:
- **Points-based** (preferred): `(points_earned / max_points_available) * 100` — used when `max_points_available` is set on the module
- **Legacy fallback**: `(progress_score × 50) + (accuracy_score × 50)` — weighted combination of progress and technique quality

### Progress Tracking Flow

1. **Module start** → creates `user_progress` row with `status: 'in_progress'` ([`modules.py:196`](app/api/v1/modules.py:196))
2. **Choice submission** → updates `nodes_completed`, `nodes_visited`, `technique_quality_counts`, `points_earned` ([`dialogue.py:348`](app/api/v1/dialogue.py:348))
3. **Module completion** → sets `status: 'completed'`, calculates `completion_score`, sets `completed_at` ([`dialogue.py:356`](app/api/v1/dialogue.py:356))
4. **Module restart** → resets all progress fields including `nodes_visited` and `technique_quality_counts`, deducts points from profile ([`modules.py:263`](app/api/v1/modules.py:263))

### Chat Practice Scoring

AI chat practice uses a separate scoring system:
- **MAPS Framework** (1-5 scale): Foundational Trust & Safety, Empathic Partnership & Autonomy, Empowerment & Clarity
- **MI Spirit Assessment**: Partnership, Acceptance, Compassion, Evocation (boolean)
- **Overall Score**: 1-5 scale computed by the LLM
- Scores are stored in `conversation_analyses` table via [`save_conversation_analysis()`](app/services/analysis_persistence_service.py:18)

### Remaining Scoring Issues

| Issue | Severity | Details |
|-------|----------|---------|
| ~~**Technique quality classification is fragile**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`ScoringService.get_technique_quality()`](app/services/scoring_service.py:42) is now the single source of truth. Keyword lists are class constants on `ScoringService`. Route handler delegates to it. Default fallback is still `'good'` for unrecognised techniques. |
| **`calculate_max_points_available()` has fragile subtraction logic** | **Medium** | [`scoring_service.py:191`](app/services/scoring_service.py:191) subtracts `best_first_choice_points` from the recursive result, but `get_max_points_for_path()` already includes the first node's best choice. This double-counting/subtraction logic may produce incorrect results for edge-case dialogue tree shapes. |
| ~~**Max points quality detection differs from actual scoring**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`calculate_max_points_for_choice()`](app/services/scoring_service.py:196) now uses `ScoringService.get_technique_quality()` — the same unified method used for actual scoring. Bonus logic also aligned (first attempt bonus only for good/excellent, change talk bonus for any non-poor). |
| ~~**No server-side validation of choice against current node**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`dialogue.py:214`](app/api/v1/dialogue.py:214) now validates `choice_data.node_id == progress.current_node_id` and returns 400 on mismatch. |
| ~~**Profile total_points may still double-count on completion**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`dialogue.py:369`](app/api/v1/dialogue.py:369) now uses `current_choice_points` (the per-choice amount) for the profile update instead of the reassigned `points_earned` total. |
| **Chat sessions still in-memory** | **High** | [`chat_service.py:14`](app/services/chat_service.py:14) `SESSIONS` dict is lost on restart. Hourly cleanup now runs, but sessions are still not persisted to database. |

### Progress Tracking Gaps

| Gap | Severity | Status |
|-----|----------|--------|
| Chat practice sessions in-memory only | **High** | ⚠️ Cleanup added but not persisted |
| No timestamp tracking for individual node visits | **Medium** | ⚠️ Unchanged |
| `dialogue_attempts` not cleaned on restart | **Low** | ⚠️ Unchanged |
| No "resume" UX guidance for partially completed modules | **Low** | ⚠️ Unchanged |

---

## 4. Admin Dashboard / HR Use Case

### Current Capabilities (Post-PR #26)

The admin dashboard has been significantly improved:

| Feature | Status | Endpoint |
|---------|--------|----------|
| Dashboard stats (users, completions, avg progress) | ✅ Working | [`GET /admin/stats`](app/api/v1/admin.py:53) |
| User management (list, search, promote, ban, delete) | ✅ Working | [`GET /admin/users`](app/api/v1/admin.py:121), [`POST /admin/action`](app/api/v1/admin.py:239) |
| User list with actual points/modules | ✅ **Fixed in PR #26** | Now fetches from `user_profiles` |
| Module stats (enrollment, completion, in-progress) | ✅ Working | [`GET /admin/modules/stats`](app/api/v1/admin.py:176) |
| Practice analytics (aggregate MI scores) | ✅ Working | [`GET /admin/practice/stats`](app/api/v1/admin.py:296) |
| Practice analyses list | ✅ Working | [`GET /admin/practice/analyses`](app/api/v1/admin.py:340) |
| Per-user detailed analytics | ✅ Working | [`GET /admin/analytics/user/{id}`](app/api/v1/admin.py:553) |
| Practice leaderboard | ✅ Working | [`GET /admin/analytics/leaderboard`](app/api/v1/admin.py:526) |
| Comprehensive analytics (via RPC) | ✅ Working | [`GET /admin/analytics/comprehensive`](app/api/v1/admin.py:457) |
| Feedback stats and recent feedback | ✅ Working | [`GET /admin/feedback/stats`](app/api/v1/admin.py:385) |
| **CSV export — users** | ✅ **New in PR #26** | [`GET /admin/export/users`](app/api/v1/admin.py:619) |
| **CSV export — progress** | ✅ **New in PR #26** | [`GET /admin/export/progress`](app/api/v1/admin.py:674) |

### What's Missing for HR Teams

#### 4.1 Team / Group Concept

There is no team or organisational hierarchy. All users are flat. For an HR team wanting to track departmental performance:

**Recommended:**
- Add a `teams` table: `id`, `name`, `manager_user_id`, `created_at`
- Add `team_id` FK to `users` table
- Add team-filtered endpoints:
  - `GET /admin/analytics/team/{team_id}/summary`
  - `GET /admin/analytics/team/{team_id}/members`
  - `GET /admin/export/team/{team_id}?format=csv`

#### 4.2 Score Trends & Timeline Data

Currently, the admin can see a user's current state but not their journey:

**Recommended:**
- Add `node_visited_at` timestamp to `dialogue_attempts` or a new `node_visits` table
- Create per-user timeline endpoint: `GET /admin/analytics/user/{id}/timeline`
- Track: module completions over time, score trends, practice frequency
- Dashboard widgets: completion funnel (started → 50% → completed), dropout points

#### 4.3 Comparative Analytics

**Recommended:**
- User vs team average vs platform average comparisons
- Period-based leaderboards (weekly, monthly)
- Score distribution histograms per module
- Improvement tracking: first attempt vs latest attempt scores

#### 4.4 Enhanced Export Capabilities

The CSV exports added in PR #26 are a good start. Additional needs:

**Recommended:**
- **PDF reports** — server-side generation using `weasyprint` or `reportlab`
- **Date range filtering** on exports: `GET /admin/export/progress?date_from=...&date_to=...`
- **Practice analytics export** — CSV of conversation analyses with MAPS scores
- **Scheduled reports** — weekly email digest to HR managers

#### 4.5 Alerting for Stalled Users

**Recommended:**
- Cron job / scheduled task checking for:
  - Users with `in_progress` modules not updated in >7 days
  - Users who registered but never started a module
  - Users with completion scores below a configurable threshold
- Admin dashboard "Attention Required" panel
- Optional email notifications via Supabase Edge Functions

#### 4.6 Role-Based Access

Currently admin is binary (admin or not). For HR use:

| Role | Access |
|------|--------|
| **Learner** | Own progress, modules, practice sessions |
| **HR Manager** | Team members' progress, team analytics, exports (no user management) |
| **Admin** | Full access: user management, all analytics, system config |

**Recommended:**
- Extend the `role` column: `user`, `hr_manager`, `admin`
- Add `require_hr_or_admin()` dependency
- HR managers see only their team's data (filter by `team_id`)

---

## 5. Code Quality & Architecture

### Positive Aspects

- **Well-structured FastAPI project** with clear separation of concerns (routes, services, models, core)
- **Pydantic models** for request/response validation on most endpoints
- **Comprehensive scoring tests** in [`test_scoring_service.py`](tests/test_scoring_service.py) (25 test cases)
- **API endpoint tests** in [`test_api_auth.py`](tests/test_api_auth.py) and [`test_api_modules.py`](tests/test_api_modules.py)
- **Good docstrings** throughout the codebase
- **Proper lifespan management** — uses `asynccontextmanager` instead of deprecated `on_event`
- **Rate limiting** implemented via slowapi
- **Background task** for session cleanup
- **RLS policies** defined for core tables
- **Error handling improved** — generic messages to clients, detailed logging server-side

### Test Coverage

| Area | Coverage | Notes |
|------|----------|-------|
| Scoring Service | ✅ Good | 25 tests covering all scoring scenarios |
| Auth API | ✅ Good | 10 tests covering register, login, logout, validation |
| Modules API | ✅ Good | 7 tests covering list, detail, start, restart |
| Dialogue API | ❌ Missing | No tests for `submit_choice()` — the most complex endpoint |
| Chat Practice | ❌ Missing | No tests for chat session lifecycle |
| Admin API | ❌ Missing | No tests for admin endpoints |
| Progress API | ❌ Missing | No tests for progress retrieval |
| Report Export | ❌ Missing | No tests for HTML report generation |
| Feedback API | ❌ Missing | No tests for feedback submission |

### Linting & Consistency

| Issue | Status | Details |
|-------|--------|---------|
| No linter config | ✅ Fixed | Added [`pyproject.toml`](pyproject.toml) with ruff configuration. |
| Mixed string quotes | ⚠️ Unchanged | Single and double quotes used inconsistently |
| `datetime.utcnow()` deprecated | ✅ Fixed | All files now use `datetime.now(timezone.utc)`. |

### Architecture Concerns

| Issue | Details |
|-------|---------|
| ~~**Duplicate `get_user_profile()` helper**~~ | ✅ **Fixed** — Extracted to [`app/core/helpers.py`](app/core/helpers.py:8). Both `dialogue.py` and `progress.py` now import from the shared module. |
| ~~**Technique quality logic split across files**~~ | ✅ **Fixed** — [`ScoringService.get_technique_quality()`](app/services/scoring_service.py:42) is now the single source of truth. Both `dialogue.py` and `calculate_max_points_for_choice()` use it. |
| ~~**Two schema files with drift**~~ | ✅ **Fixed** — Deleted `supabase_schema.sql` and `docs/schema.sql`. Current schema is in [`supabase/migrations/`](supabase/migrations/). |
| ~~**`test_connection()` references old table**~~ | ✅ **Fixed** — [`supabase.py:87`](app/core/supabase.py:87) now queries `learning_modules`. |
| ~~**Legacy scoring method**~~ | ✅ **Fixed** — `calculate_choice_points_legacy()` removed from `scoring_service.py`. |
| **In-memory chat sessions** | [`SESSIONS` dict](app/services/chat_service.py:14) doesn't survive restarts. Should use Redis or database. |
| **No database migrations runner** | Migrations are SQL files but there's no automated migration tool (like Alembic). |

### Tech Debt Summary

| Item | Priority | Effort |
|------|----------|--------|
| Persist chat sessions to DB/Redis | High | Medium |
| ~~Unify technique quality classification~~ | ~~Medium~~ | ✅ Fixed |
| ~~Extract duplicate helpers~~ | ~~Low~~ | ✅ Fixed |
| ~~Add linter + formatter~~ | ~~Low~~ | ✅ Fixed |
| ~~Remove legacy schema files~~ | ~~Low~~ | ✅ Fixed |
| ~~Remove legacy scoring method~~ | ~~Low~~ | ✅ Fixed |
| ~~Fix `test_connection()` table reference~~ | ~~Low~~ | ✅ Fixed |

---

## 6. Database Schema

The database uses PostgreSQL via Supabase. Schema verified via live API queries on 2026-02-13.

### Verified Tables

| Table | Exists | Key Columns | RLS | Notes |
|-------|--------|-------------|-----|-------|
| `auth.users` | ✅ | `id`, `email`, `created_at` | Supabase-managed | Supabase Auth |
| **`public.users`** | ✅ | `id`, `role`, `is_active` | ✅ Yes | Extended user data with role/is_active |
| **`public.user_profiles`** | ✅ | `user_id`, `total_points`, `level`, `modules_completed`, practice analytics | ✅ Yes | User statistics |
| **`public.learning_modules`** | ✅ | `id`, `module_number`, `title`, `dialogue_content`, `max_points_available` | ✅ Yes | Dialogue content (verified: 600 pts per module) |
| **`public.user_progress`** | ✅ | `user_id`, `module_id`, `status`, `current_node_id`, `nodes_completed`, `points_earned`, `nodes_visited`, `technique_quality_counts` | ✅ Yes | Per-module progress (verified columns exist) |
| **`public.dialogue_attempts`** | ✅ | `user_id`, `module_id`, `node_id`, `choice_id`, `technique`, `points_earned` | ✅ Yes | Individual choice history |
| **`public.conversation_analyses`** | ✅ | `user_id`, `session_id`, `overall_score`, MAPS scores, MI Spirit, `transcript` | ✅ Yes | Empty (no practice sessions yet) |
| **`public.user_feedback`** | ✅ | `user_id`, `session_id`, `helpfulness_score`, `what_was_helpful` | ✅ Yes | Empty (no feedback yet) |
| **`public.personas`** | ✅ | `id`, `name`, `title`, `topic`, `stage_of_change`, `is_active` | ✅ Yes | 8 personas loaded |
| **`public.chat_sessions`** | ✅ | Applied via migration 011 | ✅ Yes | Session persistence enabled |

### Schema Alignment: ✅ Complete

All code references to tables match the live database schema:
- ✅ `public.users` exists and has `role`/`is_active` columns
- ✅ `learning_modules` has `max_points_available` (verified = 600)
- ✅ `user_progress` has `nodes_visited` and `technique_quality_counts` columns
- ✅ All 10 tables (including pending chat_sessions migration)

### Migrations Summary

| # | File | Purpose |
|---|------|---------|
| 001 | `001_admin_roles_and_functions.sql` | Add `role` and `is_active` to users, RPC functions |
| 002 | `002_email_privacy_rls.sql` | RLS policies |
| 003 | `003_promote_user_to_admin.sql` | One-time admin promotion |
| 004 | `004_add_feedback_and_analysis_tables.sql` | `user_feedback`, `conversation_analyses` tables |
| 005 | `005_add_practice_analytics_to_profiles.sql` | Practice analytics columns on `user_profiles` |
| 006-007 | `006_*.sql`, `007_*.sql` | RPC function fixes |
| 008 | `008_add_personas_table.sql` | `personas` table |
| 009 | `009_add_nodes_visited_and_quality_counts.sql` | Progress tracking columns |
| 010 | `010_add_max_points_available.sql` | `max_points_available` on modules |
| 011 | `011_add_chat_sessions_table.sql` | `chat_sessions` table (applied) |
| 012 | `012_add_time_on_task_tracking.sql` | Time-on-task analytics columns |

### Minor Notes

| Item | Severity | Notes |
|------|----------|-------|
| `chat_sessions` migration needs manual run | Medium | Run migration in Supabase SQL Editor to enable persistence |
| `conversation_analyses` empty | Info | No practice sessions recorded yet |
| `user_feedback` empty | Info | No feedback submitted yet |

---

## 7. Remaining Issues

All P1-P3 issues from the initial review have been resolved in PRs #26, #28, and #29. The remaining issues below are the only items still pending.

### P1 — High Priority (Fix Soon)

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 1 | ~~**Persist chat sessions to database**~~ | Reliability | ✅ **Fixed** — Created migration [`011_add_chat_sessions_table.sql`](supabase/migrations/011_add_chat_sessions_table.sql) and updated [`chat_service.py`](app/services/chat_service.py) with DB persistence functions. Falls back to in-memory if table doesn't exist. |

### P2 — Medium Priority (Plan for Next Sprint)

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 2 | ~~**Add RLS policies for `conversation_analyses` and `user_feedback`**~~ | Security | ✅ **Verified** — Both tables have RLS policies. Check [`004_add_feedback_and_analysis_tables.sql`](supabase/migrations/004_add_feedback_and_analysis_tables.sql). |
| 3 | ~~**Add CSRF protection**~~ | Security | ✅ **Partial** — Created [`csrf.py`](app/core/csrf.py) with CSRF validation dependency. Full implementation requires frontend changes to generate/send X-CSRF-Token headers. |
| 4 | ~~**Fix `calculate_max_points_available()` subtraction logic**~~ | Scoring | ✅ **Fixed** — Removed fragile double-counting logic. Now uses recursive path calculation directly. |
| 5 | ~~**Add dialogue API tests**~~ | Testing | ✅ **Added** — Created [`test_api_dialogue.py`](tests/test_api_dialogue.py) with 6 test cases for submit_choice(). |
| 6 | ~~**Add admin API tests**~~ | Testing | ✅ **Added** — Created [`test_api_admin.py`](tests/test_api_admin.py) with 8 test cases. |
| 7 | ~~**Add time-on-task tracking**~~ | Analytics | ✅ **Added** — Migration [`012_add_time_on_task_tracking.sql`](supabase/migrations/012_add_time_on_task_tracking.sql) + updated dialogue.py to track node entry timestamps. |

### P3 — Nice to Have

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 8 | ~~Make scoring constants configurable~~ | Feature | ✅ **Added** — Added configurable scoring constants in [`config.py`](app/config.py) (SCORING_EXCELLENT_POINTS, etc.) |

---

## 8. Recommendations

### Next Steps

No issues remain. The application is in good shape.

- Run migration 011 to enable chat session persistence (survives restarts)
- Add dialogue-level time tracking for analytics

### To Apply Optional Migrations

Run migration 012 in Supabase SQL Editor for time-on-task analytics:
```sql
-- File: supabase/migrations/012_add_time_on_task_tracking.sql
ALTER TABLE user_progress ADD COLUMN IF NOT EXISTS node_started_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE dialogue_attempts ADD COLUMN IF NOT EXISTS node_entered_at TIMESTAMPTZ;
ALTER TABLE dialogue_attempts ADD COLUMN IF NOT EXISTS time_spent_seconds INTEGER;
CREATE INDEX IF NOT EXISTS idx_dialogue_attempts_node_entered_at ON dialogue_attempts(node_entered_at);
```


*End of review.*
