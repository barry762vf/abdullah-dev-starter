# Repository map

This is the current layout, not a list of future files. Add project-specific domains only when a clone needs them.

| Path | Purpose |
| --- | --- |
| `backend/app/api/v1/` | Health, auth, self-profile, admin, integration HTTP routes |
| `backend/app/core/` | Settings, database, security, errors, logging, IP trust, rate limits, role seed and preflight |
| `backend/app/models/`, `schemas/`, `services/` | ORM entities, request/response contracts, transactional operations |
| `backend/app/integrations/` | Optional provider protocols, factory, Null and reference adapters |
| `backend/alembic/` | Reversible PostgreSQL migrations |
| `backend/tests/unit/`, `api/`, `integration/` | Fast tests, HTTP boundary tests and dedicated-database tests |
| `frontend/src/components/`, `features/`, `pages/`, `routes/` | React presentation and application routes |
| `frontend/src/lib/`, `stores/`, `locales/`, `test/` | API/i18n, UI state, Arabic/English strings and tests |
| `frontend/functions/` | Cloudflare Pages `/api/*` proxy and proxy tests |
| `frontend/nginx/` | Production Nginx configuration and startup guard |
| `.github/workflows/` | Backend, frontend and production-container CI |
| `deploy/production.env.example` | Self-hosted production configuration template; real values stay ignored |
| `scripts/` | Local database shortcuts, image build and production smoke test |
| `.ai/` | Active engineering state, ADRs, bug registry and handoffs |
| `docs/` | Architecture, security, testing, deployment and customization guidance |

Root `docker-compose.yml` provides local PostgreSQL. `docker-compose.prod.yml` assembles database, one-shot migration, API and web containers. Root `.env.example` is for local development; `.env` and `deploy/production.env` are ignored. See [README](../README.md) for commands.
