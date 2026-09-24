# Independent Review: Phases 0–2 before authentication

> **Reviewer:** Claude Code (Claude Opus 5.5). Independent reviewer; did not implement this project.
> **Date:** 2026-09-24
> **Commit reviewed:** `ddbc9d4` (`feat: implement phase 2 database foundation`) on `main`
> **Scope:** Phase 0 (repository), Phase 1 (backend), Phase 2 (database), and readiness for Phase 3 (authentication). Phase 3 was not implemented.
> **Repository changes during the review:** none. The only new file is this report.

---

## 1. Verdict

The foundation is small, clean and mostly well built. It is **nearly ready** for Phase 3.

Five items should be fixed or decided before authentication work begins (§3). Item 1 is a confirmed bug that Phase 3 will almost certainly trigger. The remaining findings (§4) can be scheduled normally.

---

## 2. How the review was done

- **Documents read:** `AI_CONTEXT.md`, all `.ai/*.md` files, `SECOND_BRAIN_HANDOFF.md`, and the engineering guides in `docs/`.
- **Code read:** every tracked backend file: application, core, models, Alembic environment, migration, seed and tests. Also the Phase 0 files: `.gitignore`, `.dockerignore`, `.env.example`, `docker-compose.yml` and `scripts/`.
- **Commands run:**

| Check | Result |
| :--- | :--- |
| `.venv/Scripts/python.exe -m pytest -q` (from `backend/`) | **19 passed**, including Alembic upgrade → downgrade → re-upgrade and `alembic check` |
| `alembic upgrade head --sql` (offline mode) | Generates SQL cleanly |
| Git history scan for `.env` and secret-like strings | `.env` never tracked; no real secrets found |
| Live database probes (throwaway script, **only** `abdullah_core_test`, every transaction rolled back) | Results below, marked **confirmed** |

When the documentation and the code disagreed, the code was treated as the truth.

---

## 3. Fix or decide before Phase 3

### 3.1 Deleting a user through the ORM crashes when roles or tokens are loaded

- **Severity:** High. **Status:** Confirmed.
- **Location:** `backend/app/models/user.py` lines 27–32.
- **Cause:** `role_assignments` and `refresh_tokens` use `passive_deletes=True` without a `delete` cascade. SQLAlchemy only leaves child rows to the database when they are *not loaded*. When they *are* loaded, it tries to set their foreign key to NULL.
- **Observed:**
  - With `selectinload(User.role_assignments)`: `AssertionError: Dependency rule on column 'users.id' tried to blank-out primary key column 'user_roles.user_id'`.
  - With `selectinload(User.refresh_tokens)`: `IntegrityError ... NotNullViolationError: null value in column "user_id" of relation "refresh_tokens"`.
  - With nothing loaded: the delete succeeds, and the database cascade works.
- **Why it matters now:** Phase 3's `get_current_user` and `require_role` will load roles. Any later "delete user" feature (Phase 5 admin) will then fail.
- **Why the tests miss it:** `tests/integration/test_database.py:106` uses a Core `delete(User)` statement, which bypasses ORM relationship handling.
- **Fix:** set `cascade="all, delete-orphan", passive_deletes=True` on `User.role_assignments` and `User.refresh_tokens`. Add a test that deletes a user through `session.delete()` with those relationships loaded.

### 3.2 Email uniqueness is case-sensitive at the database level

- **Severity:** High (for authentication). **Status:** Confirmed.
- **Location:** `backend/app/models/user.py:17`; migration `ix_users_email`.
- **Observed:** `Case@Example.test` and `case@example.test` were both inserted.
- **Cause:** lowercasing is planned only in the request validation layer (`docs/SECURITY_BASELINE.md` §4). Several paths would bypass it:
  - the Phase 3 admin bootstrap and seed scripts
  - future admin endpoints
  - direct SQL
- **Risk:** duplicate accounts for one person, and ambiguous login lookups.
- **Fix:** enforce the invariant in the database with either of these:
  - `CHECK (email = lower(email))`, keeping the existing unique index; or
  - a unique index on `lower(email)`.

  Doing it now is cheap because no real data exists yet.

### 3.3 Password hashes can reach the logs

- **Severity:** Medium. **Status:** Confirmed.
- **Location:** `backend/app/core/database.py:17` (engine) and `backend/app/core/exceptions.py:53` (`logger.exception`).
- **Observed:** with the engine's default settings, a duplicate-email insert produced an `IntegrityError` whose text contained the `hashed_password` value. With `hide_parameters=True`, the hash was absent.
- **Risk:** a failed registration or a password change would write the Argon2 hash to the JSON logs, where it could be cracked offline. Future refresh-token hashes would leak the same way.
- **Fix:** pass `hide_parameters=True` to `create_async_engine`. The email still appears in PostgreSQL's own `DETAIL:` line; that is acceptable.

### 3.4 The migration round-trip test will fail as soon as a second migration exists

- **Severity:** Medium. **Status:** Certain on the first new revision.
- **Location:** `backend/tests/integration/test_database.py:38–39`.
- **Cause:** the test runs `downgrade "-1"` and then asserts that all model tables are gone. After a `002` revision exists, `-1` only undoes `002`, so the tables remain and the assertion fails.
- **Fix:** use `command.downgrade(migration_config, "base")`.

### 3.5 Two authentication questions need an answer in `AUTH_STRATEGY.md`

- **Severity:** Medium. **Type:** Design decision, not a code defect.

**a) When disabling an account or removing a role takes effect.**
- The spec says access tokens are verified with "Zero DB overhead", and the roadmap puts `roles` in the JWT.
- Consequence: setting `is_active = false` or removing a role takes effect only after the access token expires, up to 15 minutes.
- If that delay is not acceptable, `get_current_active_user` should load the user by primary key on each request and read `is_active` and roles from the database. That is one indexed lookup per request.
- Decide this explicitly before writing the dependencies.

**b) Refresh-token rotation and reuse detection.** The current `refresh_tokens` table is checked against the documented design below.

| Requirement | Supported? | Notes |
| :--- | :--- | :--- |
| Hashed storage (SHA-256) | Yes | `token_hash` is `String(64)`, unique, with a length CHECK. Raw tokens are not stored. |
| Expiration | Yes | `expires_at` is timezone-aware and NOT NULL. |
| Revocation / logout | Yes | `is_revoked`. |
| Rotation without races | Yes | Use a single conditional statement: `UPDATE … SET is_revoked = true WHERE token_hash = :h AND is_revoked = false AND expires_at > now() RETURNING user_id`. Zero rows returned means the token is invalid or was reused. |
| Reuse detection (revoke all on replay) | Yes | A presented token that is already revoked → revoke every token for that `user_id` (indexed). |
| Grace window for concurrent refreshes | **No** | Two browser tabs refreshing at once would look like token reuse and log the user out everywhere. A nullable `revoked_at` timestamp (replacing or alongside `is_revoked`) enables a short grace window and helps investigations. It is cheap to add now. |
| Per-device session management | Not needed | Not part of the documented architecture. Do not add it. |

**Spec corrections needed:**
- **"Tampered" tokens:** `AUTH_STRATEGY.md` (sequence diagram) and `TESTING_STRATEGY.md` say a *tampered* refresh token triggers mass revocation. This can't be implemented: an unknown hash maps to no user. Only a **reused, already-revoked** token can trigger it. Reword both documents.
- **Token generation:** `AUTH_STRATEGY.md` says refresh tokens are generated as `UUIDv4`. Prefer `secrets.token_urlsafe(32)`, which has 256 bits of entropy and no structure.

---

## 4. Lower-priority findings

### 4.1 Database and ORM

| # | Finding | Evidence | Recommendation |
| :--- | :--- | :--- | :--- |
| D1 | Deleting a role cascades and silently removes every assignment of it, including all superadmins. | Confirmed: after the role was deleted, 0 assignments remained. `user.py:57` has `ondelete="CASCADE"`. | Use `ondelete="RESTRICT"` on `user_roles.role_id`. |
| D2 | Reading a relationship that wasn't loaded raises `MissingGreenlet` in async code. | Confirmed. | Set `lazy="raise"` on relationships so the mistake fails the same way every time and tests catch it. |
| D3 | No metadata naming convention. Primary and foreign keys use PostgreSQL's default names (for example `user_roles_role_id_fkey`). | `base.py:11`; confirmed from `pg_constraint`. | Add `MetaData(naming_convention=…)` before more migrations exist. |
| D4 | No index on `user_roles.role_id`. | Schema inspection. | Add one when "users with role X" queries appear (Phase 5). |
| D5 | Deleting a user sets the audit log's actor to NULL, so attribution is lost. | Intentional (`audit.py`, handoff). | Prefer deactivating accounts (`is_active`) over deleting them. If hard delete is needed, snapshot the actor's identifier in `details`. |
| D6 | The application's database user can UPDATE and DELETE audit rows. | Single database role. | Acceptable for a starter; record the decision. Optional later hardening: a separate database role without UPDATE/DELETE on `audit_logs`. |
| D7 | Baseline roles exist only if someone runs `python -m app.core.seed` manually. Phase 3 registration depends on the `user` role. | ADR 008 / `seed.py`. | Registration must fail loudly if the role is missing, and tests and CI must run the seed. Moving roles into a data migration is an alternative. |
| D8 | `updated_at` changes automatically only when updates go through SQLAlchemy (`onupdate`); raw SQL won't touch it. | `base.py:27–33`. | Acceptable; note it for anyone writing raw SQL. |

### 4.2 Configuration, backend and deployment

| # | Finding | Evidence | Recommendation |
| :--- | :--- | :--- | :--- |
| B1 | Production guards don't apply to `staging`. A public staging deployment would accept the sample `SECRET_KEY`, `DEBUG=true` and HTTP origins. | `config.py:76`. | Apply the secret and debug checks to every environment except `development`. |
| B2 | Production requires `INITIAL_ADMIN_PASSWORD` to stay set permanently, even after the admin exists. | `config.py:89–91`. | Validate it only when bootstrapping the first admin (Phase 3). |
| B3 | `DATABASE_STRATEGY.md` says the app works with Supabase's transaction-mode pooler (Supavisor, port 6543). asyncpg's prepared-statement caching breaks under that pooler. | `database.py` sets no `statement_cache_size` or `prepared_statement_cache_size`. | Make these configurable (set both to 0 when using the pooler), or document the direct port (5432) only. |
| B4 | Pool sizes (10 connections + 20 overflow per worker) are hardcoded. | `database.py:19–22`. | Move them into Settings; free-tier databases have low connection limits. |
| B5 | `client_ip` is the proxy's address when the app runs behind a proxy. | `main.py:78`. | Before Phase 3 per-IP rate limiting and audit `ip_address`, run Uvicorn with `--proxy-headers` and a restricted `--forwarded-allow-ips`. |
| B6 | `/docs` and `/openapi.json` are enabled in production. | `main.py:49`. | A per-project decision; add a setting to disable them. |
| B7 | The readiness probe can wait up to 30 seconds if the pool is exhausted (`pool_timeout=30`). | `health.py`, `database.py`. | Low priority; bound it with a timeout if orchestrators probe aggressively. |
| B8 | Every non-404 HTTP error gets the generic title "HTTP Error". | `exceptions.py:79`. | Use the HTTP status phrase instead (RFC 7807 nicety). |
| B9 | `config.py` finds `.env` with `parents[3]`, which assumes the repository's directory layout. | `config.py:11`. | Check this against the Phase 7 container layout. |

### 4.3 Phase 0 and repository

| # | Finding | Recommendation |
| :--- | :--- | :--- |
| R1 | One Windows checkout reported Git dubious ownership. | Verify repository ownership or set a deliberate `safe.directory` entry on that host. |
| R2 | Early context included personal details and absolute local paths. | Public-template guidance was sanitized during v1.0 preparation; historical Git commits may retain old text. |
| R3 | The root `.dockerignore` won't apply if the Phase 7 build context is `backend/`. | Add `backend/.dockerignore` in Phase 7. |
| R4 | The test database must be created by hand. | Optional: a Compose init script that creates `abdullah_core_test`. |

**Solid in Phase 0 and Phase 1:**
- Compose binds PostgreSQL to 127.0.0.1 and has a healthcheck; `.env` is ignored.
- Settings use `SecretStr` and never print secrets; `DATABASE_URL` is validated.
- CORS origins are strictly validated, `*` is rejected, and credentials are allowed only for explicit origins.
- RFC 7807 error responses don't echo submitted values; unhandled errors are sanitized and carry a request ID.
- Logs are JSON and record the path without the query string.
- Liveness (`/health`) and readiness (`/ready`) are separate endpoints.
- The engine is disposed at shutdown, the session factory sets `expire_on_commit=False`, and handlers control commits.

---

## 5. Test gaps to close before authentication

1. ORM delete of a user with `role_assignments` and `refresh_tokens` loaded (§3.1).
2. Case-variant duplicate email rejected by the database (§3.2).
3. `downgrade base` round-trip (§3.4).
4. `get_db` lifecycle: when a handler raises, uncommitted work is rolled back and the session is closed.
5. A disallowed CORS origin receives no `Access-Control-Allow-Origin` header; preflight behavior.
6. One test per production guard. `tests/unit/test_config.py:55` triggers several violations at once, so deleting any single check would still pass.
7. Security headers beyond `nosniff`, including HSTS only in production.
8. An opt-in marker (for example `-m integration`) so unit tests run without PostgreSQL. Today the whole suite fails if `TEST_DATABASE_URL` is unreachable.
9. Declare `python-dotenv` explicitly in `requirements-dev.txt`. `tests/integration/conftest.py` imports it, but it's installed only indirectly through `pydantic-settings`.
10. The audit assertion at `test_database.py:117–118` passes only because the earlier `AuditLog` object was garbage-collected and reloaded from the database. Reload explicitly with `populate_existing` or `session.expire_all()` so the test doesn't depend on that.

---

## 6. Documentation drift

| Document | Says | Code does |
| :--- | :--- | :--- |
| `docs/DATABASE_STRATEGY.md`, `docs/AUTH_STRATEGY.md` | Roles `manager` and `guest` | Seed creates `superadmin`, `admin`, `user` |
| `docs/DATABASE_STRATEGY.md` ERD | `SYSTEM_SETTINGS` table | Not implemented, and not in the Phase 2 roadmap |
| `.ai/ARCHITECTURE.md` | `get_db` in `app/api/deps.py` | In `app/core/database.py` |
| `docs/SECURITY_BASELINE.md` §3 | Security headers in `app/core/security.py`, including `X-XSS-Protection` and HSTS `preload` | Headers are in `main.py`; the set differs (reasonably) |
| `docs/DEPLOYMENT_STRATEGY.md` §5 | `/health` returns `database: connected`; failed migrations at startup stop the container becoming healthy | `/health` returns `not_checked`; there are no startup migrations |
| `docs/AUTH_STRATEGY.md` | Mass revocation on a *tampered* token; refresh token is a UUIDv4 | See §3.5 |

---

## 7. Simplicity

The code is lean and free of needless abstraction. **Do not** add a repository or unit-of-work layer.

The complexity risk is in the documentation: nine `.ai/` state files and eleven design documents already disagree with each other and with the code (§6). Treat the code and the ADRs as the source of truth, and keep the other documents short or clearly marked as aspirational.

---

## 8. Recommended order of work

1. §3.1 ORM cascade fix + test
2. §3.2 email case invariant (migration `002`) + test
3. §3.3 `hide_parameters=True`
4. §3.4 `downgrade base` in the round-trip test
5. §3.5 record the decisions in `AUTH_STRATEGY.md` (DB-checked `is_active`/roles; `revoked_at`; corrected tampered-token wording)
6. Optionally, at the same time: D1 (`RESTRICT`), D2 (`lazy="raise"`), D3 (naming convention), B1 (staging guards)

After steps 1–5, the foundation is ready for Phase 3.

---

## 9. Codex verification and resolution (2026-09-24)

The original review above is preserved. The report arrived as untracked `REVIEW_CLAUDE.md` at the repository root; it was moved to the requested `.ai/REVIEW_CLAUDE.md` location for this hardening checkpoint. All live probes below used `abdullah_core_test` and rolled back their data transactions.

| Finding | Independent status | Evidence and resolution |
| :--- | :--- | :--- |
| §3.1 Loaded ORM user deletion | **CONFIRMED** | Reproduced `AssertionError` for loaded roles and `IntegrityError` for loaded tokens. Added `delete-orphan` ORM cascades and regression test using `session.delete()` and `commit()` with both collections loaded. |
| §3.2 Case-sensitive email | **CONFIRMED** | Reproduced simultaneous inserts of `Case@Example.test` and `case@example.test`. Migration `002_pre_auth_hardening` replaces the plain unique index with unique `lower(email)` and tests case-variant rejection. |
| §3.3 Sensitive SQL parameters/logs | **CONFIRMED**, with a qualification | Reproduced a synthetic password-hash marker in default `IntegrityError` text. `hide_parameters=True` hides SQLAlchemy-bound values, but a second probe found PostgreSQL `DETAIL` still includes a conflicting token hash. The central error handler now logs only database error class; tests cover engine exception text and sanitized logs. |
| §3.4 Single-step migration downgrade | **CONFIRMED** | With revision `002`, `downgrade -1` leaves `001` tables. The round-trip test now exercises `base → head → base → head` and Alembic metadata drift check. |
| §3.5 Authentication behavior | **DESIGN TRADEOFF** | No auth code exists yet. ADR 009 and `docs/AUTH_STRATEGY.md` now require current DB account/role checks, atomic rotation, distinct known-reuse versus unknown input handling, `secrets.token_urlsafe(32)`, and `revoked_at` with no acceptance grace window. |
| D1 Role deletion | **CONFIRMED; adopted** | Existing FK used `CASCADE`; migration `002` changes it to `RESTRICT`, with a loaded-assignment ORM regression test. |
| D2 Async relationship loading | **CONFIRMED; adopted** | Unloaded async relationships could implicitly perform I/O; `lazy="raise"` makes this explicit, with a test. |
| D3 Naming convention | **DESIGN TRADEOFF; deferred** | The metadata had no convention, but adding one after committed revision `001` would require renaming existing constraints without resolving a current defect. Reconsider only when a concrete migration need appears. |
| B1 Staging security guards | **CONFIRMED; adopted** | `config.py` previously returned early for every non-production environment. Staging and production now share security checks, with one test per guard. |
