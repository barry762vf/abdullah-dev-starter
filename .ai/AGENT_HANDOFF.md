# AI Agent Handoff — pre-Phase-3 hardening complete

> From: Codex (Primary Implementation Engineer)
> Date: 2026-09-24
> Status: Phases 0–2 complete and hardened; Phase 3 has not started.

## Review verification and resolution

The independent report arrived as untracked root `REVIEW_CLAUDE.md`, while the request named `.ai/REVIEW_CLAUDE.md`. It was moved intact into `.ai/`; Codex's evidence and classifications were appended in §9. Code and live rollback-only probes on `abdullah_core_test` were used to verify the pre-Phase-3 findings.

| Review finding | Codex status | Resolution |
| :--- | :--- | :--- |
| Loaded ORM user deletion | **CONFIRMED** | Reproduced role `AssertionError` and token `IntegrityError`; added User delete-orphan cascades and `session.delete()`/commit test with relationships loaded. |
| Case-sensitive email uniqueness | **CONFIRMED** | Reproduced case-variant inserts; Alembic `002_pre_auth_hardening` adds unique `lower(email)` index and test. Request normalization remains Phase 3. |
| SQL parameter/hash logging | **CONFIRMED**, proposed fix only partial | Default SQLAlchemy exception exposed synthetic password hash. `hide_parameters=True` hides it, but PostgreSQL `DETAIL` still exposes conflicting token hash. Database exceptions now log class only; tests cover both layers. |
| `downgrade -1` round-trip | **CONFIRMED** | With two revisions, one-step downgrade leaves initial tables. Test now covers `base → head → base → head` plus `alembic check`. |
| Authentication design questions | **DESIGN TRADEOFF**, resolved in ADR 009 | Phase 3 must load current `is_active` and roles from DB on protected requests; rotate refresh digests atomically; distinguish known revoked-token reuse from unknown/tampered or expired input; use `secrets.token_urlsafe(32)`; record `revoked_at`. No grace window in baseline. No auth code was added. |

Optional items: D1 role deletion **CONFIRMED/adopted** with `ON DELETE RESTRICT` and a loaded-assignment test. D2 async relationship loading **CONFIRMED/adopted** with `lazy="raise"` and a test. D3 naming convention **DESIGN TRADEOFF/deferred** because committed revision 001 already has PostgreSQL-generated constraint names and changing them adds migration churn without a current defect. B1 staging guard **CONFIRMED/adopted** with one test per security check. Lower-priority review items remain in `.ai/TODO.md` for their phases.

## Changes and migration

- New revision `backend/alembic/versions/002_pre_auth_hardening.py` adds the case-insensitive email invariant, nullable `refresh_tokens.revoked_at`, and restricted role deletion. It refuses to apply when existing case-variant duplicate emails require resolution. Revision 001 was not edited.
- Updated `backend/app/models/{user,token,audit}.py`, `backend/app/core/{database,config,exceptions,logging}.py`, and Alembic's engine configuration. `get_db` remains in `app.core.database`.
- Expanded integration tests for ORM deletion, role restriction, email collisions, `revoked_at`, async relationship access, hidden parameters, and migration lifecycle. Added API test for sanitized database logs and staging guard tests.
- Updated ADR 004/009 and the relevant auth, database, security, testing, deployment, roadmap, and AI architecture documentation. Seeded roles remain `superadmin`, `admin`, and `user`; `guest` is not persisted and `manager` is an optional extension.

## Verification and environment

Docker Desktop engine 29.8.0 and the existing PostgreSQL 16 container were healthy. All destructive migration tests used only `abdullah_core_test`; the normal development schema was not changed. The test URL guard requires the `_test` suffix and differs from the development URL. `.env`, database volume data, and the virtual environment remain ignored.

| Exact check | Result |
| :--- | :--- |
| `.venv/Scripts/python.exe -m pytest -q` from `backend/` | 30 passed |
| `.venv/Scripts/ruff.exe check .` | All checks passed |
| `.venv/Scripts/ruff.exe format --check .` | All backend files formatted |
| `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| Guarded CLI `alembic upgrade head` → `downgrade base` → `upgrade head` | Passed on `abdullah_core_test` |
| Guarded CLI `alembic check` and `alembic current` | No new upgrade operations; `002_pre_auth_hardening (head)` |

The hardening change is a separate commit after `ddbc9d4`, pushed normally to `origin/main`. No force-push was used. Verify the current commit with `git log -1` when continuing.

## Remaining issues and exact next task

No confirmed critical/high or explicit pre-Phase-3 blocker remains. Phase 3 is ready to begin, but **was not started in this run**. The next engineer should implement Phase 3 authentication and RBAC using ADR 009 and `docs/AUTH_STRATEGY.md`: Argon2id and secure initial superadmin provisioning, DB-checked active users/current roles, atomic refresh rotation and known-reuse behavior, auth endpoints, and tests. Also handle Phase 3 TODOs for baseline role presence, permanent bootstrap-secret configuration, and trusted proxy IP before rate limiting. Do not treat JWT role claims as authoritative or mass-revoke on unknown/tampered token input.
