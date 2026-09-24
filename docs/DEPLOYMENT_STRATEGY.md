# 🚀 Deployment Strategy & DevOps Architecture

> **Document:** `DEPLOYMENT_STRATEGY.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Cloud Architecture & Hosting Topology

The deployment architecture is optimized for **minimal monthly operating cost ($0 to $5/month)**, high uptime, and global edge delivery:

```mermaid
flowchart LR
    subgraph GitHub["GitHub Repository (barry762vf)"]
        MainBranch["Branch: main"]
        CI["GitHub Actions CI/CD"]
    end

    subgraph EdgeFrontend["Frontend Tier: Cloudflare Pages (Free CDN)"]
        CF_Build["Vite Build: dist/"]
        CF_CDN["Global Edge CDN\n(Unlimited Bandwidth, 0ms cold-start)"]
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
    CF_CDN -->|API HTTPS Requests| FastAPI_App
```

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
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | `development` | `production` |
| `DEBUG` | FastAPI debug mode & detailed error traces | `true` | `false` (Strict) |
| `SECRET_KEY` | Cryptographic JWT signing secret (256-bit min) | Dev placeholder | High-entropy random hex |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/abdullah_core_dev` | Supabase / Railway URI |
| `CORS_ORIGINS` | Comma-separated allowed frontend domains | `http://localhost:5173,http://localhost:3000` | `https://yourdomain.pages.dev` |
| `COOKIE_SECURE` | Force HTTPS for auth cookies | `false` | `true` |

Phase 3 browser sessions use `SameSite=Lax` HttpOnly cookies. The production SPA and API must therefore use the same schemeful site (for example, `app.example.com` and `api.example.com`) or a same-origin reverse proxy. A default `*.pages.dev` frontend calling an unrelated `*.railway.app` API is cross-site, so browser fetches will not send these cookies. Decide the domain/proxy arrangement before Phase 4 browser integration; changing to `SameSite=None` would require a separate security decision and CSRF review.

The Phase 3 authentication rate limiter is per application process. For a reverse-proxy deployment, configure Uvicorn `--forwarded-allow-ips` with only the proxy's actual IP addresses and strip untrusted forwarded headers at that proxy. Configure a shared rate limiter before scaling to multiple workers or instances.
| `INITIAL_ADMIN_EMAIL`| Auto-seeded superadmin account | `admin@devcore.local` | Client owner email |
| `INITIAL_ADMIN_PASSWORD`| Initial superadmin temporary password | `Admin123!Secure` | Strong temporary secret |

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
