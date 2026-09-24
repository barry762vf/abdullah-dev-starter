# Current repository state — Abdullah Developer Kit

> Updated: 2026-09-24 · Roadmap implementation: **Phases 0–8 complete** · Active work: **v1.0.0 release candidate**

## Shipped foundation

- FastAPI, validated settings, JSON request logging, RFC 7807 errors, process liveness and PostgreSQL readiness.
- PostgreSQL 16 with async SQLAlchemy models, Alembic revisions 001/002, guarded test database and explicit role/admin seed.
- Argon2id authentication, 15-minute access JWTs, rotating 14-day opaque refresh tokens, current database RBAC and audited admin operations.
- React/TypeScript static SPA with English LTR/Arabic RTL, dashboard, admin user/stats/audit screens and same-origin cookie client.
- Nginx/Compose production stack, Cloudflare Pages proxy option, CI, and disabled-by-default Gemini/Telegram/Supabase Storage/SMTP reference slots.

## Release-candidate verification

- Backend: 91 unit tests, 136 total against dedicated PostgreSQL, 95% coverage; Ruff lint/format and pip check passed. Alembic drift passed against the guarded test database. The standalone check against the unmigrated development database reported “Target database is not up to date”; development data was not modified.
- Frontend: 54 Vitest tests, 97.91% statements/lines and 90.51% branches; TypeScript, ESLint and production build passed.
- Dependency audit: full npm audit reports 8 accepted findings (5 moderate, 1 high, 2 critical) under BUG-013/ADR 014; production audit reports 2 moderate, exits 0 at the high gate. Python dependency integrity passed; no Python vulnerability scanner is configured.
- Docker CLI is unavailable in this task environment. GitHub workflows for release commit `14598e9` passed: [backend-ci](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155712) ran 136 tests at 95% coverage, [frontend-ci](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155774) passed, and [containers](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155862) built healthy services and passed `scripts/smoke-prod.sh`.
- Read-only release security review found no confirmed high/critical application defect. No paid-provider calls were made.

## Release preparation

The README, architecture/security/auth/database guides, customization guide and release notes now describe the shipped kit. Tracked absolute machine paths and private profile details were removed from the current tree while `.ai/` remains. Earlier Git history can still contain those strings; it was not rewritten. GitHub currently reports the repository as **PRIVATE**, default branch `main`, and template mode off. Backend/frontend metadata is `1.0.0`; the eventual `v1.0.0` Git tag is the canonical release identifier. No tag has been created yet.

## Remaining work

1. Release-preparation code commit `14598e9` and all triggered workflows are green. Review release notes, then create/publish annotated `v1.0.0` when the owner chooses to release.
2. For each real deployment, complete the Cloudflare/Railway or chosen-host smoke, TLS, proxy-IP and edge rate-limit checks in `docs/DEPLOYMENT_STRATEGY.md`.
3. Enable optional providers only with project credentials, quotas, data policy and live tests; install a durable Telegram handler first.
4. Reassess BUG-013 and older direct pins as a planned dependency update, without an untested major upgrade in this release.
