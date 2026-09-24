# 📂 Repository & Folder Structure Specification

> **Document:** `FOLDER_STRUCTURE.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Root Repository Layout

The project adopts a clean, decoupled two-tier structure (`backend/` and `frontend/`) with unified root-level orchestration, Docker, environment templates, and multi-agent AI documentation:

```
abdullah-dev-starter/
├── .ai/                       # AI Agent Collaboration Hub & Memory
│   ├── PROJECT_CONTEXT.md     # Core project identity, goals, and rules for agents
│   ├── CURRENT_STATE.md       # Real-time progress, completed items, active blockers
│   ├── ARCHITECTURE.md        # AI quick-reference architectural summary
│   ├── DECISIONS.md           # Permanent Architectural Decision Records (ADRs)
│   ├── TODO.md                # Actionable task backlog across phases
│   ├── BUGS.md                # Active and resolved bug registry with root causes
│   ├── AGENT_HANDOFF.md       # Explicit task handoff instructions for the next agent
│   └── CHANGELOG_AI.md        # Session-by-session execution audit log
├── .github/                   # CI/CD Workflows
│   └── workflows/
│       ├── backend-ci.yml     # Pytest, flake8/ruff, alembic check
│       └── frontend-ci.yml    # ESLint, TypeScript check, Vite build
├── backend/                   # Python FastAPI Backend Service
├── frontend/                  # React + Vite + TypeScript Frontend Service
├── docs/                      # Comprehensive Architecture & Engineering Guides
│   ├── PROJECT_VISION.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── FOLDER_STRUCTURE.md
│   ├── DATABASE_STRATEGY.md
│   ├── AUTH_STRATEGY.md
│   ├── SECURITY_BASELINE.md
│   ├── TESTING_STRATEGY.md
│   ├── DEPLOYMENT_STRATEGY.md
│   ├── DEVELOPMENT_ROADMAP.md
│   └── AI_AGENT_WORKFLOW.md
├── scripts/                   # Cross-Platform Automation Scripts
│   ├── dev.ps1                # Run full stack locally on Windows (FastAPI + Vite + Docker DB)
│   ├── dev.sh                 # Run full stack locally on Linux/macOS
│   ├── migrate.ps1            # Apply Alembic migrations
│   └── seed.ps1              # Seed default admin user & demo fixtures
├── .dockerignore              # Docker build exclusions
├── .env.example               # Master environment variable reference
├── .gitignore                 # Strict Git exclusion rules (keys, .venv, dist)
├── docker-compose.yml         # Local orchestration: PostgreSQL + pgAdmin / backend
├── docker-compose.override.yml.example # Local developer overrides
├── AI_CONTEXT.md              # Bridge note linking repo to Abdullah's Obsidian Second Brain
├── LICENSE                    # MIT License
└── README.md                  # Quickstart, installation commands & overview
```

---

## 2. Backend Directory Breakdown (`backend/`)

```
backend/
├── alembic/                   # Database Migration Management
│   ├── versions/              # Individual migration revision files (e.g., 001_initial_tables.py)
│   ├── env.py                 # Alembic environment runner loading SQLAlchemy metadata
│   └── script.py.mako         # Migration file template
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app initialization, middleware, router mount
│   ├── api/                   # HTTP Presentation & Controller Layer
│   │   ├── __init__.py
│   │   ├── deps.py            # FastAPI dependency injection (get_db, get_current_user, require_role)
│   │   └── v1/                # Version 1 API routes
│   │       ├── __init__.py
│   │       ├── router.py      # Master v1 router aggregating all endpoints
│   │       ├── auth.py        # /auth (login, register, refresh, logout, password reset)
│   │       ├── users.py       # /users (profile, preferences, user self-service)
│   │       ├── admin.py       # /admin (user management, audit logs, system stats)
│   │       └── health.py      # /health (database ping, uptime, memory, version)
│   ├── core/                  # System Foundations & Cross-Cutting Infrastructure
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic Settings class parsing .env
│   │   ├── security.py        # Argon2 / Bcrypt password hashing, JWT sign/verify
│   │   ├── database.py        # Async SQLAlchemy engine, session maker, DeclarativeBase
│   │   ├── logging.py         # Structured JSON logging configuration
│   │   └── exceptions.py      # Custom business exceptions & Starlette handlers
│   ├── models/                # SQLAlchemy 2.0 ORM Entities
│   │   ├── __init__.py
│   │   ├── base.py            # Base entity with id (UUID), created_at, updated_at
│   │   ├── user.py            # User, Role, Permission entities
│   │   ├── audit.py           # AuditLog entity (action, user_id, ip_address, timestamp)
│   │   └── token.py           # RefreshToken entity for revocation tracking
│   ├── schemas/               # Pydantic v2 Request & Response Data Contracts
│   │   ├── __init__.py
│   │   ├── auth.py            # LoginRequest, RegisterRequest, TokenResponse
│   │   ├── user.py            # UserCreate, UserUpdate, UserResponse
│   │   ├── admin.py           # AdminUserUpdate, SystemStatsResponse
│   │   └── common.py          # PaginatedResponse[T], APIResponse[T], ErrorResponse
│   ├── services/              # Pure Business Logic Layer
│   │   ├── __init__.py
│   │   ├── auth_service.py    # Authentication, password verification, token generation
│   │   ├── user_service.py    # User creation, updating, role assignment
│   │   └── audit_service.py   # Security and administrative event logging
│   └── integrations/          # Pluggable Service Adapters (Optional Slots)
│       ├── __init__.py
│       ├── base.py            # Abstract Base Classes (Protocols)
│       ├── ai/                # AI provider slot (Gemini, OpenAI, Mock provider)
│       ├── messenger/         # Chatbot slot (Telegram bot, WhatsApp Cloud API)
│       ├── notifications/     # Notification slot (Email SMTP/Resend, Webhooks)
│       └── storage/           # File storage slot (Supabase Storage, AWS S3, Local)
├── tests/                     # Automated Test Suite
│   ├── conftest.py            # Pytest fixtures (test database, test async client)
│   ├── api/                   # Integration tests for API routes
│   │   ├── test_auth.py
│   │   ├── test_users.py
│   │   └── test_admin.py
│   └── unit/                  # Unit tests for security and services
│       ├── test_security.py
│       └── test_services.py
├── alembic.ini                # Alembic database configuration file
├── Dockerfile                 # Multi-stage production container for FastAPI
├── pyproject.toml             # Python package configuration & dependencies
├── requirements.txt           # Frozen pip dependencies
└── requirements-dev.txt       # Development & testing tools (pytest, ruff, black)
```

---

## 3. Frontend Directory Breakdown (`frontend/`)

```
frontend/
├── public/                    # Static Assets (favicon, manifest, brand icons)
├── src/
│   ├── assets/                # Logos, SVG illustrations, typography assets
│   ├── components/            # Reusable Presentation Components
│   │   ├── ui/                # Base primitives (Button, Input, Card, Modal, Dropdown, Table)
│   │   ├── layout/            # AppShell, Navbar, Sidebar, Footer, DirectionToggle
│   │   └── feedback/          # ToastNotification, LoadingSpinner, EmptyState, ErrorBoundary
│   ├── features/              # Modular Domain Features
│   │   ├── auth/              # Authentication flows
│   │   │   ├── components/    # LoginForm, RegisterForm, PasswordResetModal
│   │   │   ├── hooks/         # useAuth, useLoginMutation
│   │   │   └── AuthGuard.tsx  # Protected route gate checking authentication state
│   │   ├── admin/             # Admin Dashboard feature
│   │   │   ├── components/    # StatsOverview, UserTable, AuditLogViewer
│   │   │   ├── hooks/         # useAdminUsers, useSystemHealth
│   │   │   └── RoleGuard.tsx  # Route gate restricting views by role ('admin', 'manager')
│   │   └── profile/           # User account & settings
│   │       ├── components/    # ProfileForm, ChangePasswordForm
│   │       └── hooks/         # useProfileUpdate
│   ├── hooks/                 # Global utility hooks
│   │   ├── useDirection.ts    # Manages RTL/LTR toggling and document dir
│   │   ├── useTheme.ts        # Dark/Light theme switching
│   │   └── useDebounce.ts     # Search input debouncing
│   ├── lib/                   # External library clients and configurations
│   │   ├── api.ts             # Axios client with baseURL, credentials, and interceptors
│   │   ├── queryClient.ts     # TanStack Query client with caching defaults
│   │   └── i18n.ts            # i18next configuration loading locales
│   ├── locales/               # Bilingual translation files
│   │   ├── ar/
│   │   │   └── translation.json # Arabic translations (RTL)
│   │   └── en/
│   │       └── translation.json # English translations (LTR)
│   ├── pages/                 # Top-level Page Views
│   │   ├── HomePage.tsx       # Landing page / overview
│   │   ├── LoginPage.tsx      # Sign-in screen
│   │   ├── RegisterPage.tsx   # Sign-up screen
│   │   ├── DashboardPage.tsx  # User portal
│   │   ├── AdminPage.tsx      # Administrative control panel
│   │   └── NotFoundPage.tsx   # 404 handler
│   ├── routes/
│   │   └── AppRoutes.tsx      # React Router v6 route configuration
│   ├── stores/                # Client-only micro state stores (Zustand)
│   │   ├── uiStore.ts         # Sidebar collapsed state, language, theme
│   │   └── authStore.ts       # Cached user state for fast client UI rendering
│   ├── types/                 # Shared TypeScript interfaces & types
│   │   ├── api.ts             # Generic API responses, pagination types
│   │   ├── auth.ts            # User, Role, Credentials, AuthState
│   │   └── admin.ts           # AuditLog, SystemMetrics
│   ├── App.tsx                # App root with QueryProvider, I18nProvider, Router
│   ├── main.tsx               # DOM mounting entry point
│   └── index.css              # Tailwind imports, custom font faces, RTL utilities
├── (no API URL env file)       # Browser API paths are relative /api/v1 per ADR 011
├── Dockerfile                 # Multi-stage production Nginx static container
├── index.html                 # Main HTML template with dynamic dir attribute
├── package.json               # Frontend dependencies & npm scripts
├── postcss.config.js          # PostCSS configuration
├── tailwind.config.js         # Tailwind configuration with RTL plugins & brand colors
├── tsconfig.json              # TypeScript strict configuration
└── vite.config.ts             # Vite build settings & dev proxy config
```

---

## 4. Architectural Rules for Future Additions

1. **Adding a New Domain Feature (e.g., `Courses` or `Orders`):**
   - **Backend:**
     - Create entity model in `backend/app/models/order.py`.
     - Create schemas in `backend/app/schemas/order.py`.
     - Create service in `backend/app/services/order_service.py`.
     - Create endpoints in `backend/app/api/v1/orders.py`.
     - Register router in `backend/app/api/v1/router.py`.
     - Generate and apply Alembic migration (`alembic revision --autogenerate -m "add_orders"`).
   - **Frontend:**
     - Create feature folder `frontend/src/features/orders/`.
     - Add route in `frontend/src/routes/AppRoutes.tsx`.
     - Add translations in `frontend/src/locales/ar/` and `frontend/src/locales/en/`.

2. **Adding an Optional Integration (e.g., `WhatsApp Bot`):**
   - Add implementation inside `backend/app/integrations/messenger/whatsapp.py` implementing `BaseMessenger`.
   - Wire credentials through `backend/app/core/config.py`.
   - Core application logic remains untouched.
