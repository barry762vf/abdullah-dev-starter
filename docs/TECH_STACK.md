# Technology choices

The release uses the versions pinned in `backend/requirements*.txt` and `frontend/package-lock.json`; those files, rather than this prose, are authoritative for exact package releases.

| Layer | Choice | Reason |
| --- | --- | --- |
| API | Python 3.11+, FastAPI, Pydantic v2, Uvicorn | Typed HTTP contracts, validation and async request handling. |
| Persistence | PostgreSQL 16, SQLAlchemy 2 async, asyncpg, Alembic | Relational constraints, transactions and explicit migrations. |
| Authentication | Argon2id, PyJWT, opaque refresh tokens | Password hashing and short-lived, rotating sessions. |
| Frontend | React 18, TypeScript, Vite 5, React Router | Static SPA with typed components and simple deployment. |
| UI/data | Tailwind, i18next, TanStack Query, Zustand | Logical-direction styling, translations, server cache and small UI state. |
| Deployment | Docker Compose, Nginx or Cloudflare Pages Function | One browser origin with a private API/database path. |
| Validation | Pytest, Ruff, Vitest, TypeScript, ESLint, GitHub Actions | Local and CI feedback across API, UI, migrations and containers. |

The frontend uses Axios with relative `/api/v1` requests. Supabase is supported as a PostgreSQL host and optional Storage adapter; Supabase Auth is not part of this release. Cloudflare Pages/Railway are documented options, not required hosts. Dependency advisories and the decision to retain current major versions are recorded under BUG-013 and ADR 014.
