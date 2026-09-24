# Abdullah Developer Kit v1.0.0 — stable reusable baseline

> Updated: 2026-09-24 · Phases 0–8 complete · v1 architecture frozen

## Frozen v1 foundation

- FastAPI backend with validated settings, structured request logs, centralized problem responses, liveness and database readiness.
- PostgreSQL / SQLAlchemy async / Alembic, UUID models, reversible migrations, explicit role seed and guarded test database.
- Argon2id authentication, short-lived access JWTs, rotating opaque refresh tokens, database-backed RBAC, administration and audit logs.
- React / Vite / TypeScript SPA, Arabic/English strings, RTL/LTR direction switching, dashboard and admin UI.
- Pytest/Vitest suites, Ruff/TypeScript/ESLint/build checks, GitHub Actions, hardened Docker Compose production stack, and authenticated same-origin Nginx/Cloudflare proxy topologies.
- Disabled-by-default Gemini, Telegram, Supabase Storage and SMTP extension slots; `.ai/` multi-agent workflow.

The v1 architecture is the stable reusable starter baseline. Bug fixes use patch releases, backward-compatible reusable improvements use minor releases, and breaking architecture changes use major releases. Product-specific functionality belongs in cloned projects.

## Release verification

- Backend: 136 tests against dedicated PostgreSQL, 95% coverage; 91 unit-only tests; Ruff lint/format, pip check, and guarded Alembic drift passed.
- Frontend: 54 tests, 97.91% statements/lines and 90.51% branches; typecheck, lint, build and npm clean-install dry run passed.
- GitHub CI for code commit `14598e9`: backend, frontend and containers workflows all succeeded. The container workflow built the stack, reached healthy services and passed `scripts/smoke-prod.sh`.
- Full npm audit remains an accepted BUG-013 risk (8 findings: 5 moderate, 1 high, 2 critical); production high-severity gate passes with two moderate findings. `pip check` passed; no Python vulnerability scanner is configured.
- No confirmed high/critical application defect was found. No paid provider calls were made. Docker CLI was unavailable locally; container behavior was verified in GitHub Actions.
- The development database is below Alembic head; do not point integration tests there. The dedicated test database passed migration and drift checks.

## Repository and release

GitHub repository is **public** and **template-enabled**. The current tree has no tracked environment secrets, generated output or personal absolute paths. Earlier public Git history may still contain removed personal context; history was not rewritten. Cloudflare/Railway live checks, WAF settings and optional provider calls are deployment-specific.

Package metadata is `1.0.0`. The annotated `v1.0.0` tag is the canonical release identifier. The release-preparation code commit and CI are verified; create the tag and GitHub release as the final publication step.
