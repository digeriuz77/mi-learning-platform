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
6. [Remaining Issues](#6-remaining-issues)
7. [Recommendations](#7-recommendations)

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

### Current Health: 🟡 Good — Significant Improvements, Some Issues Remain

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
| **Token accepted from query params** | **Medium** | [`auth.py:207`](app/core/auth.py:207) still checks `request.query_params.get("token")`. Tokens in URLs appear in server logs, browser history, and referrer headers. Should be limited to WebSocket upgrade requests only. |
| **7-day token expiry config is dead code** | **Low** | [`config.py:58`](app/config.py:58) sets `ACCESS_TOKEN_EXPIRE_MINUTES = 10080` but this value is never used — Supabase controls token expiry. Misleading config. |
| **Token refresh is a no-op** | **Medium** | [`auth.py:488-492`](app/api/v1/auth.py:488) returns the same token if valid. No actual refresh token flow. Users must re-login when tokens expire. |
| **Admin delete lacks cascade cleanup** | **Medium** | [`admin.py:283`](app/api/v1/admin.py:283) deletes from `users` table but doesn't clean up `user_profiles`, `user_progress`, `dialogue_attempts`, or `conversation_analyses`. Orphaned data remains. |
| ~~**`/chat-practice/analyze` accepts raw dict**~~ | ~~**Medium**~~ | ✅ **Fixed** — [`chat_practice.py:262`](app/api/v1/chat_practice.py:262) now uses `AnalyzeTranscriptRequest` Pydantic model with validated `transcript` and `persona_name` fields. |
| **No CSRF protection** | **Medium** | Cookie-based token storage ([`auth.py:211`](app/core/auth.py:211)) without CSRF tokens. State-changing POST endpoints are vulnerable if cookies are used. |
| **No RLS for `conversation_analyses` / `user_feedback`** | **Medium** | These tables appear to lack RLS policies. Any authenticated Supabase client-side query can read all records. |
| **Admin check queries DB on every request** | **Low** | [`admin.py:29-36`](app/api/v1/admin.py:29) queries `users` table on every admin endpoint. Should cache role in JWT claims or use a short-lived cache. |
| **`limit` and `offset` have no upper bounds** | **Low** | Admin endpoints accept arbitrary `limit` values (e.g., [`admin.py:342`](app/api/v1/admin.py:342)), potentially causing expensive queries. |
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
| **Technique quality classification is fragile** | **Medium** | [`get_technique_quality()`](app/api/v1/dialogue.py:61) uses keyword matching on `technique` and `feedback` strings. The keyword lists are hardcoded in the route handler, not in the scoring service. Default fallback is `'good'` (line 106), which means unrecognised techniques get generous scoring. |
| **`calculate_max_points_available()` has fragile subtraction logic** | **Medium** | [`scoring_service.py:191`](app/services/scoring_service.py:191) subtracts `best_first_choice_points` from the recursive result, but `get_max_points_for_path()` already includes the first node's best choice. This double-counting/subtraction logic may produce incorrect results for edge-case dialogue tree shapes. |
| **Max points quality detection differs from actual scoring** | **Medium** | [`calculate_max_points_for_choice()`](app/services/scoring_service.py:209) uses different keyword matching logic than [`get_technique_quality()`](app/api/v1/dialogue.py:61). For example, `calculate_max_points_for_choice()` checks for `'reflection'` to classify as excellent, while `get_technique_quality()` requires `'complex reflection'` for excellent. This means `max_points_available` may be calculated with different assumptions than actual scoring, leading to completion scores that don't accurately reflect performance. |
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
| No linter config | ⚠️ Unchanged | No `.flake8`, `pyproject.toml` (ruff/black), or `.pre-commit-config.yaml` |
| Mixed string quotes | ⚠️ Unchanged | Single and double quotes used inconsistently |
| `datetime.utcnow()` deprecated | ✅ Fixed | All files now use `datetime.now(timezone.utc)`. |

### Architecture Concerns

| Issue | Details |
|-------|---------|
| **Duplicate `get_user_profile()` helper** | Defined identically in [`dialogue.py:24`](app/api/v1/dialogue.py:24) and [`progress.py:17`](app/api/v1/progress.py:17). Should be extracted to a shared location. |
| **Technique quality logic split across files** | [`get_technique_quality()`](app/api/v1/dialogue.py:61) is in the route handler, [`calculate_max_points_for_choice()`](app/services/scoring_service.py:196) has its own quality detection in the scoring service. These should be unified. |
| **Two schema files with drift** | [`supabase_schema.sql`](supabase_schema.sql) references `app_user`/`mi_module` (old schema) vs [`supabase/migrations/`](supabase/migrations/) uses `users`/`learning_modules` (current). The old schema is confusing. |
| ~~**`test_connection()` references old table**~~ | ✅ **Fixed** — [`supabase.py:87`](app/core/supabase.py:87) now queries `learning_modules`. |
| **Legacy scoring method** | [`calculate_choice_points_legacy()`](app/services/scoring_service.py:82) is unused but maintained. |
| **In-memory chat sessions** | [`SESSIONS` dict](app/services/chat_service.py:14) doesn't survive restarts. Should use Redis or database. |
| **No database migrations runner** | Migrations are SQL files but there's no automated migration tool (like Alembic). |

### Tech Debt Summary

| Item | Priority | Effort |
|------|----------|--------|
| Persist chat sessions to DB/Redis | High | Medium |
| Unify technique quality classification | Medium | Low |
| Extract duplicate helpers | Low | Low |
| Add linter + formatter | Low | Low |
| Remove legacy schema files | Low | Trivial |
| Remove legacy scoring method | Low | Trivial |
| ~~Fix `test_connection()` table reference~~ | ~~Low~~ | ✅ Fixed |

---

## 6. Remaining Issues

### P0 — Critical (Fix Immediately)

_No P0 issues remain._ All critical security issues from the initial review have been addressed in PR #26.

### P1 — High Priority (Fix Soon)

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 1 | **Persist chat sessions to database** | Reliability | [`SESSIONS` dict](app/services/chat_service.py:14) is lost on restart/redeployment. Use Supabase or Redis. |
| 2 | ~~**Fix profile total_points double-counting on completion**~~ | Scoring | ✅ **Fixed** — Profile update now uses `current_choice_points` instead of the reassigned module total. |
| 3 | **Unify technique quality classification** | Scoring | [`get_technique_quality()`](app/api/v1/dialogue.py:61) and [`calculate_max_points_for_choice()`](app/services/scoring_service.py:196) use different keyword matching logic, causing `max_points_available` to be calculated with different assumptions than actual scoring. |
| 4 | ~~**Validate choice submission against current node**~~ | Security | ✅ **Fixed** — [`dialogue.py:214`](app/api/v1/dialogue.py:214) now validates node_id matches current_node_id, returns 400 on mismatch. |
| 5 | **Add cascade cleanup for user deletion** | Data Integrity | [`admin.py:283`](app/api/v1/admin.py:283) leaves orphaned data in `user_profiles`, `user_progress`, `dialogue_attempts`, `conversation_analyses`. |
| 6 | ~~**Add Pydantic model for `/chat-practice/analyze`**~~ | Security | ✅ **Fixed** — [`chat_practice.py:262`](app/api/v1/chat_practice.py:262) now uses `AnalyzeTranscriptRequest` Pydantic model. |
| 7 | **Implement proper token refresh** | Auth | Current refresh endpoint is a no-op. Implement Supabase refresh token flow or document that client should use Supabase client-side refresh. |

### P2 — Medium Priority (Plan for Next Sprint)

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 8 | **Add RLS policies for `conversation_analyses` and `user_feedback`** | Security | These tables lack RLS, meaning any authenticated Supabase client can read all records. |
| 9 | **Restrict token from query params** | Security | [`auth.py:207`](app/core/auth.py:207) accepts tokens in URL query params. Limit to WebSocket only. |
| 10 | **Add CSRF protection** | Security | Cookie-based auth without CSRF tokens is vulnerable. |
| 11 | **Fix `calculate_max_points_available()` subtraction logic** | Scoring | [`scoring_service.py:191`](app/services/scoring_service.py:191) fragile double-counting/subtraction. |
| 12 | **Add upper bounds on `limit`/`offset` params** | Security | Admin endpoints accept arbitrary values. Cap at reasonable maximum (e.g., 500). |
| 13 | **Add dialogue API tests** | Testing | `submit_choice()` is the most complex endpoint with no test coverage. |
| 14 | **Add admin API tests** | Testing | No tests for any admin endpoints. |
| 15 | **Add time-on-task tracking** | Analytics | Timestamp node visits for learning analytics. |
| 16 | ~~**Fix auth error message leaks**~~ | Security | ✅ **Fixed** — [`auth.py:200`](app/api/v1/auth.py:200) and [`auth.py:293`](app/api/v1/auth.py:293) now return generic messages; actual errors logged server-side. |
| 17 | ~~**Use Settings for OpenAI key in `conversation_analysis_service.py`**~~ | Consistency | ✅ **Fixed** — [`conversation_analysis_service.py:22`](app/services/conversation_analysis_service.py:22) now uses Settings class. |

### P3 — Nice to Have

| # | Issue | Category | Details |
|---|-------|----------|---------|
| 18 | Add linter and formatter (ruff/black + pre-commit) | Quality | No linting config exists. |
| 19 | ~~Replace remaining `datetime.utcnow()`~~ | Quality | ✅ **Fixed** — [`analysis_persistence_service.py:87`](app/services/analysis_persistence_service.py:87) now uses `datetime.now(timezone.utc)`. |
| 20 | Extract duplicate `get_user_profile()` helper | Quality | Defined identically in `dialogue.py` and `progress.py`. |
| 21 | Move `get_technique_quality()` to scoring service | Architecture | Currently in route handler, belongs in service layer. |
| 22 | Remove legacy schema files | Cleanup | `supabase_schema.sql` and `docs/schema.sql` reference old table names. |
| 23 | Remove `calculate_choice_points_legacy()` | Cleanup | Unused method in scoring service. |
| 24 | ~~Fix `test_connection()` table reference~~ | Cleanup | ✅ **Fixed** — [`supabase.py:87`](app/core/supabase.py:87) now references `learning_modules`. |
| 25 | Remove dead `ACCESS_TOKEN_EXPIRE_MINUTES` config | Cleanup | [`config.py:58`](app/config.py:58) is never used. |
| 26 | Add team/group model for HR analytics | Feature | Required for team-level reporting. |
| 27 | Add PDF export endpoints | Feature | HR teams need formatted reports. |
| 28 | Add alerting for stalled users | Feature | Scheduled job to identify inactive users. |
| 29 | Make scoring constants configurable | Feature | Allow tuning via environment variables or admin settings. |

---

## 7. Recommendations

### Immediate Next Steps (This Sprint)

1. **Fix the profile total_points double-counting** (P1-2) — This is a data integrity issue that affects leaderboards and user-facing scores. When a module completes, the profile update should only add the current choice's points, not the full module total.

2. **Unify technique quality classification** (P1-3) — Move [`get_technique_quality()`](app/api/v1/dialogue.py:61) into `ScoringService` and have [`calculate_max_points_for_choice()`](app/services/scoring_service.py:196) use the same logic. This ensures `max_points_available` is consistent with actual scoring.

3. **Add node validation to `submit_choice()`** (P1-4) — Add a check that `choice_data.node_id == progress['current_node_id']` to prevent out-of-order submissions.

4. **Add Pydantic model for analyze endpoint** (P1-6) — Replace `request: dict` with a typed model that validates `transcript` and `persona_name` fields.

### Short-Term (Next Sprint)

5. **Persist chat sessions** (P1-1) — Store sessions in Supabase `chat_sessions` table. This is the highest-impact reliability improvement.

6. **Add cascade delete** (P1-5) — Either use PostgreSQL `ON DELETE CASCADE` or clean up related tables in the admin action handler.

7. **Add dialogue and admin API tests** (P2-13, P2-14) — These are the largest untested areas. Focus on `submit_choice()` first as it has the most complex logic.

8. **Add RLS policies** (P2-8) — Protect `conversation_analyses` and `user_feedback` tables.

### Medium-Term (HR Features)

9. **Add team/group model** (P3-26) — Foundation for all HR analytics features.

10. **Add role-based access** — Extend roles to include `hr_manager` with team-scoped access.

11. **Add timeline/trend endpoints** — Per-user and per-team score trends over time.

12. **Add PDF export** — Server-side PDF generation for formal reports.

### Quality Improvements

13. **Add linter** (P3-18) — Configure `ruff` with pre-commit hooks. Low effort, high impact on consistency.

14. **Clean up legacy code** (P3-22, P3-23, P3-24, P3-25) — Remove dead code and old schema files.

---

*End of review.*
