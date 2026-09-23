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
  - Access tokens are cryptographically verified in memory without database hits.
  - Refresh tokens are hashed (SHA-256) in the database with rotation on every use; token reuse detection immediately revokes compromised sessions.
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
