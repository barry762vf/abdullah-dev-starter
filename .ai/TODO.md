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

## 🎨 Phase 4: Frontend Shell, Modern UI & Bilingual Engine (RTL / LTR)
- [ ] Choose same-site SPA/API hostnames or a same-origin proxy before wiring browser cookie auth (BUG-008).
- [ ] Scaffold `frontend/` with React, Vite, and TypeScript.
- [ ] Configure Tailwind CSS with RTL logical properties and Cairo + Inter fonts.
- [ ] Set up `i18next` with Arabic (`locales/ar/translation.json`) and English (`locales/en/translation.json`).
- [ ] Implement `useDirection` hook dynamically switching `dir="rtl"` / `dir="ltr"`.
- [ ] Configure Axios API client with interceptors for credentials and error handling (`src/lib/api.ts`).
- [ ] Configure TanStack Query client (`src/lib/queryClient.ts`).
- [ ] Build layout shell (`AppShell`, `Navbar`, `Sidebar`, `LanguageToggle`, `ThemeToggle`).
- [ ] Build responsive `LoginPage` and `RegisterPage` with form validation.
- [ ] Implement `AuthGuard` protecting dashboard routes.

---

## 🛡️ Phase 5: Admin Dashboard & User Management
- [ ] Implement backend admin endpoints (`/api/v1/admin/users`, `/stats`, `/audit-logs`).
- [ ] Implement frontend `RoleGuard` restricting `/admin` to authorized roles.
- [ ] Build admin dashboard overview with KPI metric cards.
- [ ] Build user management data table (search, pagination, role change, status toggle).
- [ ] Build audit log timeline viewer.
- [ ] Add `user_roles.role_id` index if role-filtered user queries need it; preserve audit attribution when designing any hard-delete flow.

---

## 🧪 Phase 6: Automated Testing Suite
- [ ] Finalize backend pytest suite covering edge cases and security boundaries.
- [ ] Implement Vitest component tests for language switching and form inputs.
- [ ] Set up test coverage reporting.
- [ ] Consider opt-in integration markers, explicit `python-dotenv` test dependency, and coverage of `get_db` exception cleanup, CORS preflight, and security headers.

---

## 🚢 Phase 7: Production Containerization & CI/CD
- [ ] Configure exact trusted proxy IPs, strip untrusted forwarding headers, and add a shared auth rate limiter before multi-worker or multi-instance deployment.
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
