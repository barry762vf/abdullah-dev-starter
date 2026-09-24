# 🚀 Deployment Strategy & DevOps Architecture

> **Document:** `DEPLOYMENT_STRATEGY.md`  
> **Status:** Implemented (Phase 7, ADR 011 and ADR 014)  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Browser topology: one public origin

Every supported deployment exposes **one browser-facing origin** that serves the SPA and proxies `/api/*` to FastAPI. The browser only calls relative `/api/v1/...`, so the HttpOnly, Secure, SameSite=Lax cookies stay first-party and host-only. Never switch to `SameSite=None` or a cross-site API host as a shortcut.

```text
Browser ──HTTPS──> public origin ──/assets, SPA routes──> static files
                               └──/api/*──> proxy ──(X-Edge-Client-IP + X-Edge-Proxy-Secret)──> FastAPI ──> PostgreSQL
```

Two implementations of that proxy ship with the starter:

| Topology | Proxy | Where it is defined | Verified |
| :--- | :--- | :--- | :--- |
| **Self-hosted (VPS, any Docker host)** | Nginx in the `web` image | `docker-compose.prod.yml`, `frontend/Dockerfile`, `frontend/nginx/` | Built and run locally; CI `containers` workflow runs `scripts/smoke-prod.sh` |
| **Cloudflare Pages + Railway (or any container host)** | Pages Function | `frontend/functions/api/[[path]].ts`, `frontend/functions/_proxy.ts`, `frontend/public/_headers` | Unit-tested proxy behavior; the live Cloudflare/Railway route must be smoke-tested per deployment (§8) |

Both proxies preserve method, path, query, body, status codes and every `Set-Cookie` header; force `Cache-Control: no-store` on API responses; remove client-supplied `X-Forwarded-For`, `X-Real-IP`, `Forwarded`, `X-Edge-*`; and add the two headers the API trusts (below). Static assets use content-hashed, immutable caching; `index.html` is revalidated.

---

## 2. Client IP and proxy bypass (BUG-009 resolved)

The API never trusts `X-Forwarded-For`. Uvicorn always runs with `--no-proxy-headers`. `CLIENT_IP_SOURCE` must be set explicitly outside development:

- **`edge_header` (both shipped topologies):** the proxy sends `X-Edge-Client-IP` (the address *it* observed: Nginx `$remote_addr`, or Cloudflare's `CF-Connecting-IP`) and `X-Edge-Proxy-Secret` (the shared `EDGE_PROXY_SECRET`, ≥32 characters). The API refuses every request without the correct secret (403), except `/api/v1/health` for platform liveness checks, so direct access to the API host cannot bypass the proxy or choose its own IP. The secret header is stripped before handlers and logs. An invalid IP value becomes "unknown".
- **`peer`:** the socket peer is the client. Use only when clients connect to Uvicorn directly.

That resolved IP feeds rate limits, request logs and `audit_logs.ip_address`. If Nginx itself sits behind another load balancer, `$remote_addr` is that balancer: configure Nginx `real_ip_header`/`set_real_ip_from` for the balancer's exact range, or rely on edge-level limiting and treat audit IPs as proxy-derived. Do not pretend the app knows the client IP when the ingress cannot guarantee it.

---

## 3. Authentication rate limiting (BUG-010 resolved for the starter)

| Layer | Scope | Mechanism |
| :--- | :--- | :--- |
| **Edge / proxy (shared per IP)** | All API instances | Self-hosted: Nginx `limit_req` — login 5/min/IP (burst 5), register 1/min/IP (burst 2), 429 problem+json. Cloudflare: add WAF rate-limiting rules for `POST /api/v1/auth/login` and `/register` in the dashboard (not expressible in the repo). |
| **Shared per account** | All workers and instances | PostgreSQL: 10 failed logins within 15 minutes since the last success returns 429 before password hashing (`auth.login_throttled` audit). |
| **Application-local per IP** | One worker process | Existing in-memory 5/min login, 3/hour registration. Defence in depth only; not global. |

The per-account throttle is deliberately shared through the audit table (no Redis). Tradeoff: someone who knows an email can keep that account throttled with 10 failures per 15 minutes; per-IP edge limits bound the cost. Add CAPTCHA or a shared store only when a project needs more.

---

## 4. Images

**`backend/Dockerfile`:** multi-stage `python:3.11-slim-bookworm`, virtualenv copied into the runtime stage, code root-owned and read-only, runs as uid 10001, `ENV_FILE=""` (reads real environment variables only, never a copied `.env`). The command runs `python -m app.preflight` first — it validates settings once and exits non-zero (printing field names, never values) instead of letting Uvicorn workers crash-loop — then Uvicorn with `--no-proxy-headers`. Health check: `/api/v1/health`.

**`frontend/Dockerfile`:** `node:22-alpine` build, then `nginxinc/nginx-unprivileged:1.27-alpine` (uid 101, port 8080). `API_UPSTREAM` and `EDGE_PROXY_SECRET` are substituted into the Nginx config at container start; a startup check refuses to run without them or without a writable config directory. Health check: `/healthz`.

Neither image contains secrets (`backend/.dockerignore`, `frontend/.dockerignore`).

---

## 5. Self-hosted production (`docker-compose.prod.yml`)

```powershell
Copy-Item deploy/production.env.example deploy/production.env   # fill every value; git-ignored
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build --wait
bash scripts/smoke-prod.sh deploy/production.env
```

- Services: `db` → `migrate` (one-shot) → `api` → `web`. Only `web` publishes a port (default `127.0.0.1:8080`); `api` and `db` live on an internal network with no route from the host.
- All app containers: read-only root filesystem, `cap_drop: [ALL]`, `no-new-privileges`, tmpfs scratch.
- **TLS:** terminate HTTPS in front of `web` (Caddy, a cloud load balancer, or Cloudflare). `COOKIE_SECURE=true` is enforced, so browsers only send cookies over HTTPS (browsers also accept `http://localhost` for local checks).

### Configuration safeguards

Outside development the API refuses to start unless: `SECRET_KEY` has ≥64 hex characters; `DEBUG=false`; `COOKIE_SECURE=true`; `CORS_ORIGINS` are HTTPS; `CLIENT_IP_SOURCE` is set (and `EDGE_PROXY_SECRET` ≥32 characters for `edge_header`); and `INITIAL_ADMIN_PASSWORD` is **absent**. OpenAPI (`/docs`, `/redoc`, `/openapi.json`) is disabled unless `API_DOCS_ENABLED=true`. HSTS is sent on API responses in staging and production.

---

## 6. Database migrations and bootstrap

- **One release step per deploy**, never at API worker start: `alembic upgrade head && python -m app.core.seed` (compose `migrate` service; Railway "pre-deploy command"). `alembic/env.py` holds a PostgreSQL session advisory lock, so a retried or duplicate release job waits instead of racing.
- Migrate through a **direct or session-pooled** connection (Supabase port 5432). Advisory locks and DDL do not belong on a transaction pooler.
- **First superadmin**, once, with the password only in that one-off command:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml run --rm --no-deps \
  -e INITIAL_ADMIN_EMAIL=owner@example.com -e INITIAL_ADMIN_PASSWORD='<unique 12–128 chars>' \
  migrate python -m app.core.seed --bootstrap-admin
```

Run it before exposing registration. It never promotes an existing account. The API refuses to start if `INITIAL_ADMIN_PASSWORD` is left in its environment.

---

## 7. PostgreSQL / Supabase connections

| Setting | Default | Meaning |
| :--- | :--- | :--- |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 5 | Per process. `(size + overflow) × WEB_CONCURRENCY × instances` must stay below the database connection limit. |
| `DB_POOL_TIMEOUT` | 10 s | Wait for a pooled connection. |
| `DATABASE_TRANSACTION_POOLER` | false | Set `true` for PgBouncer/Supavisor transaction mode (Supabase port 6543): disables asyncpg prepared-statement caches. |

Supabase requires TLS: append `?ssl=require` to the asyncpg `DATABASE_URL`. `/api/v1/ready` pings the database with a 3 s bound; `/api/v1/health` is process liveness only.

---

## 8. Cloudflare Pages + Railway runbook

1. **Railway (API):** deploy `backend/Dockerfile`. Variables: `ENVIRONMENT=production`, `SECRET_KEY`, `DATABASE_URL` (Supabase, `?ssl=require`; transaction pooler flag if port 6543), `CORS_ORIGINS=https://<pages-host>`, `COOKIE_SECURE=true`, `CLIENT_IP_SOURCE=edge_header`, `EDGE_PROXY_SECRET`. Pre-deploy command: `alembic upgrade head && python -m app.core.seed` (session/direct connection URL). Health check path `/api/v1/health`.
2. **Cloudflare Pages (web):** project root `frontend/`, build `npm ci && npm run build`, output `dist`. Environment: `API_ORIGIN=https://<railway-host>` and `EDGE_PROXY_SECRET` (encrypted). `functions/` provides `/api/*`; `public/_headers` sets static security headers.
3. **Edge limits:** Cloudflare WAF rate-limiting rules for login and registration (§3).
4. **Verify live** before announcing: login sets two cookies on the Pages host; `/users/me`, refresh and logout work; a direct request to the Railway host returns 403; an audit row shows the real client IP; API responses are `no-store`.

---

## 9. CI (GitHub Actions)

Phase 8 adds an optional `egress` network to the API container for configured AI, Telegram, Storage and SMTP adapters. The database and migration job stay internal. Leave providers disabled unless their credentials, outbound firewall policy and service quotas have been reviewed. See `docs/INTEGRATIONS.md` for the exact variables and webhook handling contract.

| Workflow | Runs on changes to | Checks |
| :--- | :--- | :--- |
| `backend-ci` | `backend/**` | pip check, Ruff lint and format, fast unit tests, full pytest with coverage against a PostgreSQL 16 service (migration round-trip, drift check, migration lock) |
| `frontend-ci` | `frontend/**` | typecheck, lint, Vitest with coverage (SPA and Pages proxy), build, `npm audit --omit=dev --audit-level=high` |
| `containers` | backend, frontend, compose, smoke script | builds both images, starts the production stack with throwaway secrets, runs `scripts/smoke-prod.sh` |

No workflow needs production secrets. Deployment itself stays manual or platform-driven (Pages/Railway Git integration).
