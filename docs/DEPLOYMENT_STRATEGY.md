# 🚀 Deployment Strategy & DevOps Architecture

> **Document:** `DEPLOYMENT_STRATEGY.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Cloud Architecture & Hosting Topology

The baseline browser deployment uses **one origin** for the SPA and API. Cloudflare Pages serves the Vite build and routes only `/api/*` through a Pages Function (or equivalent edge proxy) to the FastAPI service on Railway. The browser calls relative `/api/v1/...` URLs. This is an architecture choice, not a deployed proxy yet; Phase 4/7 must implement and verify it.

```mermaid
flowchart LR
    subgraph GitHub["GitHub Repository (barry762vf)"]
        MainBranch["Branch: main"]
        CI["GitHub Actions CI/CD"]
    end

    subgraph EdgeFrontend["Frontend Tier: Cloudflare Pages (Free CDN)"]
        CF_Build["Vite Build: dist/"]
        CF_CDN["Global Edge CDN\n(Unlimited Bandwidth, 0ms cold-start)"]
        API_Proxy["Same-origin /api/* proxy\n(Pages Function)"]
    end

    subgraph CloudBackend["Backend Tier: Railway (PaaS Container)"]
        FastAPI_App["FastAPI Service (Docker)\nUvicorn ASGI Workers"]
    end

    subgraph DataTier["Database Tier: Supabase Cloud (Free Tier)"]
        Supabase_PG[(PostgreSQL 16\nManaged Backups & Supavisor Pool)]
        Supabase_Storage[(Supabase Storage Bucket\nMedia & File Uploads)]
    end

    MainBranch --> CI
    CI -->|Push Trigger| CF_Build
    CF_Build --> CF_CDN
    CI -->|Deploy Trigger| FastAPI_App
    FastAPI_App -->|Async SQLAlchemy (Port 6543 / 5432)| Supabase_PG
    FastAPI_App -->|S3 REST API / Signed URLs| Supabase_Storage
    CF_CDN -->|Relative /api/v1 requests| API_Proxy
    API_Proxy -->|HTTPS upstream| FastAPI_App
```

### Browser topology decision

| Option | Cookies and CORS | Delivery tradeoff |
| :--- | :--- | :--- |
| **Recommended: same-origin `/api/*` proxy** | Host-only, Secure, SameSite=Lax cookies work on the one browser-facing host; normal browser calls need no CORS. | Cloudflare Pages can route `/api/*` with a Function while static assets remain on Pages. The proxy must preserve path, method, body and separate `Set-Cookie` headers, disable API caching, and strip/overwrite client-supplied forwarding headers. Implement and test it in Phase 4/7. |
| Same-site `app.example.com` + `api.example.com` | Lax cookies work only with an explicit `withCredentials`/`credentials: include` client and exact HTTPS CORS allowlist. | Both Pages and Railway support custom domains, but clones need two DNS names and must protect against untrusted sibling subdomains setting parent-domain cookies. |

The starter uses a relative `/api/v1` base URL. During local development, a Vite dev proxy forwards `/api/*` to `localhost:8000`, preserving the production path and same-origin browser behavior. Direct `localhost:5173` → `localhost:8000` is also same-site but requires CORS; it is not the starter baseline. An unrelated `*.pages.dev` SPA calling `*.up.railway.app` directly is cross-site and cannot send Lax cookies on fetch even with credentials enabled. A Pages Function on the **same Pages hostname** avoids that problem. Do not switch to `SameSite=None` as a shortcut. [Cloudflare Pages Function routing](https://developers.cloudflare.com/pages/functions/routing/) and [Railway domains](https://docs.railway.com/networking/domains/working-with-domains/) describe the platform mechanisms; their implementation and current limits must be rechecked at deployment time.

---

## 2. Multi-Stage Docker Build Strategies

### Backend Multi-Stage Dockerfile (`backend/Dockerfile`):
- **Stage 1 (Builder):** Installs compiler tools, wheels, and dependencies into a virtual environment.
- **Stage 2 (Runtime):** Copies only the virtual environment into `python:3.11-slim`.
- **Security:** Creates a non-root system user (`appuser:10001`) to run the Uvicorn process.
- **Healthcheck:** Built-in `HEALTHCHECK` pinging `http://localhost:8000/api/v1/health`.

### Frontend Multi-Stage Dockerfile (`frontend/Dockerfile` - for self-hosted / VPS use):
- **Stage 1 (Node Build):** Installs npm packages and compiles static assets via `npm run build`.
- **Stage 2 (Nginx Alpine):** Copies `dist/` into lightweight `nginx:alpine` with gzip compression and cache headers.
*(Note: When deploying to Cloudflare Pages, Cloudflare directly builds from Git, making the container optional for production).*

---

## 3. Environment Configuration & Profiles

| Environment Variable | Description | Development Default | Production Target |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Required runtime mode (`development`, `staging`, `production`) | Explicit `development` in `.env.example` | Explicit `production` |
| `DEBUG` | FastAPI debug mode & detailed error traces | `true` | `false` (Strict) |
| `SECRET_KEY` | Cryptographic JWT signing secret (256-bit min) | Dev placeholder | High-entropy random hex |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/abdullah_core_dev` | Supabase / Railway URI |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://localhost:3000` | Exact SPA origin, e.g. `https://app.example.com`; same-origin browser calls do not invoke CORS |
| `COOKIE_SECURE` | Force HTTPS for auth cookies | `false` | `true` |
| `INITIAL_ADMIN_EMAIL` | Explicit first-superadmin bootstrap only | Empty | Temporary owner email; remove after bootstrap |
| `INITIAL_ADMIN_PASSWORD` | Explicit first-superadmin bootstrap only | Empty | Unique strong temporary secret; remove after bootstrap |

Set `ENVIRONMENT=production` explicitly in the deployed service. A missing value now fails startup, but copying the development template unchanged still selects development; deployment automation must set and verify the production value along with a strong secret, `DEBUG=false`, HTTPS origins, and `COOKIE_SECURE=true`. Run the bootstrap command before exposing registration; never promote a pre-registered account if the intended bootstrap email is already taken.

### Trusted client IP and rate-limit deployment gate

Uvicorn 0.34.2 enables proxy headers by default and trusts `127.0.0.1`, so even direct loopback requests can alter `request.client.host` with `X-Forwarded-For`. Direct local startup therefore uses `--no-proxy-headers`. Behind a proxy, start Uvicorn with `--proxy-headers --forwarded-allow-ips=<exact trusted ingress IPs>` **only after** the ingress overwrites untrusted `X-Forwarded-For` and `X-Forwarded-Proto`, and blocks direct access that bypasses it. Do not set `--forwarded-allow-ips='*'` on a publicly reachable service. If the Pages/Railway path cannot provide stable trusted ingress addresses, run with `--no-proxy-headers`, treat the recorded IP as the proxy address, and enforce abuse controls at the edge instead of claiming the per-IP app limiter is client-accurate. Phase 7 must smoke-test the IP written in `audit_logs` through the actual deployed path.

The current limiter is bounded and per process. Key churn can evict a live bucket; IPv6 address rotation and distributed attempts are not fully constrained; there is no per-account throttle. A shared or edge limiter is required before claiming production enforcement, especially with multiple workers. These are deployment follow-ups and do not block the Phase 4 local browser client.

---

## 4. GitHub Actions CI/CD Pipeline

The repository provides two separate, highly optimized GitHub Actions workflows:

1. **`backend-ci.yml`:**
   - Triggers on push or pull request to `main` affecting `backend/**`.
   - Runs `ruff` for linting and code formatting checks.
   - Spins up a temporary PostgreSQL service container.
   - Runs `alembic upgrade head` to verify migration integrity.
   - Executes `pytest` with coverage report.
2. **`frontend-ci.yml`:**
   - Triggers on push or pull request affecting `frontend/**`.
   - Runs TypeScript compilation check (`tsc --noEmit`).
   - Runs ESLint.
   - Runs `npm run build` to ensure static production bundle passes without bundle errors.

---

## 5. Zero-Downtime Deployment & Health Monitoring

- **Liveness Endpoint (`/api/v1/health`):**
  Returns application status without querying PostgreSQL:
  ```json
  {
    "status": "healthy",
    "environment": "production",
    "database": "not_checked",
    "uptime_seconds": 34821.0
  }
  ```
- **Deployment Rollouts:**
  - `/api/v1/ready` performs a database ping and returns 503 when PostgreSQL is unavailable; configure dependency-aware deployment probes to use it.
  - Migrations are an explicit deployment step. The current application does not run them automatically at startup.
