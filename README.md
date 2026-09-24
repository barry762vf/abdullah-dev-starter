# Abdullah Developer Core

A reusable foundation for bilingual web applications, with a FastAPI API, a React and TypeScript client, and PostgreSQL. The repository is being built in [roadmap phases](docs/DEVELOPMENT_ROADMAP.md). Phases 0–2 provide the local database, FastAPI foundation, ORM models, and migrations; the frontend is planned for a later phase.

```text
Browser (React, Vite, Arabic/English)
          |
          v
FastAPI REST API (authentication, roles, services)
          |
          v
PostgreSQL 16 (local Docker or compatible hosted database)
```

**Stack:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · PostgreSQL 16 · React 18 · Vite 5 · TypeScript

## Quickstart

Docker with Compose is required for the local database. From the repository root:

1. Copy the template: `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`). The database credentials are for isolated local development only; administrator bootstrap values are deliberately blank. Set new secrets before real use. Keep `POSTGRES_PASSWORD` and the password in `DATABASE_URL` identical.
2. Start the database: `docker compose up -d --wait db` (or run `.\scripts\dev.ps1` in PowerShell / `bash scripts/dev.sh` on Linux or macOS). Compose binds PostgreSQL to `127.0.0.1:5432` and persists data in the `postgres_data` named volume.
3. Set up Python 3.11+ in `backend/`, install `requirements-dev.txt`, then run `python -m uvicorn app.main:app --reload`. On Windows PowerShell: `py -3.11 -m venv backend/.venv`, `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt`, then from `backend/` run `.venv/Scripts/python.exe -m uvicorn app.main:app --reload`. The frontend is planned for Phase 4.

From `backend/`, run `.venv/Scripts/python.exe -m alembic upgrade head` to apply migrations to `DATABASE_URL`. Run `.venv/Scripts/python.exe -m app.core.seed` explicitly to insert missing baseline roles. It does not create an administrator account; secure account provisioning follows in Phase 3. The API responds at `/api/v1/health` for liveness (`database: not_checked`) and `/api/v1/ready` for a PostgreSQL ping. Interactive docs are at `/docs`.

For database integration tests, set `TEST_DATABASE_URL` to a separate PostgreSQL database whose name ends in `_test`. Create that database once, for example from the repository root with `docker compose exec -T db psql -U postgres -d postgres -c 'CREATE DATABASE abdullah_core_test'`. Then run `.venv/Scripts/python.exe -m pytest -q` from `backend/`. The migration test drops and recreates **only the test database schema**; never point this URL at development or production data. Tests refuse a URL without the `_test` suffix.

Check the container with `docker compose ps db`. Stop it with `docker compose down` (the named volume remains).

## Documentation

- [Project vision](docs/PROJECT_VISION.md)
- [System architecture](docs/ARCHITECTURE.md)
- [Technology choices](docs/TECH_STACK.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Deployment strategy](docs/DEPLOYMENT_STRATEGY.md)

The planning documents live in `docs/`. `.ai/` records current implementation state and engineer handoffs. The source is distributed under the [MIT License](LICENSE).
