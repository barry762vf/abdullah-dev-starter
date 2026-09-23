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
- [ ] Scaffold `backend/` directory structure.
- [ ] Create `backend/pyproject.toml` and `backend/requirements.txt`.
- [ ] Implement `backend/app/core/config.py` using Pydantic Settings v2.
- [ ] Implement `backend/app/core/logging.py` for structured JSON logging with request ID tracing.
- [ ] Implement `backend/app/core/exceptions.py` with custom error hierarchy and Starlette handlers.
- [ ] Implement `backend/app/api/v1/health.py` endpoint with uptime and DB status.
- [ ] Implement `backend/app/main.py` assembling middleware, CORS, security headers, and router.
- [ ] Write integration test for `/api/v1/health`.

---

## 🗄️ Phase 2: Database Layer & Declarative Models
- [ ] Implement `backend/app/core/database.py` with async SQLAlchemy 2.0 engine and sessionmaker.
- [ ] Implement `backend/app/models/base.py` with UUID PK and timestamp mixins.
- [ ] Implement `backend/app/models/user.py` (`User`, `Role`, `UserRole`).
- [ ] Implement `backend/app/models/token.py` (`RefreshToken`).
- [ ] Implement `backend/app/models/audit.py` (`AuditLog`).
- [ ] Initialize Alembic with async migration support in `backend/alembic/`.
- [ ] Generate initial migration revision (`001_initial_schema.py`).
- [ ] Implement initial superadmin and roles seeder (`backend/app/core/seed.py`).

---

## 🔐 Phase 3: Authentication & Role-Based Authorization (RBAC)
- [ ] Implement `backend/app/core/security.py` (Argon2id password hashing and JWT encoding/decoding).
- [ ] Create Pydantic v2 auth and user schemas (`backend/app/schemas/auth.py`, `backend/app/schemas/user.py`).
- [ ] Implement `backend/app/services/auth_service.py` (login, register, token rotation, revocation).
- [ ] Implement `backend/app/services/user_service.py` (profile retrieval, user updates).
- [ ] Implement FastAPI dependencies (`backend/app/api/deps.py`: `get_db`, `get_current_user`, `require_role`).
- [ ] Implement API endpoints (`/api/v1/auth/register`, `/login`, `/refresh`, `/logout`).
- [ ] Implement `/api/v1/users/me` profile endpoints.
- [ ] Write pytest integration suite verifying auth, token rotation, and RBAC guards.

---

## 🎨 Phase 4: Frontend Shell, Modern UI & Bilingual Engine (RTL / LTR)
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

---

## 🧪 Phase 6: Automated Testing Suite
- [ ] Finalize backend pytest suite covering edge cases and security boundaries.
- [ ] Implement Vitest component tests for language switching and form inputs.
- [ ] Set up test coverage reporting.

---

## 🚢 Phase 7: Production Containerization & CI/CD
- [ ] Write multi-stage, non-root `backend/Dockerfile`.
- [ ] Write multi-stage Nginx `frontend/Dockerfile`.
- [ ] Configure GitHub Actions workflow `backend-ci.yml`.
- [ ] Configure GitHub Actions workflow `frontend-ci.yml`.
- [ ] Create `docker-compose.prod.yml`.

---

## 🔌 Phase 8: Reusable Extension Slots (Pluggable Modules)
- [ ] Define abstract interfaces (`backend/app/integrations/base.py`).
- [ ] Implement Gemini AI provider adapter slot.
- [ ] Implement Telegram Bot messenger adapter slot.
- [ ] Implement Supabase Storage bucket adapter slot.
- [ ] Implement Email notification adapter slot.
- [ ] Verify `NullProvider` fallback operations.
