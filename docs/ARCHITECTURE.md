# Current architecture

Abdullah Developer Kit is a static React SPA and a FastAPI REST API backed by PostgreSQL. The browser uses one origin: Vite proxies `/api/*` locally, and either the bundled Nginx image or a Cloudflare Pages Function proxies it in production. The API is the authorization boundary. See [deployment](DEPLOYMENT_STRATEGY.md) and accepted ADRs in `.ai/DECISIONS.md`.

```text
Browser → SPA + same-origin /api/* proxy → FastAPI → PostgreSQL
                                           ├─ auth, users, admin
                                           └─ optional integration adapters
```

## Backend

- `app/api/v1/` defines health/readiness, authentication, self-profile, administration, and limited integration routes. `app/api/deps.py` verifies access tokens, loads current user/roles from the database, and checks role guards.
- `app/core/` owns validated settings, database sessions, security, structured JSON logging, request IDs, client-IP proxy authentication, error handling, rate limiting, and explicit seeding.
- `app/services/` owns auth, user, and admin transactions. `app/models/` and `app/schemas/` hold SQLAlchemy entities and Pydantic contracts. Alembic revisions are in `backend/alembic/versions/`.
- `app/integrations/` defines four typed protocols, inert Null providers and selected Gemini, Telegram, Supabase Storage and SMTP adapters. Only Gemini generation (superadmin) and Telegram webhook have generic routes. Storage and mail are internal service slots. See [integrations](INTEGRATIONS.md).

Requests get a correlation ID, JSON request log, explicit security headers, RFC 7807 error responses and `no-store` on API responses. `/api/v1/health` is process liveness; `/api/v1/ready` pings PostgreSQL. Outside development, docs are off by default, configuration is validated, and the proxy must authenticate its client-IP header when `CLIENT_IP_SOURCE=edge_header`.

## Frontend

`frontend/src/routes/AppRoutes.tsx` defines public home/login/register, authenticated dashboard, and `/admin` overview/users/audit pages. `AuthGuard` and `RoleGuard` improve UX; the backend enforces access. `src/lib/api.ts` uses relative `/api/v1`, HttpOnly cookies, Web Locks for cross-tab refresh ordering, and RFC 7807 error handling. `src/lib/i18n.ts`, locale JSON, and `useDirection` switch Arabic RTL and English LTR at the document root. `src/stores/uiStore.ts` persists only UI preferences.

See [folder structure](FOLDER_STRUCTURE.md) for a repository map and [authentication](AUTH_STRATEGY.md) for the session contract.
