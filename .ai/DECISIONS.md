# ⚖️ .ai/DECISIONS.md — Architectural Decision Records (ADRs)

> **Document:** `.ai/DECISIONS.md`  
> **Repository:** Abdullah Developer Core (`abdullah-dev-core`)  
> **Status:** Active Architectural Ledger

This file contains permanent records of all major technical and architectural decisions, the business/technical context, rationale, and explicitly rejected alternatives.

---

## ADR 001: Selected FastAPI over Flask for Backend REST API
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Abdullah has hands-on proficiency in both Flask and FastAPI. The platform requires rapid API construction, robust input validation, enterprise OpenAPI documentation, and async capabilities for webhook handling.
- **Decision:** Use **FastAPI (Python 3.11+)** with Uvicorn.
- **Rationale:**
  - FastAPI provides native Pydantic v2 data validation, eliminating hundreds of lines of error-prone manual input parsing.
  - Generates interactive OpenAPI Swagger documentation (`/docs`) out of the box.
  - Native asynchronous concurrency cleanly handles external webhooks (Telegram/WhatsApp bots).
  - Modern dependency injection simplifies database sessions and RBAC guards.
- **Rejected Alternative:** Flask (Requires multiple disparate, third-party libraries for validation, Swagger, and async; lacks unified type-driven runtime checks).

---

## ADR 002: Selected React (Vite SPA) over Next.js (App Router)
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Deciding frontend technology for client portals, dashboards, and SaaS backoffices.
- **Decision:** Use **React 18 + Vite 5 + TypeScript**.
- **Rationale:**
  - Preserves clean architectural decoupling: Backend is 100% Python/FastAPI; Frontend is a client-side SPA.
  - Generates pure static HTML/JS/CSS assets deployable on Cloudflare Pages or GitHub Pages for **$0/month** with zero Node.js server maintenance.
  - Avoids Next.js App Router hydration bugs, edge runtime quirks, and vendor lock-in with Vercel.
  - Instant HMR during local development on Windows.
- **Rejected Alternative:** Next.js App Router (Introduces complex Node server hosting costs on Railway, dual-backend confusion with Server Actions, and unnecessary SSR complexity for authenticated dashboards).

---

## ADR 003: Selected PostgreSQL & Supabase with SQLAlchemy 2.0 & Alembic
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Need a relational, reliable, production-ready database engine compatible with local development and cloud hosting.
- **Decision:** Use **PostgreSQL 16** with **SQLAlchemy 2.0 (asyncpg)** and **Alembic** migrations.
- **Rationale:**
  - PostgreSQL delivers rock-solid relational integrity, JSONB, UUIDs, and ACID guarantees.
  - Supabase Cloud provides a generous free tier, web-based table editor, and optional expansion into Storage/pgvector.
  - Local Docker Compose uses official `postgres:16-alpine`, ensuring zero cloud vendor lock-in.
  - Alembic guarantees explicit, auditable, reversible database schema evolution.
- **Rejected Alternatives:**
  - Firebase Firestore (Document model requires expensive denormalization; read costs scale unpredictably).
  - SQLite for production (Lacks row-level write concurrency and network connection pooling).

---

## ADR 004: Dual-Token JWT with HTTP-Only Cookies over LocalStorage
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Designing session security to prevent token theft and minimize database query pressure.
- **Decision:** Use **Short-Lived Access Tokens (15 min) + Rotating Refresh Tokens (14 days)** stored in **HTTP-Only, Secure, SameSite=Lax Cookies**.
- **Rationale:**
  - Eliminates Cross-Site Scripting (XSS) token theft because JavaScript cannot read HTTP-only cookies.
  - Access-token signatures are verified in memory; ADR 009 adds a database lookup for current account and role state on protected requests.
  - Refresh tokens are hashed (SHA-256) in the database with rotation on every use; known revoked-token reuse revokes that user's sessions under ADR 009.
  - Also supports `Authorization: Bearer` headers as a fallback for external mobile clients and webhooks.
- **Rejected Alternative:** Storing access tokens in browser `localStorage` (Vulnerable to credential harvesting via malicious third-party scripts or XSS).

---

## ADR 005: Native Tailwind CSS Logical Properties for Bilingual Arabic/English Parity
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** The platform must natively support Arabic (RTL) and English (LTR) with zero layout breaking.
- **Decision:** Utilize **Tailwind CSS with CSS Logical Properties** (`ms-`, `me-`, `ps-`, `pe-`) paired with dynamic `dir="rtl"` / `dir="ltr"` root toggling via `i18next`.
- **Rationale:**
  - Logical margins and paddings automatically invert based on text direction, eliminating duplicate CSS files or messy conditional class cascades.
  - Google Cairo and Inter fonts provide optimal optical balance and readability for Arabic and English respectively.
- **Rejected Alternative:** Separate LTR and RTL stylesheets (Hard to maintain, error-prone, doubles CSS asset weight).

---

## ADR 006: Pluggable Adapter Slots Architecture for Optional Services
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Future clones will need AI, Telegram, WhatsApp, file storage, and email, but bloating the core with inactive SDKs creates maintenance overhead.
- **Decision:** Implement **abstract protocol interfaces** (`app/integrations/`) with a factory pattern and default `NullProvider` implementations.
- **Rationale:**
  - Keeps the core starter clean, lightweight, and fast to clone.
  - New capabilities can be enabled purely by filling `.env` variables without refactoring core services.
- **Rejected Alternative:** Pre-implementing all external SDKs with hard dependencies in the base install (Bloats Docker images, increases attack surface, requires useless configuration keys for projects that don't need them).

---

## ADR 007: Formal Multi-Agent Collaboration Hub (`.ai/`) & Second Brain Bridge
- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Multiple AI coding agents (Codex, Claude Code, Antigravity, DeepSeek) will work on this repository across time.
- **Decision:** Establish a standardized `.ai/` directory containing operational state files and `AI_CONTEXT.md` bridging to Abdullah's Obsidian Second Brain.
- **Rationale:**
  - Prevents context loss between agent handoffs.
  - Enforces atomic state tracking (`CURRENT_STATE.md`, `TODO.md`, `CHANGELOG_AI.md`).
  - Separates transient code details from durable architectural knowledge in Obsidian.

---

## ADR 008: Keep Phase 2 role seeding separate from administrator provisioning

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** The database strategy describes both baseline roles and an initial superadmin. The roadmap places Argon2id password hashing and authentication behavior in Phase 3. Creating a superadmin in Phase 2 without that mechanism would risk an insecure account.
- **Decision:** Phase 2 provides an explicit, idempotent role seed command only. It never creates a user or changes existing role grants. Phase 3 must implement initial superadmin provisioning with Argon2id and the configured `INITIAL_ADMIN_EMAIL`/`INITIAL_ADMIN_PASSWORD` after migration.
- **Consequences:** Fresh Phase 2 installations contain role definitions but no admin login. Database integration tests use a separately named `_test` PostgreSQL database and refuse the normal development URL; migration round-trips may recreate schema only there.

---

## ADR 009: Pre-authentication data integrity and immediate authorization state

- **Date:** 2026-09-24
- **Status:** Accepted; amends the no-database-lookup and broad reuse wording in ADR 004.
- **Context:** Independent review found loaded ORM relationships breaking user deletion, case-sensitive email uniqueness, SQL error details containing hashes, and ambiguity about refresh replay and account disabling.
- **Decision:** Migration `002_pre_auth_hardening` enforces unique `lower(email)`, restricts deletion of assigned roles, and adds nullable `refresh_tokens.revoked_at`. ORM user deletion cascades loaded role assignments and tokens. Protected Phase 3 requests must load current user and roles from PostgreSQL after JWT verification. Refresh rotation must atomically revoke a valid digest and insert its successor in one transaction. Only a known revoked token can identify a user for mass revocation; unknown/tampered or merely expired tokens cannot. Raw refresh tokens will use `secrets.token_urlsafe(32)` and only SHA-256 digests will be stored.
- **Security and operational consequences:** Disabling an account or removing a role takes effect on the next protected request at the cost of an indexed lookup plus role loading. No token-reuse grace window is accepted in the baseline; concurrent refreshes may force re-login. `revoked_at` supports investigation without implying acceptance of replay. SQLAlchemy hides bound parameters and database exceptions are logged by class, because PostgreSQL constraint details can contain a token hash. Staging receives the same key/debug/cookie/CORS/admin-password guards as production.
- **Optional review items:** Adopted restricted role deletion and `lazy="raise"` on async relationships. Deferred a metadata naming convention because already-committed migration `001` uses PostgreSQL-generated names and renaming existing constraints adds migration churn without fixing a current behavior. Database pool tuning, proxy handling, and production deployment work remain later-phase tasks.

---

## ADR 010: Explicit superadmin bootstrap and scoped authentication limits

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Phase 3 needs an initial administrator without leaving a permanent bootstrap secret, and IP-based auth limits cannot safely trust arbitrary forwarded headers.
- **Decision:** Keep `python -m app.core.seed` as roles-only. The `--bootstrap-admin` option runs only when explicitly invoked, rejects blank/sample credentials, serializes first-admin creation with a PostgreSQL transaction advisory lock, and never changes an existing superadmin. Normal application startup no longer requires `INITIAL_ADMIN_PASSWORD`. Access JWTs contain identity and lifetime claims only; `superadmin` satisfies reusable role guards through current database membership. The current 5/minute login and 3/hour registration limits use the ASGI resolved peer IP and a bounded in-process store. Cookie-authenticated mutations require `X-Requested-With: XMLHttpRequest` and use the explicit CORS allowlist.
- **Consequences:** Provisioners remove the bootstrap password after first use. Deployments must configure Uvicorn with exact trusted proxy addresses and strip untrusted forwarding headers. The in-process limiter is effective for a single worker but is not a global limit across workers or instances; a shared limiter is a deployment follow-up. No Phase 5 account-management endpoints or frontend auth behavior are introduced here.

---

## ADR 011: Same-origin browser API and serialized refresh contract

- **Date:** 2026-09-24
- **Status:** Accepted; Phase 4 browser implementation complete, production edge proxy pending
- **Context:** The independent Phase 3 audit confirmed that concurrent browser refreshes trigger ADR 009's known-reuse revocation. It also confirmed that an unrelated Cloudflare Pages host calling a Railway host cannot send the approved SameSite=Lax cookies on API fetches (BUG-008).
- **Decision:** Keep strict backend rotation and SameSite=Lax. The starter's browser-facing production topology is one origin: Cloudflare Pages serves the SPA and routes `/api/*` to FastAPI on Railway through a Pages Function or equivalent same-origin edge proxy. The frontend uses relative `/api/v1` URLs, with a Vite `/api` proxy locally. Phase 4 must use in-tab single-flight plus a same-origin Web Lock to serialize refresh and logout across tabs; under the lock it probes `/users/me` before attempting one refresh. BroadcastChannel carries non-secret auth state signals only. A lost refresh response is never automatically retried. Browsers without Web Locks require re-login rather than unsafe cross-tab automatic refresh.
- **Alternatives considered:** Same-site `app.example.com` and `api.example.com` custom subdomains would keep Lax cookies but require exact credentialed CORS and careful sibling-subdomain cookie handling. `SameSite=None` and server-side replay grace were rejected because they weaken the approved security boundary. A same-origin proxy adds a small edge route but keeps host-only cookies, avoids production browser CORS, and makes the starter's API base URL portable.
- **Consequences:** Phase 4 may implement the frontend contract but must not store tokens in JavaScript storage. Phase 4/7 must implement and test the edge proxy, cookie forwarding, no-cache behavior, and domain configuration before deployment. BUG-008 is resolved as an architecture decision, not as a deployed system.

---

## ADR 012: Explicit runtime mode and bounded password work

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** The Phase 3 audit reproduced event-loop stalls during Argon2 operations and found that a missing `ENVIRONMENT` silently selected `development`, bypassing production guards. Uvicorn's default loopback proxy trust also changes the client IP seen by the app.
- **Decision:** Require `ENVIRONMENT` explicitly; the local template and tests set `development`, while deployment must set and verify `production`. Run request-time password hashing and verification and explicit admin bootstrap hashing in AnyIO worker threads under a dedicated two-operation capacity limiter without reducing Argon2 parameters. Direct local Uvicorn commands use `--no-proxy-headers`; reverse-proxy trust is configured at deployment using exact ingress addresses and header overwriting, with a deployed IP smoke test.
- **Consequences:** Missing mode fails startup. Copying a development `.env` into production remains an operator error, so deployment automation must assert the production mode and security settings. The limiter is per backend process; shared/edge abuse controls and verified proxy topology remain Phase 7 requirements.

---

## ADR 013: Administration authorization and privileged-change invariants

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Phase 5 adds `/api/v1/admin/*`. `docs/AUTH_STRATEGY.md` gives `admin` user management and audit viewing and reserves role modification for `superadmin`. Admin changes must not allow privilege escalation or lock every superadmin out.
- **Decision:** One router-level `require_role(["admin"])` guard protects every admin route; `superadmin` passes it through the existing override. Reads (users, stats, audit logs) are available to both. `PATCH /admin/users/{id}` accepts only `is_active`, `is_verified` and a complete `roles` set (`extra="forbid"`). Rules: nobody modifies their own account through this API; only a superadmin changes roles or modifies accounts that hold `admin` or `superadmin`; role names must already exist and are never created here. Every change takes the transaction-scoped PostgreSQL advisory lock shared with the superadmin bootstrap, re-reads the actor's current active state and roles under that lock, and refuses (409) a change that would leave no active superadmin. Disabling an account also revokes its refresh tokens. Each effective change writes one `admin.user_update` audit row (actor, target id, from/to values) in the same commit; a no-op writes nothing.
- **Consequences:** Two superadmins demoting each other at the same time cannot both succeed (tested with independent connections). An installation without a superadmin can still manage ordinary accounts. The frontend `RoleGuard` and hidden navigation are UX only. Failed (403) admin attempts are not audited yet; add that when a security-monitoring requirement appears.

---

## ADR 014: Production containers, proxy-authenticated client IP, layered rate limiting

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Phase 7 must make the starter deployable without weakening ADR 009/011: one browser origin, host-only Lax cookies, relative `/api/v1`. BUG-009 (client IP trust), BUG-010 (non-shared limits) and BUG-013 (npm advisories) were deployment gates.
- **Decision:**
  - **Topologies:** self-hosted Docker (`web` Nginx serving the SPA and proxying `/api/*` → internal `api` → internal `db`) and Cloudflare Pages with a Pages Function proxy to a container host. Both force `no-store` on API responses and preserve status, body and every `Set-Cookie`.
  - **Client IP:** `CLIENT_IP_SOURCE` is explicit outside development. In `edge_header` mode the proxy overwrites `X-Edge-Client-IP` with the address it observed and authenticates with `EDGE_PROXY_SECRET`; the API refuses unauthenticated requests (liveness exempt) and strips the credential. Uvicorn never trusts forwarding headers. This works on hosts whose ingress IPs are not stable, so no `--forwarded-allow-ips` configuration is needed.
  - **Rate limiting:** shared per-IP limits at the proxy/edge; shared per-account throttle in PostgreSQL via the audit table (no new infrastructure); the in-process limiter stays as local defence in depth.
  - **Migrations:** one release job per deploy (`alembic upgrade head && python -m app.core.seed`) under a PostgreSQL advisory lock; workers never migrate.
  - **Configuration:** production refuses to start with weak/sample secrets, insecure cookies, debug, HTTP origins, an implicit client-IP source, or a leftover `INITIAL_ADMIN_PASSWORD`; the image preflight exits non-zero instead of crash-looping. API docs are off outside development. Pool sizes are configurable, with a transaction-pooler mode for Supabase Supavisor.
  - **BUG-013:** accept the remaining advisories with documented scope instead of major upgrades (see BUGS.md); CI gates the production dependency audit.
- **Consequences:** A proxy secret must be provisioned on both the proxy and the API and rotated together. Cloudflare WAF rules and the first live Cloudflare/Railway smoke test are operational steps outside the repository. A known email can be throttled by repeated failures (bounded by edge limits). `backend` has no outbound internet on the internal compose network; Phase 8 integrations that need egress must add an egress network deliberately.

---

## ADR 015: Optional provider slots and outbound network boundary

- **Date:** 2026-09-24
- **Status:** Accepted
- **Context:** Phase 8 must make Gemini, Telegram, Supabase Storage and email available to cloned projects while preserving ADR 006's lightweight, credential-free default startup. The production API had no outbound network route.
- **Decision:** Four typed protocols have inert Null implementations; validated environment selectors construct the reference adapters only when enabled. Gemini, Telegram and Supabase use their documented HTTPS APIs through the already-used `httpx` dependency, avoiding eager vendor SDK imports. Email uses authenticated SMTP and STARTTLS off the event loop. The only generic AI route is superadmin-only; storage and mail have no public routes. The Telegram webhook validates Telegram's secret header and returns 503 until a cloned app supplies a durable update handler, so updates are retried rather than silently dropped. The API alone joins a deliberate Compose egress network; database and migration services stay internal.
- **Consequences:** Configured providers require outbound access and operator-managed credentials, quotas and data policies. Cloned projects must authorize storage/mail use and install a durable Telegram handler. No live paid provider calls are part of CI. OpenAI and WhatsApp remain protocol extension examples, not enabled products.
