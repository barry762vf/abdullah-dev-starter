# Abdullah Developer Kit

A reusable full-stack starter for bilingual web applications. It includes a FastAPI API, PostgreSQL, a React/TypeScript SPA, authentication, role-based administration, production containers, CI, and optional integration slots. Clone it as a starting point for your own project; it is not a hosted service.

**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, React 18, Vite 5, TypeScript, Tailwind CSS. The Git tag is the release version; package metadata is aligned to `1.0.0` for this release.

```text
Browser ── same origin ──> SPA + /api/* proxy ──> FastAPI ──> PostgreSQL
                  (Vite locally; Nginx or Pages Function in production)
```

## What's included

- English LTR and Arabic RTL UI, theme preference, dashboard, and administration screens.
- Argon2id passwords, short-lived access JWTs, rotating opaque refresh cookies, current database role checks, and audit logs.
- User registration/login/logout, first-superadmin bootstrap, admin user management, stats, and audit viewer.
- Reversible migrations and idempotent baseline role seed; isolated PostgreSQL integration tests.
- Production Nginx/Compose stack, Cloudflare Pages proxy option, and GitHub Actions checks.
- Disabled-by-default Gemini, Telegram, Supabase Storage, and SMTP adapter slots.

## Start a local development copy

Prerequisites: Git, Docker Engine with Compose, Python 3.11+, Node.js 22+, and npm. Commands below run from the repository root unless noted. The `.env.example` password is **local development only**.

1. Clone and enter the project: `git clone https://github.com/barry762vf/abdullah-dev-starter.git && cd abdullah-dev-starter`.
   GitHub access is required while the source repository remains private; the owner may enable template mode and public visibility separately.
2. Copy `.env.example` to `.env` (`cp .env.example .env`; PowerShell: `Copy-Item .env.example .env`). Keep `POSTGRES_PASSWORD` and the password in `DATABASE_URL` equal. Generate a new `SECRET_KEY` before exposing the API. `.env` is ignored by Git.
3. Start PostgreSQL: `docker compose up -d --wait db`. Confirm it is healthy with `docker compose ps db`.
4. Create a Python virtual environment and install dependencies: `python -m venv backend/.venv`; on Linux/macOS run `backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt`, or on Windows run `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt`.
5. From `backend/`, apply migrations and seed roles: `<venv-python> -m alembic upgrade head` then `<venv-python> -m app.core.seed`, replacing `<venv-python>` with `.venv/bin/python` or `.venv/Scripts/python.exe`.
6. Bootstrap the first superadmin **before opening registration**. Set a unique `INITIAL_ADMIN_EMAIL` and a strong, unique 12–128 character `INITIAL_ADMIN_PASSWORD` in your local shell (or temporarily in `.env`), then from `backend/` run `<venv-python> -m app.core.seed --bootstrap-admin`. Remove the bootstrap password afterward. The command never promotes an existing account; if the email is taken, choose a fresh one.
7. Start the API from `backend/`: `<venv-python> -m uvicorn app.main:app --reload --no-proxy-headers`. Check `http://127.0.0.1:8000/api/v1/health` and `/api/v1/ready`; `/docs` is available in development.
8. In another terminal, from `frontend/` run `npm ci` and `npm run dev`. Open `http://127.0.0.1:5173`, sign in with the bootstrapped account, then open `/dashboard` and `/admin`. Vite proxies relative `/api/*` requests to the API. The UI stores language/theme preferences, while credentials stay in HttpOnly cookies.

The server and frontend are separate processes. Stop the database with `docker compose down`; its named volume remains until explicitly removed. `scripts/dev.ps1` and `scripts/dev.sh` are shortcuts for starting the local database.

## Verify a clone

Create the dedicated test database once: `docker compose exec -T db psql -U postgres -d postgres -c 'CREATE DATABASE abdullah_core_test'`. `TEST_DATABASE_URL` in `.env` must point to this database and end in `_test`; tests refuse a development/production database. From `backend/`, run `<venv-python> -m pytest --cov=app`, `<venv-python> -m pytest -m unit -q`, `<venv-python> -m ruff check .`, `<venv-python> -m ruff format --check .`, `<venv-python> -m pip check`, and `<venv-python> -m alembic check`. The integration migration test recreates **only the guarded test schema**.

From `frontend/`, run `npm run test:coverage`, `npm run typecheck`, `npm run lint`, `npm run build`, `npm audit`, and `npm audit --omit=dev --audit-level=high`. The full audit currently reports accepted advisories; see [BUG-013](.ai/BUGS.md). CI verifies backend, frontend, and production containers on relevant changes.

## Customize and deploy

Start with [the customization guide](docs/CUSTOMIZATION.md) for branding, languages, roles, domains, database, admin account, integrations, and deployment target. The [deployment guide](docs/DEPLOYMENT_STRATEGY.md) covers self-hosted Docker and Cloudflare Pages with a container-hosted API. Production needs HTTPS, new secrets, and a one-time admin bootstrap. Its same-origin proxy keeps cookies first-party; proxy authentication and database-backed RBAC are part of the security model. See [security baseline](docs/SECURITY_BASELINE.md) and [auth contract](docs/AUTH_STRATEGY.md).

Optional providers are off by default and require credentials, egress and project-specific policies when enabled; see [integrations](docs/INTEGRATIONS.md). The first live Cloudflare/Railway deployment and paid-provider behavior still require host-specific verification. See [v1.0.0 release notes](docs/RELEASE_NOTES_v1.0.0.md) for accepted limits.

The roadmap is complete through Phase 8. Current status is in [.ai/CURRENT_STATE.md](.ai/CURRENT_STATE.md); architecture, testing and other engineering guides are in [docs/](docs/). Licensed under [MIT](LICENSE).
