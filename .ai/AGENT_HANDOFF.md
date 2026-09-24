# AI Agent Handoff — Phase 6 automated regression suite complete

> From: Claude Code
> Date: 2026-09-24
> Status: Phases 0–6 complete and verified. Phase 7 (containerization and CI/CD) is next; no Phase 7/8 work was started.

## 1. Backend tests added (50 → 99)

- **`tests/unit/test_security.py`:** rejects JWTs with `alg:none`, HS512 (same key), HS256 with a different key, each missing claim (`sub`/`type`/`iat`/`exp`), a non-UUID or integer `sub`, and a future `iat`. Extra `roles` claims are ignored.
- **`tests/unit/test_db_guard.py` + `tests/db_guard.py`:** the `_test` database guard refuses the wrong driver, missing names, non-`_test` names, and the development database even when spelled differently (host, port and database are compared, `127.0.0.1` equals `localhost`).
- **`tests/unit/test_rate_limit.py`:** the login window resets after 60 s; registration is limited to 3 per hour; memory stays bounded (the BUG-010 limitation is documented).
- **`tests/api/test_cors_and_headers.py`:**
  - An allowed-origin preflight gets credentials and the `X-Requested-With` header.
  - Other origins (lookalike ports, `null`, plain HTTP) get no origin grant.
  - Security headers are present on success and error responses; HSTS appears only in production; the relaxed CSP applies to `/docs` only.
- **`tests/integration/test_auth_regressions.py`:**
  - Route inventory: every non-public `/api` route depends on `get_current_active_user`.
  - A deleted user's valid token is rejected on both transports.
  - Cookie `Path`, `Max-Age`, `HttpOnly`, `SameSite`, host-only and `Secure` (tested on and off) at login; clearing at logout.
  - A disabled user's refresh revokes every session.
  - A failure after the conditional refresh UPDATE rolls back: the old token stays valid, no cookie is set, and a retry succeeds.
  - No secrets in logs on the reuse and bootstrap paths.
  - Proven-concurrent refresh and bootstrap races: the second transaction is observed blocked in `pg_stat_activity`.
  - The bootstrap never promotes an existing account and refuses a missing role.
  - A non-Bearer `Authorization` header never falls back to the cookie.
  - Names with bidi overrides, zero-width or control characters are rejected.
  - `get_db` rolls back and releases its connection when a handler raises.
- **`tests/integration/test_admin.py` (+2):**
  - A disabled admin gets 401 immediately, even with a valid token.
  - Users, stats and audit responses contain no raw tokens, digests or password hashes after real login and refresh activity.
  - Invalid role names are rejected, and a forced last-superadmin 409 rolls back fully with no audit row.

## 2. Frontend tests added (32 → 45), in `src/test/regression.test.tsx`

- A cross-tab `signed-out` broadcast clears the tab and leaves protected pages; malformed or foreign messages are ignored.
- Navbar logout: success, and failure (session kept, alert shown).
- After login, the app returns to an allowlisted `/admin`; an off-list `from` falls back to `/dashboard`.
- The theme toggle persists only its preference.
- Statistics error with a working retry; RoleGuard error state (not "Access denied").
- Audit empty state and users error state; pagination requests page 2 (mirrored labels).
- Enabling an account needs no confirmation, and a 404 shows its message.
- Tab stays inside the confirmation dialog; Escape restores focus.

## 3. Security gaps closed

The Phase 3 TODO regression list is fully covered:
- JWT forgery;
- stale role claims;
- cookies;
- bootstrap race;
- disabled-user refresh;
- route inventory;
- rollback after the refresh UPDATE;
- log redaction;
- a true refresh race.

Also covered:
- `get_db` cleanup;
- CORS and headers;
- disabled admins and secret-free admin responses;
- name spoofing.

## 4. Bugs

**No application defect found.** Two test-harness issues were fixed:
- The bootstrap race proof now commits roles first; otherwise the second transaction waited on the role insert rather than the advisory lock.
- One CORS assertion was stricter than the property: Starlette sends `Allow-Credentials` without `Allow-Origin`, and browsers ignore it.

BUG-013 is annotated: adding `@vitest/coverage-v8` (dev only) raises the full audit to 8 entries by inheriting the existing Vitest advisory.

## 5–11. Results (exact)

**Backend** (from `backend/`):

| Check | Result |
| :--- | :--- |
| `pytest -q --cov` | **99 passed**; total coverage **97%** (851 statements, 140 branches) |
| `pytest -m unit` | 56 passed in about 1 s, no PostgreSQL needed |
| `ruff check .` | Passed |
| `ruff format --check .` | 49 files formatted |
| `pip check` | No broken requirements |
| Alembic `check` on the test database | No new upgrade operations |

The test database is left empty.

**Frontend** (from `frontend/`):

| Check | Result |
| :--- | :--- |
| `npm run test:coverage` | **45 passed**; statements/lines **98.36%**, branches **90.2%**, functions **91.66%** |
| `npm run typecheck`, `npm run lint`, `npm run build` | Passed |
| `npm audit --audit-level=high` | 8 (5 moderate, 1 high, 2 critical; dev toolchain, BUG-013) |
| `npm audit --omit=dev` | Exit 0, with 2 moderate (React Router) |

**Configuration:**
- Coverage is reported, not enforced (`pyproject.toml [tool.coverage]` with `concurrency = ["greenlet", "thread"]`; `vite.config.ts` `test.coverage`).
- `coverage/` and `.coverage` are git-ignored.

## 12. Remaining test gaps (low value)

- The seed CLI entry point.
- Race-only `IntegrityError` branches in bootstrap and registration.
- The empty-role-list guard construction.
- A real multi-tab Web Locks test needs a real browser; that fits Phase 7 end-to-end work.

## 13. Git

A separate Phase 6 commit on `main`, pushed normally (see `git log`). No force-push.

## 15. Next task

**Phase 7 production containerization and CI/CD**:
- a non-root backend Dockerfile and an Nginx frontend Dockerfile;
- `docker-compose.prod.yml`;
- GitHub Actions running these suites (`pytest` with a PostgreSQL service and `TEST_DATABASE_URL`, `npm run test:coverage`);
- the Pages `/api/*` proxy;
- resolving BUG-009, BUG-010 and BUG-013 before any public deployment.
