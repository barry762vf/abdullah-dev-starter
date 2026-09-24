# 📋 .ai/TODO.md — Master Task Backlog

> **Document:** `.ai/TODO.md`  
> **Status:** Active Backlog  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 🚀 Phase 0: Repository Foundation & Scaffolding
- [x] Analyze requirements and inspect engineer's Obsidian Second Brain context.
- [x] Complete comprehensive architectural documentation suite (engineering guides in `docs/`, bridge in root `AI_CONTEXT.md`).
- [x] Establish `.ai/` collaboration memory system (`PROJECT_CONTEXT.md`, `CURRENT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `BUGS.md`, `AGENT_HANDOFF.md`, `CHANGELOG_AI.md`).
- [x] Initialize local Git repository and create root `.gitignore` (Python, Node, Docker, environment exclusions).
- [x] Create root `.dockerignore`.
- [x] Create master `.env.example` with documented environment configurations.
- [x] Create root `docker-compose.yml` defining PostgreSQL 16 service.
- [x] Create developer automation scripts (`scripts/dev.ps1`, `scripts/dev.sh`).
- [x] Initialize `README.md` with quickstart guide and architecture overview; add `LICENSE`.
- [x] Place the engineering guides in the specified `docs/` directory.
- [x] Verify Compose configuration and healthy PostgreSQL startup on a live Docker host (`docker compose config`, `docker compose up -d --wait db`, `docker compose ps db`, `docker compose exec db pg_isready -U postgres -d abdullah_core_dev`, and a SQL query confirming PostgreSQL 16.15).

---

## ⚙️ Phase 1: Backend Foundation & Core Infrastructure
- [x] Scaffold `backend/` directory structure for the Phase 1 application and tests.
- [x] Create `backend/pyproject.toml`, `backend/requirements.txt`, and `backend/requirements-dev.txt`.
- [x] Implement `backend/app/core/config.py` using Pydantic Settings v2.
- [x] Implement `backend/app/core/logging.py` for structured JSON logging with request ID tracing.
- [x] Implement `backend/app/core/exceptions.py` with custom error hierarchy and Starlette handlers.
- [x] Implement `backend/app/api/v1/health.py` endpoint with uptime and explicit `database: not_configured` status until Phase 2.
- [x] Implement `backend/app/main.py` assembling middleware, CORS, security headers, and router.
- [x] Write Settings unit and health/error API integration tests; verify live Uvicorn startup and `/docs`.

---

## 🗄️ Phase 2: Database Layer & Declarative Models
- [x] Implement `backend/app/core/database.py` with async SQLAlchemy 2.0 engine, sessionmaker, and request-scoped dependency.
- [x] Implement `backend/app/models/base.py` with database-generated UUID PK and timezone-aware timestamp mixins.
- [x] Implement `backend/app/models/user.py` (`User`, `Role`, `UserRole`).
- [x] Implement `backend/app/models/token.py` (`RefreshToken` hash storage).
- [x] Implement `backend/app/models/audit.py` (`AuditLog`).
- [x] Initialize Alembic with async migration support in `backend/alembic/`.
- [x] Create reversible initial migration revision (`001_initial_schema.py`) and verify upgrade/downgrade/re-upgrade on PostgreSQL.
- [x] Implement explicit idempotent baseline role seeder (`backend/app/core/seed.py`).
- [x] Verify async connectivity, model defaults/constraints/cascades, schema drift, readiness, test DB isolation, and all Phase 1 regressions.

## 🔧 Pre-Phase-3 Foundation Hardening
- [x] Independently verify every §3 finding in `.ai/REVIEW_CLAUDE.md` against code and the dedicated test database.
- [x] Fix ORM user deletion with loaded role assignments and refresh tokens; add `session.delete()`/commit regression coverage.
- [x] Add Alembic `002_pre_auth_hardening` for unique `lower(email)`, restricted role deletion, and nullable token `revoked_at`.
- [x] Hide bound SQL parameters and sanitize database exception logs, including PostgreSQL constraint details.
- [x] Change the migration test to exercise `base → head → base → head` and run Alembic drift check.
- [x] Apply staging security guards and explicit async relationship loading; test each behavior.
- [x] Record Phase 3 authorization and refresh-token decisions in ADR 009 and `docs/AUTH_STRATEGY.md`.

---

## 🔐 Phase 3: Authentication & Role-Based Authorization (RBAC)
- [x] Add secure initial superadmin provisioning to the Phase 2 seed command using Argon2id and configured credentials; never reset an existing admin password.
- [x] Implement `backend/app/core/security.py` (Argon2id password hashing and JWT encoding/decoding).
- [x] Create Pydantic v2 auth and user schemas (`backend/app/schemas/auth.py`, `backend/app/schemas/user.py`).
- [x] Implement `backend/app/services/auth_service.py` (login, register, token rotation, revocation).
- [x] Implement `backend/app/services/user_service.py` (profile retrieval, user updates).
- [x] Implement FastAPI authentication dependencies (`backend/app/api/deps.py`: import existing `get_db` from `app.core.database`; add `get_current_user`, `get_current_active_user`, `require_role`).
- [x] Load current `is_active` and role membership from PostgreSQL on protected requests; use atomic refresh rotation and known-reuse handling from ADR 009.
- [x] Make registration fail clearly if baseline `user` role is absent; ensure seed command runs in auth integration tests and deployment bootstrap.
- [x] Revisit the permanent `INITIAL_ADMIN_PASSWORD` startup requirement during secure administrator bootstrap.
- [x] Use only the ASGI resolved peer IP for Phase 3 auth limits/audit and document trusted-proxy deployment requirements.
- [x] Implement API endpoints (`/api/v1/auth/register`, `/login`, `/refresh`, `/logout`).
- [x] Implement `/api/v1/users/me` profile endpoints.
- [x] Write pytest integration suite verifying auth, token rotation, and RBAC guards.

---

## 🔍 Phase 3 Security Review Follow-ups (`.ai/REVIEW_PHASE3_AUTH_CLAUDE.md`)
Independent review, 2026-09-24: 0 CRITICAL, 2 HIGH, 4 MEDIUM, 11 LOW. Codex's independent classifications and dispositions are recorded in `.ai/REVIEW_PHASE3_AUTH_CODEX.md`; Claude's original report is preserved.

**Before browser auth integration (Phase 4):**
- [x] HIGH-01: Verify the concurrent-refresh behavior and define the Web Locks/BroadcastChannel browser contract in `docs/AUTH_STRATEGY.md`, preserving ADR 009's strict reuse rule.
- [x] HIGH-02: Choose the same-origin `/api/*` proxy topology in ADR 011 and deployment/auth docs; resolve BUG-008 at the architecture level.

**Before any public deployment:**
- [x] MEDIUM-01: Offload Argon2 hashing/verification for registration, login and bootstrap to a bounded AnyIO worker pool; retain the dummy-hash path.
- [x] MEDIUM-02 checkpoint: Confirm Uvicorn default forwarding behavior, pin `--no-proxy-headers` for local direct startup, and document exact production proxy requirements. Live ingress configuration remains Phase 7.
- [ ] MEDIUM-03 deployment extension: Add shared/edge and account-aware abuse controls before claiming production resistance to IP rotation, IPv6 churn or the bounded-store eviction; keep the current starter limiter as best effort.
- [x] MEDIUM-04: Require explicit `ENVIRONMENT` and test missing-mode startup failure.

**Test hardening:**
- [x] Verify login/register reject `text/plain` and form bodies with 422.
- [x] (Phase 6) Add remaining regression tests in the relevant phase: JWT `alg:none`/HS512/missing claims/non-UUID `sub`/deleted user; ignored `roles` claim; cookie `Path`/`Max-Age`/`Secure`; bootstrap advisory-lock race; disabled user at refresh revokes all sessions; route inventory (all non-public routes use `get_current_active_user`); failure after the conditional UPDATE leaves the old token valid; log redaction on reuse/bootstrap paths; a barrier-based true refresh race.

**Low-priority hardening:**
- [x] LOW-01 documentation: Access JWTs remain valid ≤15 min after logout/reuse; Phase 4 clears client caches. Consider `users.sessions_invalid_before` with password reset later.
- [ ] LOW-02/03 operations: Bootstrap-before-registration is documented; printing created/skipped outcome and disabled-admin recovery remain.
- [ ] LOW-04: Make `get_current_user` private or clearly documented as not checking `is_active`.
- [ ] LOW-05: Add fixed audit `reason` codes, audit refresh denial for inactive accounts, strip control characters from stored user agents.
- [x] LOW-06: Use `ACCESS_TOKEN_MINUTES`/`REFRESH_TOKEN_DAYS` constants for JWT/database expiry and cookies.
- [ ] LOW-07: Consider `check_needs_rehash` on login and NFKC password normalization (before real users exist).
- [x] LOW-08/10/11: Test JSON-only auth requests and document registration's 409 account enumeration and cookie-only refresh for non-browser clients.
- [x] LOW-09 architecture: Choose same-origin host-only cookies in ADR 011; same-site subdomain overrides must address sibling-subdomain cookie behavior.

---

## 🎨 Phase 4: Frontend Shell, Modern UI & Bilingual Engine (RTL / LTR)
- [x] Choose one-origin SPA/API topology in ADR 011 before wiring browser cookie auth (BUG-008 resolved at architecture level).
- [x] Implement the `docs/AUTH_STRATEGY.md` browser refresh contract: in-tab single-flight, Web Lock across tabs, `/users/me` probe, non-secret BroadcastChannel signals, no refresh retry after ambiguous failure, and logout cache clearing.
- [x] Use a relative `/api/v1` client URL and Vite `/api/*` development proxy; verify the local route against a live FastAPI health endpoint.
- [ ] Implement and test the production same-origin Pages `/api/*` edge route before deployment (Phase 7 gate).
- [x] Scaffold `frontend/` with React 18, Vite 5, and TypeScript.
- [x] Configure Tailwind CSS logical properties and Cairo + Inter fonts with system fallbacks.
- [x] Set up `i18next` with Arabic (`locales/ar/translation.json`) and English (`locales/en/translation.json`).
- [x] Implement `useDirection` updating root `lang` and `dir`, with language preference persistence.
- [x] Configure relative Axios API client, credentials, RFC 7807 errors, and strict refresh coordination (`src/lib/api.ts`).
- [x] Configure TanStack Query client (`src/lib/queryClient.ts`).
- [x] Build responsive layout shell (`AppShell`, `Navbar`, `Sidebar`, `LanguageToggle`, `ThemeToggle`) and loading/error/empty/not-found primitives.
- [x] Build responsive `LoginPage` and `RegisterPage` with form validation and actual Phase 3 auth routes.
- [x] Implement `AuthGuard` protecting the generic dashboard placeholder; backend remains authorization authority.
- [x] Verify mobile, tablet, and desktop English LTR and Arabic RTL layouts in a browser; fix the narrow-header wrap.
- [x] Pass frontend tests, TypeScript check, lint, build, and local API proxy smoke test.
- [x] Takeover verification (Claude): emit login/logout signals inside the Web Lock, bound auth request time, apply saved direction before first paint, make the mobile drawer an accessible modal dialog, fix the language-toggle accessible name, mirror directional icons in RTL, and verify the proxied register→login→refresh→logout lifecycle live.

---

## 🛡️ Phase 5: Admin Dashboard & User Management
- [x] Implement backend admin endpoints (`/api/v1/admin/users`, `PATCH /users/{id}`, `/stats`, `/audit-logs`) with ADR 013 authorization, advisory-lock invariant, audit rows and tests.
- [x] Implement frontend `RoleGuard` restricting `/admin` to authorized roles (UX only).
- [x] Build admin dashboard overview with KPI metric cards.
- [x] Build user management data table (debounced search, role filter, pagination, superadmin role change, status toggle with confirmation).
- [x] Build audit log viewer with action filter and text-only details dialog.
- [x] Role filter uses `EXISTS` on the `user_roles` primary key (leading `user_id`); no extra `role_id` index needed yet. No hard-delete flow was added, so audit attribution is unchanged.
- [ ] Optional later: audit refused (403) admin attempts; add a user-detail view or bulk actions only if a project needs them.

---

## 🧪 Phase 6: Automated Testing Suite
- [x] Finalize backend pytest suite covering edge cases and security boundaries (99 tests; JWT forgery, cookies, route inventory, rollback, proven concurrency races, log redaction, CORS/headers, admin regressions).
- [x] Implement Vitest tests for language switching, forms, guards, cross-tab sign-out, logout, admin states and dialog focus (45 tests).
- [x] Set up coverage reporting (pytest-cov with greenlet tracing; @vitest/coverage-v8); reported, not enforced.
- [x] Add folder-based `unit`/`integration` markers, explicit `python-dotenv` and `pytest-cov` dev pins, `get_db` rollback/connection-release, CORS preflight and security-header tests, and a unit-tested `_test` database guard.
- [ ] Optional: tests for the seed CLI entry point and race-only `IntegrityError` branches (bootstrap, registration) if those paths change.

---

## 🚢 Phase 7: Production Containerization & CI/CD
- [ ] Configure exact trusted proxy IPs, strip untrusted forwarding headers, and add a shared auth rate limiter before multi-worker or multi-instance deployment.
- [ ] Verify the production Pages `/api/*` proxy preserves paths, methods, cookies and `Set-Cookie`, avoids API caching, and records the real client IP only through a trusted ingress; otherwise use edge rate limiting and mark app IP audit as proxy-derived.
- [ ] Assert `ENVIRONMENT=production`, strong secret, secure cookies, HTTPS origin and debug off in deployment automation; do not deploy an unchanged local `.env`.
- [ ] Resolve or formally accept BUG-013 by reviewing ADR 002's pinned Vite 5 / React Router 6 / Vitest 2 versions against npm advisories before shared development or public deployment; retest after any major upgrade.
- [ ] Write multi-stage, non-root `backend/Dockerfile`.
- [ ] Write multi-stage Nginx `frontend/Dockerfile`.
- [ ] Configure GitHub Actions workflow `backend-ci.yml`.
- [ ] Configure GitHub Actions workflow `frontend-ci.yml`.
- [ ] Create `docker-compose.prod.yml`.
- [ ] Revisit Supabase transaction-pooler compatibility, configurable pool limits, production docs visibility, readiness timeout, and container `.env` path before deployment.
- [ ] Add `backend/.dockerignore` if using `backend/` as Docker build context; decide whether public repository personal context and local paths should remain.
- [ ] Decide whether a separate audit-log database role or metadata naming convention is needed when schema/deployment complexity justifies it.

---

## 🔌 Phase 8: Reusable Extension Slots (Pluggable Modules)
- [ ] Define abstract interfaces (`backend/app/integrations/base.py`).
- [ ] Implement Gemini AI provider adapter slot.
- [ ] Implement Telegram Bot messenger adapter slot.
- [ ] Implement Supabase Storage bucket adapter slot.
- [ ] Implement Email notification adapter slot.
- [ ] Verify `NullProvider` fallback operations.
