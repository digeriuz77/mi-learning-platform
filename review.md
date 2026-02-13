# Comprehensive Code Review — MI Learning Platform

**Reviewer:** Kilo Code  
**Date:** 2026-02-12  
**Commit scope:** Full repository  

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Scoring Mechanisms](#2-scoring-mechanisms)
3. [Progress Tracking](#3-progress-tracking)
4. [Security Review](#4-security-review)
5. [Admin Dashboard Assessment](#5-admin-dashboard-assessment)
6. [General Code Quality](#6-general-code-quality)
7. [Recommendations](#7-recommendations)

---

## 1. Architecture Overview

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | **FastAPI** (Python 3.11) |
| Database / Auth | **Supabase** (PostgreSQL + Supabase Auth) |
| ORM / DB access | Supabase Python client (REST, no SQLAlchemy) |
| AI / LLM | **OpenAI API** (Responses endpoint, `gpt-4.1-mini` default) |
| Frontend | Server-rendered **Jinja2** templates + vanilla JS (`static/js/app.js`) |
| Deployment | **Docker** → **Railway** |
| Validation | **Pydantic v2** (`pydantic-settings`) |
| Auth tokens | **python-jose** (JWT HS256) |

### Folder Structure

```
app/
├── main.py                  # FastAPI app, CORS, routers, templates
├── config.py                # Pydantic Settings (env vars)
├── api/v1/                  # Route handlers
│   ├── admin.py             # Admin dashboard endpoints
│   ├── auth.py              # Register / login / password reset
│   ├── chat_practice.py     # AI chat practice sessions
│   ├── dialogue.py          # Module dialogue node traversal & scoring
│   ├── feedback.py          # User feedback collection
│   ├── leaderboard.py       # Points-based leaderboard
│   ├── modules.py           # Module listing, start, restart
│   ├── progress.py          # User progress retrieval
│   └── report_export.py     # HTML/JSON report export
├── core/
│   ├── auth.py              # JWT decode, AuthContext, dependencies
│   └── supabase.py          # Supabase client singletons
├── models/                  # Pydantic request/response models
├── services/
│   ├── scoring_service.py   # Points & level calculations
│   ├── chat_service.py      # OpenAI chat session management
│   ├── conversation_analysis_service.py  # AI-powered MI analysis
│   ├── analysis_persistence_service.py   # Save analyses to DB
│   └── personas.py          # Hardcoded persona definitions
├── db/migrations/           # Legacy SQL migration (unused?)
mi_modules/                  # JSON module content files
supabase/migrations/         # Supabase SQL migrations (001–010)
static/                      # CSS, JS, images
templates/                   # Jinja2 HTML (index.html, admin.html)
tests/                       # Pytest tests
scripts/                     # Utility scripts (import, scoring fixes)
```

### How the App Is Organised

The platform is a **Motivational Interviewing (MI) training tool** with two main learning modes:

1. **Structured Dialogue Modules** — branching dialogue trees where users pick practitioner responses and receive scored feedback.
2. **AI Chat Practice** — free-form conversations with LLM-powered simulated clients, analysed post-session using the MAPS framework.

Authentication is handled by Supabase Auth; the backend validates JWTs locally (fast path) with a Supabase API fallback. An admin dashboard provides user management and analytics. Data is stored in Supabase PostgreSQL with Row-Level Security (RLS) policies, though the backend frequently uses the **service-role key** to bypass RLS.

---

## 2. Scoring Mechanisms

### Where Scores Are Calculated

| Location | What It Does |
|----------|-------------|
| [`ScoringService.calculate_choice_points()`](app/services/scoring_service.py:43) | Awards points per dialogue choice based on technique quality |
| [`ScoringService.calculate_completion_score()`](app/services/scoring_service.py:233) | Computes module completion percentage (0–100) |
| [`ScoringService.calculate_level()`](app/services/scoring_service.py:100) | Maps cumulative points → level (1–10) |
| [`ScoringService.calculate_max_points_available()`](app/services/scoring_service.py:121) | Traverses dialogue tree for optimal-path max points |
| [`ScoringService.calculate_max_points_for_choice()`](app/services/scoring_service.py:195) | Max points for a single choice (best-case bonuses) |
| [`get_technique_quality()`](app/api/v1/dialogue.py:61) | Classifies choice quality via keyword matching |
| [`evokes_change_talk()`](app/api/v1/dialogue.py:115) | Heuristic for whether a choice evokes change talk |
| [`submit_choice()`](app/api/v1/dialogue.py:187) | Orchestrates scoring, progress update, profile update |
| [`conversation_analysis_service.analyze_conversation()`](app/services/conversation_analysis_service.py:135) | LLM-based MAPS scoring (1–5 scale) for chat practice |

### Where Scores Are Stored

- **`user_progress`** table: `points_earned`, `completion_score`, `nodes_completed`, `nodes_visited`, `technique_quality_counts`
- **`user_profiles`** table: `total_points`, `level`, `modules_completed`, `change_talk_evoked`
- **`dialogue_attempts`** table: per-choice attempt records with `points_earned`
- **`conversation_analyses`** table: AI analysis scores for chat practice

### Where Scores Are Displayed

- [`get_user_stats()`](app/api/v1/progress.py:29) — returns all module progress with scores
- [`get_leaderboard()`](app/api/v1/leaderboard.py:17) — ranked by `total_points`
- [`get_dashboard_stats()`](app/api/v1/admin.py:50) — admin aggregate stats
- Frontend `app.js` renders scores in the UI

### Issues & Observations

#### Hardcoded Magic Numbers

| Constant | Value | Location |
|----------|-------|----------|
| `CORRECT_TECHNIQUE_POINTS` | 100 | [`scoring_service.py:17`](app/services/scoring_service.py:17) |
| `FIRST_ATTEMPT_BONUS` | 50 | [`scoring_service.py:18`](app/services/scoring_service.py:18) |
| `CHANGE_TALK_BONUS` | 50 | [`scoring_service.py:19`](app/services/scoring_service.py:19) |
| `MODULE_COMPLETION_BONUS` | 200 | [`scoring_service.py:20`](app/services/scoring_service.py:20) |
| `EXCELLENT_POINTS` | 150 | [`scoring_service.py:23`](app/services/scoring_service.py:23) |
| `GOOD_POINTS` | 100 | [`scoring_service.py:24`](app/services/scoring_service.py:24) |
| `ACCEPTABLE_POINTS` | 50 | [`scoring_service.py:25`](app/services/scoring_service.py:25) |
| `POOR_POINTS` | 0 | [`scoring_service.py:26`](app/services/scoring_service.py:26) |
| `LEVEL_THRESHOLDS` | [0, 500, …, 30000] | [`scoring_service.py:29`](app/services/scoring_service.py:29) |
| `MAX_TURNS` | 20 | [`chat_service.py:25`](app/services/chat_service.py:25) |
| `ModuleResponse.points` | 500 (default) | [`models/modules.py:44`](app/models/modules.py:44) |

**Finding:** All scoring constants are class-level attributes in `ScoringService`, which is good for discoverability but they are not configurable at runtime or via environment variables. If scoring needs to be tuned per deployment or A/B tested, this requires code changes.

#### Technique Quality Classification Is Fragile

[`get_technique_quality()`](app/api/v1/dialogue.py:61) uses keyword matching on the `technique` and `feedback` strings from module JSON. This is brittle:

- The keyword lists (`non_mi_keywords`, `excellent_keywords`, etc.) are hardcoded in the route handler, not in the scoring service.
- A module author could inadvertently use wording that triggers the wrong classification.
- The default fallback is `'good'` (line 106), which means unrecognised techniques get generous scoring.

#### `calculate_max_points_available()` Has a Subtle Bug

In [`scoring_service.py:191`](app/services/scoring_service.py:191), the method subtracts `best_first_choice_points` from the recursive result, but `get_max_points_for_path()` already includes the first node's best choice. This double-counting/subtraction logic is fragile and may produce incorrect results for certain dialogue tree shapes (e.g., single-node modules or modules where the start node has no choices).

#### Completion Score Double-Counting on Module Complete

In [`dialogue.py:337`](app/api/v1/dialogue.py:337), when a module completes, `points_earned` is reassigned to `total_points_earned` (which already includes the current choice's points). Then at line 345, the update adds `progress.get('points_earned', 0) + points_earned`, which could double-count the current choice's points since `points_earned` was overwritten.

#### Legacy Methods Still Present

[`calculate_choice_points_legacy()`](app/services/scoring_service.py:81) and [`CORRECT_TECHNIQUE_POINTS`](app/services/scoring_service.py:17) are kept for backward compatibility but the new quality-based system uses different constants (`EXCELLENT_POINTS`, etc.). Tests still reference the old constants, which could mask regressions.

---

## 3. Progress Tracking

### How Progress Is Tracked

1. **Module start** → creates a `user_progress` row with `status: 'in_progress'` and `current_node_id` set to the start node ([`modules.py:192`](app/api/v1/modules.py:192)).
2. **Choice submission** → updates `nodes_completed`, `nodes_visited`, `technique_quality_counts`, `points_earned`, and `current_node_id` ([`dialogue.py:340`](app/api/v1/dialogue.py:340)).
3. **Module completion** → sets `status: 'completed'`, calculates `completion_score`, sets `completed_at` ([`dialogue.py:348`](app/api/v1/dialogue.py:348)).
4. **Profile aggregation** → `user_profiles.total_points`, `level`, `modules_completed` are updated on each choice submission.

### Persistence

Progress is **persistent** in Supabase PostgreSQL. Chat practice sessions, however, are stored **in-memory only** ([`chat_service.py:14`](app/services/chat_service.py:14): `SESSIONS: Dict[str, Dict[str, Any]] = {}`). This means:

- **Chat sessions are lost on server restart or redeployment.**
- There is no way to resume a chat session after a crash.
- The `cleanup_old_sessions()` function exists but is never called automatically.

### Reset / Manipulation

- **Module restart** is supported via [`restart_module()`](app/api/v1/modules.py:225), which resets progress and deducts points from the profile.
- **No rate limiting** on restarts — a user could repeatedly restart and replay modules to farm points (though points are deducted on restart, the net effect depends on scoring).
- **No server-side validation** that `choice_id` corresponds to the current `node_id` in the user's progress. A user could potentially submit choices for nodes they haven't reached.

### Gaps

| Gap | Severity |
|-----|----------|
| Chat practice sessions are in-memory only; lost on restart | **High** |
| No `nodes_visited` reset on module restart (field reset is missing from restart update) | **Medium** |
| No `technique_quality_counts` reset on module restart | **Medium** |
| Partially completed modules are saved, but there's no "resume" UX guidance | **Low** |
| No timestamp tracking for individual node visits (time-on-task) | **Medium** |
| `dialogue_attempts` are never cleaned up on module restart | **Low** |

---

## 4. Security Review

### Authentication

| Finding | Severity | Details |
|---------|----------|---------|
| **Legacy auth returns demo user on failure** | **Critical** | [`get_current_user_legacy()`](app/core/auth.py:349) returns a hardcoded `demo-user-123` when auth fails. If any endpoint still uses this dependency, it bypasses authentication entirely. |
| **Token accepted from query params and cookies** | **Medium** | [`get_auth_context()`](app/core/auth.py:206) checks `request.query_params.get("token")` and `request.cookies.get("access_token")`. Query param tokens appear in server logs and browser history. |
| **JWT audience verification disabled** | **Low** | [`decode_jwt_token()`](app/core/auth.py:87) sets `verify_aud: False`. While Supabase tokens may not use standard `aud`, this weakens token validation. |
| **7-day token expiry** | **Medium** | [`ACCESS_TOKEN_EXPIRE_MINUTES = 10080`](app/config.py:58) (7 days). Long-lived tokens increase the window for token theft. |
| **Token refresh is a no-op** | **Medium** | [`refresh_token()`](app/api/v1/auth.py:450) just returns the same token if valid, and fails if expired. No actual refresh token flow is implemented. |

### Authorisation

| Finding | Severity | Details |
|---------|----------|---------|
| **Admin check queries DB on every request** | **Low** | [`require_admin()`](app/api/v1/admin.py:21) queries the `users` table on every admin endpoint call. Should cache or embed role in JWT claims. |
| **Feedback stats endpoint has broken auth check** | **High** | [`get_feedback_stats()`](app/api/v1/feedback.py:106) checks `auth.role` but `AuthContext` has no `role` attribute — this will always raise an `AttributeError`, making the endpoint unusable. |
| **No authorisation on chat practice endpoints** | **Medium** | Chat endpoints use `get_current_user` but don't verify the session belongs to the authenticated user. Any authenticated user can interact with any session by guessing the UUID. |
| **Admin can delete users without cascade cleanup** | **Medium** | [`perform_admin_action()`](app/api/v1/admin.py:269) deletes from `users` table but doesn't clean up `user_profiles`, `user_progress`, `dialogue_attempts`, or `conversation_analyses`. |

### Data Validation

| Finding | Severity | Details |
|---------|----------|---------|
| **`/chat-practice/analyze` accepts raw dict** | **Medium** | [`analyze_transcript()`](app/api/v1/chat_practice.py:250) accepts `request: dict` with no Pydantic validation. Arbitrary data is passed to the LLM prompt. |
| **No input sanitisation on search parameters** | **Medium** | [`get_users()`](app/api/v1/admin.py:134) passes `search` directly to `.ilike()`. While Supabase client likely parameterises this, the pattern is risky. |
| **`limit` and `offset` have no upper bounds** | **Low** | Admin endpoints accept arbitrary `limit` values, potentially causing expensive queries. |

### XSS / CSRF

| Finding | Severity | Details |
|---------|----------|---------|
| **HTML report injection** | **High** | [`_generate_html_report()`](app/api/v1/report_export.py:31) interpolates user-controlled analysis data (strengths, summaries, suggestions) directly into HTML via f-strings with **no escaping**. An attacker could inject `<script>` tags via crafted analysis data. |
| **No CSRF protection** | **Medium** | The app uses cookie-based token storage ([`auth.py:211`](app/core/auth.py:211)) but has no CSRF tokens. State-changing POST endpoints are vulnerable to CSRF if cookies are used. |
| **Supabase anon key exposed in templates** | **Low** | [`main.py:117`](app/main.py:117) passes `supabase_anon_key` to templates. This is by design for Supabase client-side usage, but the anon key should be paired with strict RLS policies. |

### Secrets Management

| Finding | Severity | Details |
|---------|----------|---------|
| **Hardcoded fallback URL** | **Low** | [`auth.py:539`](app/api/v1/auth.py:539) has a hardcoded Railway URL as fallback for password reset redirects. |
| **OpenAI key accessed via `os.getenv()` directly** | **Low** | [`chat_service.py:30`](app/services/chat_service.py:30) and [`conversation_analysis_service.py:22`](app/services/conversation_analysis_service.py:22) read `OPENAI_API_KEY` directly from env instead of through the Settings class. Inconsistent with the rest of the config. |
| **Proxy env vars forcibly deleted** | **Low** | [`supabase.py:12`](app/core/supabase.py:12) deletes `HTTP_PROXY`/`HTTPS_PROXY` from `os.environ`. This is a workaround that could break other services in the same process. |

### API Security

| Finding | Severity | Details |
|---------|----------|---------|
| **CORS allows all origins by default** | **High** | [`CORS_ORIGINS` defaults to `["*"]`](app/config.py:54) and [`main.py:64`](app/main.py:64) applies it with `allow_credentials=True`. This is a dangerous combination — browsers will send cookies cross-origin. |
| **Global exception handler leaks internal errors** | **High** | [`global_exception_handler()`](app/main.py:72) returns `str(exc)` and `type(exc).__name__` to the client. Stack traces and internal details could leak. |
| **Error messages expose implementation details** | **Medium** | Multiple endpoints return `str(e)` in error responses (e.g., [`admin.py:115`](app/api/v1/admin.py:115), [`modules.py:213`](app/api/v1/modules.py:213)). |
| **No rate limiting** | **Medium** | No rate limiting on login, registration, password reset, or API endpoints. Vulnerable to brute-force and abuse. |
| **Health endpoint exposes config details** | **Low** | [`detailed_health_check()`](app/main.py:164) reveals whether keys are configured and partial Supabase URL. |

### Supabase / Firestore Rules

- RLS policies exist for `users`, `user_profiles`, `user_progress`, `dialogue_attempts`, `learning_modules`, and `user_score` ([`002_email_privacy_rls.sql`](supabase/migrations/002_email_privacy_rls.sql)).
- However, the backend **bypasses RLS** on nearly every operation by using `get_supabase_admin()` (service role key). This means RLS is effectively a safety net only for direct Supabase client access from the frontend.
- **No RLS policies found for `conversation_analyses` or `user_feedback` tables** — these may be accessible to any authenticated user via the Supabase client.

### Client-Side Logic That Should Be Server-Side

| Issue | Details |
|-------|---------|
| **Supabase client initialised in frontend** | [`config.js`](static/js/config.js) and templates expose the anon key. While this is standard Supabase practice, any client-side queries bypass backend validation. |
| **PDF generation is client-side** | Reports are generated as HTML with a "Print" button. No server-side PDF generation exists. |

---

## 5. Admin Dashboard Assessment

### Current Functionality

The admin dashboard ([`admin.py`](app/api/v1/admin.py)) provides:

- **Dashboard stats**: total users, new users (24h), modules completed, average progress
- **User management**: list, search, promote/demote, ban/unban, delete
- **Module stats**: per-module enrollment, completion, in-progress counts
- **Practice analytics**: aggregate MI scores, per-user analytics, leaderboard
- **Feedback**: aggregate stats, recent feedback list
- **Comprehensive analytics**: via Supabase RPC functions

### Current Gaps

1. **No CSV/PDF export** — only HTML report export exists for individual analyses
2. **No team/group concept** — users are flat; no organisational hierarchy
3. **No time-on-task metrics** — no timestamps on individual node visits
4. **No alerting** — no mechanism to flag stalled or underperforming users
5. **No role-based dashboard views** — admin is binary (admin or not); no HR role
6. **User list doesn't include actual points/modules** — hardcoded to 0 at [`admin.py:149-150`](app/api/v1/admin.py:149)

### Proposed Improvements for HR Team

#### 5.1 Per-User and Team-Level Analytics

```
Proposed endpoints:
  GET /api/v1/admin/analytics/user/{user_id}/timeline
  GET /api/v1/admin/analytics/team/{team_id}/summary
  GET /api/v1/admin/analytics/team/{team_id}/members
```

- Add a `teams` table with `team_id`, `name`, `manager_id`
- Add `team_id` FK to `users` table
- Aggregate per-team: completion rates, average scores, points distribution
- Per-user timeline: module completions over time, score trends, practice frequency

#### 5.2 Exportable Reports (CSV/PDF)

```
Proposed endpoints:
  GET /api/v1/admin/export/users?format=csv
  GET /api/v1/admin/export/team/{team_id}?format=pdf
  GET /api/v1/admin/export/progress?format=csv&date_from=...&date_to=...
```

- Use `python-csv` for CSV generation (streaming response)
- Use `weasyprint` or `reportlab` for server-side PDF generation
- Include: user name, email, team, modules completed, scores, last active date
- Support date range filtering

#### 5.3 Completion Rates and Time-on-Task Metrics

- Add `node_visited_at` timestamp to `dialogue_attempts` or a new `node_visits` table
- Calculate: average time per node, average time to complete module, time between sessions
- Dashboard widgets: completion funnel (started → 50% → completed), dropout points

#### 5.4 Leaderboards and Comparative Views

- Team leaderboards (average score, total completions)
- Individual leaderboards within teams
- Comparative charts: user vs team average vs platform average
- Period-based leaderboards (weekly, monthly)

#### 5.5 Alerting for Stalled or Underperforming Users

```
Proposed:
  - Cron job / scheduled task checking for:
    - Users with in_progress modules not updated in >7 days
    - Users with completion scores below threshold
    - Users who registered but never started a module
  - Notification via email (Supabase Edge Functions) or webhook
  - Admin dashboard "Attention Required" panel
```

#### 5.6 Role-Based Access

| Role | Access |
|------|--------|
| **Learner** | Own progress, modules, practice sessions |
| **HR Manager** | Team members' progress, team analytics, exports (no user management) |
| **Admin** | Full access: user management, all analytics, system config |

- Extend the `role` column: `user`, `hr_manager`, `admin`
- Add `require_hr_or_admin()` dependency
- HR managers see only their team's data (filter by `team_id`)

---

## 6. General Code Quality

### Positive Aspects

- **Well-structured FastAPI project** with clear separation of concerns (routes, services, models, core)
- **Pydantic models** for request/response validation
- **Comprehensive scoring tests** in [`test_scoring_service.py`](tests/test_scoring_service.py)
- **Good docstrings** throughout the codebase
- **Graceful degradation** — app starts even if settings fail to load ([`main.py:23`](app/main.py:23))
- **RLS policies** defined for core tables

### Linting & Consistency

| Issue | Details |
|-------|---------|
| **No linter config** | No `.flake8`, `pyproject.toml` (ruff/black), or `.pre-commit-config.yaml` found |
| **Mixed string quotes** | Single and double quotes used inconsistently |
| **Inconsistent import style** | Some files use `from datetime import datetime`, others import the module |
| **`datetime.utcnow()` deprecated** | Used in multiple files; should use `datetime.now(timezone.utc)` |
| **Unused imports** | `Client` imported but not always used as type hint |

### Error Handling

| Issue | Details |
|-------|---------|
| **Bare `except Exception`** | Many endpoints catch all exceptions and return 500 with `str(e)`. Should catch specific exceptions. |
| **Silent failures** | [`save_conversation_analysis()`](app/services/analysis_persistence_service.py:101) catches all exceptions and returns `None`. Callers may not know data wasn't saved. |
| **Fallback response on OpenAI error** | [`chat_service.py:192`](app/services/chat_service.py:192) returns a canned response on API error. User doesn't know the AI failed. |

### Accessibility

- No accessibility audit of frontend templates was possible from backend code alone
- HTML report ([`report_export.py`](app/api/v1/report_export.py)) uses semantic HTML but lacks ARIA attributes
- Color-only score indicators (green/orange/red) may not be accessible to colorblind users

### Tech Debt

| Item | Details |
|------|---------|
| **Two schema files** | [`supabase_schema.sql`](supabase_schema.sql) (old `app_user`/`mi_module` schema) vs [`supabase/migrations/`](supabase/migrations/) (current `users`/`learning_modules` schema). The old schema is confusing and should be removed or clearly marked as deprecated. |
| **Legacy auth function** | [`get_current_user_legacy()`](app/core/auth.py:349) returns demo user on auth failure. Should be removed. |
| **Legacy scoring method** | [`calculate_choice_points_legacy()`](app/services/scoring_service.py:81) is unused but maintained. |
| **In-memory chat sessions** | [`SESSIONS` dict](app/services/chat_service.py:14) doesn't survive restarts. Should use Redis or database. |
| **Duplicate helper functions** | [`get_user_profile()`](app/api/v1/dialogue.py:24) is defined identically in both `dialogue.py` and `progress.py`. |
| **`on_event("startup")` deprecated** | [`main.py:206`](app/main.py:206) uses deprecated FastAPI lifecycle. Should use `lifespan` context manager. |
| **Typo in report export** | [`report_export.py:52`](app/api/v1/report_export.py:52): `evocation_democation_demonstrated` should be `evocation_demonstrated`. This means the Evocation field in HTML reports is always `False`. |
| **`get_next_level_threshold()` is wrong** | [`scoring_service.py:312`](app/services/scoring_service.py:312): Returns `LEVEL_THRESHOLDS[current_level - 1]` which is the *current* level's threshold, not the next level's. |
| **No database migrations runner** | Migrations are SQL files but there's no automated migration tool (like Alembic). |
| **`supabase_schema.sql` references `mi_module`** | But the actual app uses `learning_modules`. Schema drift. |

---

## 7. Recommendations

### P0 — Critical (Fix Immediately)

| # | Recommendation | Rationale |
|---|---------------|-----------|
| 1 | **Remove `get_current_user_legacy()` or ensure it's never used** | Returns a demo user on auth failure, completely bypassing authentication. Any endpoint using this dependency is unauthenticated. |
| 2 | **Fix CORS configuration** | `allow_origins=["*"]` with `allow_credentials=True` is a security misconfiguration. Set specific origins in production. |
| 3 | **Sanitise HTML report output** | [`_generate_html_report()`](app/api/v1/report_export.py:31) is vulnerable to XSS. Use `html.escape()` or a templating engine with auto-escaping. |
| 4 | **Stop leaking exception details to clients** | Replace `str(exc)` in error responses with generic messages. Log the full error server-side. |
| 5 | **Fix the `evocation_democation_demonstrated` typo** | [`report_export.py:52`](app/api/v1/report_export.py:52) — Evocation is always shown as not demonstrated in reports. |

### P1 — High Priority (Fix Soon)

| # | Recommendation | Rationale |
|---|---------------|-----------|
| 6 | **Persist chat sessions to database** | In-memory `SESSIONS` dict is lost on restart. Use Supabase or Redis. |
| 7 | **Add rate limiting** | No rate limiting on login, registration, or API endpoints. Use `slowapi` or similar. |
| 8 | **Fix `get_feedback_stats()` auth check** | [`feedback.py:115`](app/api/v1/feedback.py:115) references `auth.role` which doesn't exist on `AuthContext`. |
| 9 | **Add RLS policies for `conversation_analyses` and `user_feedback`** | These tables appear to lack RLS, meaning any authenticated Supabase client can read all records. |
| 10 | **Fix double-counting in `submit_choice()` completion logic** | [`dialogue.py:337-345`](app/api/v1/dialogue.py:337) may double-count points on module completion. |
| 11 | **Reset `nodes_visited` and `technique_quality_counts` on module restart** | [`modules.py:267`](app/api/v1/modules.py:267) doesn't reset these fields, leading to stale data. |
| 12 | **Validate session ownership in chat endpoints** | Any authenticated user can interact with any chat session by knowing the UUID. |
| 13 | **Implement proper token refresh** | Current refresh endpoint is a no-op. Implement Supabase refresh token flow. |
| 14 | **Fix `get_next_level_threshold()`** | Returns current level threshold instead of next level's. |

### P2 — Nice to Have (Plan for Next Sprint)

| # | Recommendation | Rationale |
|---|---------------|-----------|
| 15 | **Add linter and formatter** | Configure `ruff` or `black` + `isort` with pre-commit hooks. |
| 16 | **Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`** | `utcnow()` is deprecated in Python 3.12+. |
| 17 | **Move technique quality classification to scoring service** | [`get_technique_quality()`](app/api/v1/dialogue.py:61) belongs in `ScoringService`, not in the route handler. |
| 18 | **Extract duplicate `get_user_profile()` helper** | Defined identically in `dialogue.py` and `progress.py`. Move to a shared location. |
| 19 | **Add team/group model for HR analytics** | Required for team-level reporting and role-based access. |
| 20 | **Add CSV export endpoints** | HR teams need exportable data for compliance and reporting. |
| 21 | **Add time-on-task tracking** | Timestamp node visits for learning analytics. |
| 22 | **Migrate to FastAPI `lifespan`** | Replace deprecated `on_event("startup")`. |
| 23 | **Clean up legacy schema files** | Remove or clearly deprecate `supabase_schema.sql` and `docs/schema.sql`. |
| 24 | **Add integration tests** | Current tests only cover scoring service. Need API endpoint tests with mocked Supabase. |
| 25 | **Make scoring constants configurable** | Allow tuning via environment variables or admin settings. |
| 26 | **Add OpenAI key to Settings class** | Currently read via `os.getenv()` directly, inconsistent with other config. |
| 27 | **Add automated session cleanup** | `cleanup_old_sessions()` exists but is never called. Add a background task or cron. |
| 28 | **Add alerting for stalled users** | Scheduled job to identify users who haven't progressed in N days. |

---

*End of review.*
