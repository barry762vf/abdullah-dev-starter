# AI Agent Handoff — Phase 7 production containerization and CI/CD complete

> From: Claude Code
> Date: 2026-09-24
> Status: Phases 0–7 complete and verified. Phase 8 (integration slots) is next; not started.

## 1. Production architecture (ADR 014, `docs/DEPLOYMENT_STRATEGY.md`)

There is one public origin: it serves the SPA and `/api/*`, which is proxied to FastAPI. Cookies stay host-only, HttpOnly, Secure and SameSite=Lax, and browser code uses relative `/api/v1` (ADR 009/011 unchanged).

**Self-hosted** (`docker-compose.prod.yml`):
- Request path: `web` (Nginx, the only published port) → `api` → `db`, with `api` and `db` on an internal network the host can't reach.
- A one-shot `migrate` release job runs before `api` starts.
- Containers have read-only root filesystems, `cap_drop: [ALL]` and `no-new-privileges`.

**Cloudflare Pages + container host:**
- `frontend/functions/api/[[path]].ts` (logic in `functions/_proxy.ts`) serves `/api/*`.
- `frontend/public/_headers` sets the static security headers.

## 2. Images

- **`backend/Dockerfile`:** multi-stage `python:3.11-slim`, uid 10001, code read-only.
  - `ENV_FILE=""`: environment variables only, never a copied `.env`.
  - `python -m app.preflight` runs first, then Uvicorn with `--no-proxy-headers`. Health: `/api/v1/health`.
- **`frontend/Dockerfile`:** `node:22-alpine` build, then `nginx-unprivileged:1.27-alpine` (uid 101, port 8080).
  - `API_UPSTREAM` and `EDGE_PROXY_SECRET` are substituted at start; `10-require-proxy-config.sh` fails closed. Health: `/healthz`.
- Both have `.dockerignore` files; no secrets are in either image.

## 3. CI (`.github/workflows`)

- **`backend-ci`:** pip check, Ruff lint and format, fast unit tests, and the full pytest suite with coverage against a PostgreSQL 16 service.
- **`frontend-ci`:** typecheck, lint, Vitest with coverage, build, and `npm audit --omit=dev --audit-level=high`.
- **`containers`:** builds both images, runs the production stack with throwaway secrets, and runs `scripts/smoke-prod.sh`.

No workflow needs production secrets.

## 4. Proxy behavior

Both proxies:
- preserve the method, path, query, body, status and every `Set-Cookie` header;
- force `Cache-Control: no-store` on API responses;
- strip client-sent `X-Forwarded-For`, `X-Real-IP`, `Forwarded` and `X-Edge-*`.

Nginx also:
- caches hashed assets as immutable; `index.html` gets `no-cache`;
- falls back to `index.html` for SPA routes;
- applies a CSP that allows Google Fonts;
- returns 404 for `/_headers` and problem+json for its 429s.

## 5. Client IP (BUG-009 resolved)

- `CLIENT_IP_SOURCE` is required outside development.
- In `edge_header` mode, the proxy sets `X-Edge-Client-IP` from the peer it observed (Nginx `$remote_addr`, or Cloudflare `CF-Connecting-IP`) plus `X-Edge-Proxy-Secret`.
- `app/core/client_ip.py` refuses requests without the secret with 403 (`/api/v1/health` is exempt), strips the credential, and validates the IP.
- Forwarding headers are never trusted.

## 6. Rate limiting (BUG-010 resolved for the starter)

| Layer | Behaviour |
| :--- | :--- |
| Edge, shared per IP | Nginx `limit_req`: login 5/min, register 1/min with burst 2. Cloudflare WAF rules are documented. |
| PostgreSQL, shared per account | 10 failed logins within 15 min since the last success → 429 before Argon2 (`auth.login_throttled`). |
| In-process, per IP | Kept as local defence in depth. |

## 7. Dependency advisories (BUG-013, accepted with scope)

- All affected packages are at the latest release of their major; the fixes all require major upgrades.
- The production React Router advisories don't apply:
  - navigation targets are fixed paths or on the login allowlist (tests include backslash variants);
  - the `deserializeErrors` advisory is SSR-only.
- The dev-tool advisories affect only local dev or UI servers.
- CI gates the production audit.

## 8. Migrations

- One release step per deploy: `alembic upgrade head && python -m app.core.seed`.
- `alembic/env.py` holds a session advisory lock, so concurrent runs are serialized (tested).
- Migrate through a direct or session-pooled connection.
- Admin bootstrap is a one-off `run -e INITIAL_ADMIN_*` command. The API refuses to start if the password is left in its environment.

## 9. Configuration safeguards

Outside development the API refuses to start unless all of these hold:
- `SECRET_KEY` has at least 64 hex characters;
- `DEBUG=false` and `COOKIE_SECURE=true`;
- origins are HTTPS;
- `CLIENT_IP_SOURCE` is explicit, and in `edge_header` mode `EDGE_PROXY_SECRET` has at least 32 characters;
- `INITIAL_ADMIN_PASSWORD` is absent.

Also:
- Docs are off outside development (`API_DOCS_ENABLED` can override).
- HSTS is sent in staging and production.
- The pool is configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DATABASE_TRANSACTION_POOLER`).
- `/ready` has a 3 s bound.

## 10–11. Verification (exact)

**Backend** (`pytest --cov`):
- **118 passed**, 96% coverage.
- `pytest -m unit`: 73 passed, no database.
- Ruff check passed; format: 53 files formatted.
- `pip check`: no broken requirements. Alembic check: no new upgrade operations.

**Frontend:**
- `npm run test:coverage`: **54 passed**, 97.9% lines, 90.5% branches.
- Typecheck, lint and build passed.
- `npm audit`: 8, all dev tooling. `--omit=dev`: exit 0, with 2 moderate (accepted).

**Live production stack** (local Docker, generated secrets in the git-ignored `deploy/production.env`):
- **Startup and the scripted end-to-end run:**
  - All four services became healthy; `migrate` exited 0.
  - 24/24 scripted checks passed: SPA routes and caching, CSP, proxy health and readiness, register, login with two `Set-Cookie` headers and correct attributes, `/users/me`, refresh rotation with the old token rejected, logout clearing both cookies, and edge 429 as problem+json.
- **Client IP and exposure:**
  - The audit IP was the real peer (172.19.0.1); the spoofed `X-Forwarded-For` and `X-Edge-Client-IP` never appeared.
  - Direct API access without the secret got 403; liveness returned 200; docs 404.
  - Only `web` is published (127.0.0.1:8080); the API and database are unreachable from the host.
- **Containers:**
  - The API runs as uid 10001 and web as uid 101, both on read-only filesystems.
  - The web image refuses a missing or short secret; a misconfigured API container exits 1 without leaking values.
- **Admin bootstrap:**
  - The one-off bootstrap created an Argon2id superadmin.
  - The API refused to start with the bootstrap password present.
  - The superadmin reached the admin stats, users and audit endpoints through the proxy.
- **Browser and final state:**
  - In the browser, the SPA loaded under its CSP with no violations, Cairo and Inter loaded, and the guard redirected to `/login`.
  - After the final rebuild `scripts/smoke-prod.sh` passed, and the stack was then torn down with `down -v`.

**Bugs found and fixed:** BUG-017 (Uvicorn crash-loop), BUG-018 (Nginx fail-open), BUG-019 (frozen-clock test flake).

## 12. Remaining production risks

- The first live Cloudflare Pages + Railway run must follow DEPLOYMENT_STRATEGY §8; the Pages Function is unit-tested but not live-tested.
- Cloudflare WAF rate-limit rules are a dashboard step.
- TLS termination in front of `web` is the operator's choice.
- If Nginx sits behind another load balancer, configure `real_ip`.
- A known email can be throttled by an attacker; edge limits bound this.
- Dev-tool advisories are accepted until the next major-version ADR.
- Owner decision: personal context in the public repository.
- The API's internal network has no internet egress; Phase 8 integrations will need a deliberate egress network.

## 13. Git

A single Phase 7 commit on `main`, pushed normally (see `git log`); CI results are in the GitHub Actions tab. No force-push. `deploy/production.env` is git-ignored and was not committed.

## 15. Next task

**Phase 8 pluggable integration slots only:**
- abstract interfaces in `backend/app/integrations/base.py`, with `NullProvider` fallbacks;
- Gemini, Telegram, Supabase Storage and Email adapter slots enabled by environment variables;
- tests for the factories and fallbacks.

Keep secrets in environment variables, and add outbound network access in `docker-compose.prod.yml` only for the services that need it.
