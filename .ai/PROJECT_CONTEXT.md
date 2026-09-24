# Project context for coding agents

## Purpose

Abdullah Developer Kit is a reusable full-stack foundation for business systems, SaaS applications, internal tools, academic projects, and AI-enabled products. It ships a FastAPI/SQLAlchemy/PostgreSQL backend, a React/TypeScript frontend with Arabic RTL and English LTR, authentication, database-backed RBAC, an admin UI, production topology, CI, and optional disabled-by-default integrations.

This starter is prepared for public template use, although repository visibility is an owner setting. Clone owners should replace branding and example deployment values and keep personal context in private notes. No local vault, workstation, or prior project is a prerequisite.

## Engineering rules

- Prefer small, understandable changes and follow accepted ADRs in `.ai/DECISIONS.md`.
- Never commit secrets. Use validated environment settings and keep `.env` local.
- Preserve UTF-8 for Arabic content and test both text directions.
- Run relevant backend/frontend checks before declaring a change complete.
- Update `.ai/CURRENT_STATE.md`, `TODO.md`, `BUGS.md`, `CHANGELOG_AI.md`, and `AGENT_HANDOFF.md` for meaningful work.

See `README.md` for setup, `docs/ARCHITECTURE.md` for the current structure, and `docs/DEPLOYMENT_STRATEGY.md` for production.
