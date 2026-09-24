# AI Agent Handoff — Phase 3 complete

> From: Codex (Primary Implementation Engineer)
> Date: 2026-09-24
> Status: Phases 0–3 complete; Phase 4 next.

## Foundation and Git

Phases 0–2 and pre-Phase-3 hardening were verified before this work. Docker Engine 29.8.0 and PostgreSQL 16 were operational. All destructive migration tests and Phase 3 integration data used only the guarded `abdullah_core_test` database; the normal development schema was not changed. Local `main` started clean at `b91412d`, tracking `origin/main` at `https://github.com/barry762vf/abdullah-dev-starter.git`. Phase 3 is a separate commit; see Git log for its final hash and remote state.

## Phase 3 implementation

- Registration normalizes email, validates a 12–128-character password, assigns only the seeded `user` role, and maps duplicate-email races to `409`. Missing baseline role returns `503`. Profiles exclude password hashes.
- Login verifies Argon2id and issues a 15-minute HS256 JWT with only `sub`, `type`, `iat`, and `exp`. Access is carried by HttpOnly cookie or Bearer header. Each protected request loads the account and current roles from PostgreSQL, so disabling an account or removing a role takes effect immediately.
- Refresh uses a 14-day opaque token from `secrets.token_urlsafe(32)` and stores only its SHA-256 digest. A conditional PostgreSQL `UPDATE ... RETURNING` atomically consumes it; successor and audit event commit before cookies are returned. Unknown and expired input return `401` without mass revocation. Known revoked-token reuse revokes remaining sessions for that user. Concurrent use can force re-login; there is no grace window.
- Logout revokes only the presented refresh session and clears both cookies. Cookie mutations require `X-Requested-With: XMLHttpRequest`. SameSite=Lax and explicit CORS origins are retained.
- `get_current_user`, `get_current_active_user`, and `require_role` use explicitly loaded relationships. Current `superadmin` membership satisfies any role guard. No Phase 5 admin-management route was added.
- `python -m app.core.seed` remains roles-only. `python -m app.core.seed --bootstrap-admin` explicitly creates the first superadmin with Argon2id under a transaction advisory lock. It rejects blank/sample credentials, does not reset an existing administrator, and allows removal of `INITIAL_ADMIN_PASSWORD` afterward. The environment template has no administrator default.
- Audit records registration, successful/failed login, refresh, known reuse, logout, and bootstrap without credentials or token digests. Login is limited to 5/minute/IP and registration to 3/hour/IP using the ASGI resolved peer IP in a bounded per-process store. Arbitrary forwarded headers are ignored.

## Files and decisions

Added `backend/app/core/{security,rate_limit}.py`, `backend/app/api/deps.py`, `backend/app/api/v1/{auth,users}.py`, `backend/app/schemas/*`, `backend/app/services/*`, and auth unit/integration tests. Changed seed/config/app/router/dependencies, `.env.example`, README, auth/security/database/deployment docs, and `.ai/` state. ADR 010 records explicit bootstrap, role guard behavior, and scoped rate-limit/proxy behavior. ADR 009 was preserved. No database migration was needed.

## Verification

- `.venv\Scripts\python.exe -m pytest -q --tb=short` from `backend/`: **40 passed**.
- Auth integration coverage: registration/login/profile/logout, missing role, disabled account, current roles, superadmin override, JWT tampering/expiry, rotation/reuse/unknown/expired tokens, bootstrap repeat safety, rate limits, and secret-free logs.
- Independent PostgreSQL connections: concurrent refresh attempts produced exactly one success and one `401`; known reuse revoked the successor.
- `.venv\Scripts\ruff.exe check .`: passed.
- `.venv\Scripts\ruff.exe format --check .`: passed.
- `.venv\Scripts\python.exe -m pip check`: no broken requirements. `uv pip check` also passed before pip was added to the ignored virtual environment.
- Guarded Alembic check on `TEST_DATABASE_URL`: no new upgrade operations.

## Remaining issues and exact next task

BUG-008 is a browser deployment constraint: SameSite=Lax cookies require same-site SPA/API hosts (custom domains or a same-origin proxy). Default Cloudflare Pages and Railway domains are cross-site. The Phase 3 limiter does not enforce limits across workers/instances; production must configure exact trusted proxy IPs and strip untrusted forwarding headers. These are tracked in Phase 4/7 TODOs.

**Exact next task:** Implement Phase 4 frontend shell and bilingual RTL/LTR engine only, first choosing a same-site SPA/API domain or proxy for browser cookie integration. Do not start Phase 5 administration or alter ADR 009 refresh behavior.
