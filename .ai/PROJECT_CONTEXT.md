# 🤖 .ai/PROJECT_CONTEXT.md — Core Context for AI Agents

> **Repository:** Abdullah Developer Core (`abdullah-dev-core`)  
> **Author & Lead Engineer:** Abdullah  
> **Status:** Active Foundation  
> **Target Audience:** All AI Coding Agents (Codex, Claude Code, Antigravity, DeepSeek)

---

## 1. Project Purpose & Long-Term Identity

**Abdullah Developer Core** is the standardized, production-grade, clone-and-launch foundation for Abdullah's future software projects—spanning commercial client systems, educational SaaS platforms, internal automation utilities, and graduation capstone tooling.

Whenever Abdullah starts a new web application, he clones this repository to inherit:
1. Modern, clean Python backend (FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic).
2. Modern, decoupled frontend (React, Vite, TypeScript, Tailwind CSS, TanStack Query).
3. Full Arabic RTL and English LTR bidirectional parity out-of-the-box.
4. Role-based access control (RBAC), user authentication, and admin dashboard.
5. Defensive cybersecurity baseline (Argon2id, HTTP-only secure cookies, rate limiting, structured audit logging).
6. Dockerized PostgreSQL with 100% Supabase Cloud compatibility.
7. Prepared pluggable adapter slots (AI models, Telegram/WhatsApp, Storage, Email).

---

## 2. Engineer Profile & Coding Rules

- **Lead Engineer:** Abdullah (Information & Communication Engineering, U. of Baghdad - Al-Khwarizmi).
- **Core Strengths:** Python (FastAPI, Flask), SQL (PostgreSQL, Supabase), HTML/CSS/JS, Defensive Cybersecurity/SOC, Git, Docker, Railway, Cloudflare Pages.
- **Development Rig:** HP Omen 16 (Windows 11, pwsh).
- **Critical Rules:**
  - **Surgical Changes Only:** Do not rewrite entire files when only modifying a specific function or line range.
  - **Zero Secrets in Git:** Never hardcode secrets. Always use `Settings` and `.env`.
  - **UTF-8 on Windows:** Explicitly preserve UTF-8 encoding for Arabic strings.
  - **Test Before Declaring Complete:** Always run pytest or npm tests before ending your turn.
  - **Update `.ai/` files:** Every session must conclude with updates to `CURRENT_STATE.md`, `TODO.md`, `CHANGELOG_AI.md`, and `AGENT_HANDOFF.md`.

---

## 3. Tech Stack Reference Table

| Layer | Technology | Primary Documentation |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | `docs/TECH_STACK.md` & `docs/ARCHITECTURE.md` |
| **Validation** | Pydantic v2 | `backend/app/schemas/` |
| **ORM & DB** | SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16 | `DATABASE_STRATEGY.md` |
| **Frontend** | React 18, Vite 5, TypeScript | `docs/TECH_STACK.md` & `docs/FOLDER_STRUCTURE.md` |
| **Styling & Bidi** | Tailwind CSS (logical properties: `ms-`, `pe-`), Lucide React | `ARCHITECTURE.md` |
| **State** | TanStack Query v5 (Server), Zustand (Client UI) | `docs/FOLDER_STRUCTURE.md` |
| **Auth** | Argon2id, JWT (Access + Refresh Rotation), HTTP-only cookies | `AUTH_STRATEGY.md` |
| **Container** | Docker & Docker Compose | `docs/DEPLOYMENT_STRATEGY.md` |
