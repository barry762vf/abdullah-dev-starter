# 🐞 .ai/BUGS.md — Bug & Incident Registry

> **Document:** `.ai/BUGS.md`  
> **Status:** Active Registry  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Registry Format

Whenever a bug, regression, or environment fault is identified, record it immediately using this schema:

```markdown
### 🐛 BUG-XXX: [Concise Title]
- **Date Discovered:** YYYY-MM-DD
- **Severity:** [Critical | High | Medium | Low]
- **Component:** [Backend Auth | Database | Frontend Bidi | Docker | CI/CD]
- **Symptoms:** [Exact error message or unexpected UI behavior]
- **Root Cause:** [Technical explanation of the defect]
- **Fix Applied:** [Summary of files modified and logic corrected]
- **Verification:** [Test executed confirming fix]
- **Status:** [Active | In Progress | Resolved]
```

---

## 2. Active Bugs

*No active confirmed pre-Phase-3 blocker after the hardening pass. Lower-priority review items are tracked in `.ai/TODO.md`.*

---

## 3. Resolved Bugs

### 🐛 BUG-003: ORM user deletion failed with loaded children
- **Date Discovered:** 2026-09-24
- **Severity:** High
- **Component:** Database ORM
- **Symptoms:** Loaded role assignments caused `AssertionError`; loaded refresh tokens caused `IntegrityError` during `session.delete(user)`.
- **Root Cause:** `passive_deletes=True` without ORM delete cascade let SQLAlchemy attempt to null required child foreign keys.
- **Fix Applied:** Added `cascade="all, delete-orphan"` to both User collections while retaining database `ON DELETE CASCADE` for unloaded rows.
- **Verification:** Live rollback-only reproduction before fix; regression test deletes a user with both collections loaded via `session.delete()`/`commit()` and verifies children removed and audit row retained.
- **Status:** Resolved

### 🐛 BUG-004: Case-variant duplicate user emails
- **Date Discovered:** 2026-09-24
- **Severity:** High
- **Component:** Database
- **Symptoms:** `Case@Example.test` and `case@example.test` could coexist.
- **Root Cause:** The original unique index compared email with case sensitivity.
- **Fix Applied:** Alembic revision `002_pre_auth_hardening` creates unique index on `lower(email)` and checks for existing collisions before applying it.
- **Verification:** Live reproduction before fix; case-variant duplicate insert now raises `IntegrityError`; Alembic drift check passes.
- **Status:** Resolved

### 🐛 BUG-005: SQL database exceptions could log password or token hashes
- **Date Discovered:** 2026-09-24
- **Severity:** High
- **Component:** Database / logging
- **Symptoms:** Synthetic password hash appeared in default SQLAlchemy exception text; PostgreSQL constraint `DETAIL` could include a synthetic token hash even after hiding SQL parameters.
- **Root Cause:** Engine did not hide parameters, and centralized `logger.exception` logged unsanitized database exception details.
- **Fix Applied:** Enabled `hide_parameters=True` on application and Alembic engines; central handler logs database exception class only and returns the existing generic 500 response.
- **Verification:** Live probes and tests confirm password marker absent from engine exception text and token marker absent from structured application logs and response.
- **Status:** Resolved

### 🐛 BUG-006: Migration round-trip assumed only one revision
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Alembic tests
- **Symptoms:** `downgrade -1` would leave initial tables after a second revision.
- **Root Cause:** Test asserted all tables disappear after a relative one-step downgrade.
- **Fix Applied:** Test now uses `downgrade base`; explicit CLI upgrade, downgrade base, re-upgrade, and `alembic check` passed with two revisions.
- **Status:** Resolved

### 🐛 BUG-007: Staging skipped security configuration guards
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Configuration
- **Symptoms:** Staging accepted weak signing keys, debug mode, insecure cookies/origins, and sample admin password.
- **Root Cause:** Settings returned early unless environment was exactly `production`.
- **Fix Applied:** Security validator now exempts only explicit `development`.
- **Verification:** Separate tests reject each insecure staging value and accept a secure staging configuration.
- **Status:** Resolved

---

### 🐛 BUG-001: Phase 0 Docker runtime validation unavailable
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Docker / local development environment
- **Symptoms:** The first session could not run Compose or PostgreSQL; after Docker Desktop installation, the CLI was outside the session PATH and the engine initially was not running.
- **Root Cause:** Docker Desktop was initially unavailable. The installed per-user CLI and credential helper directory was not on this session's PATH.
- **Fix Applied:** Started Docker Desktop and included its installed `resources/bin` directory on the verification command's PATH. Updated `scripts/dev.ps1` to discover this per-user installation and include its credential helper automatically. No Compose change was required.
- **Verification:** `docker compose config --quiet` passed; `docker compose up -d --wait db` produced a healthy PostgreSQL container; `docker compose ps db` showed `Up (healthy)` on `127.0.0.1:5432`; `pg_isready` accepted connections; SQL returned `abdullah_core_dev|16.15`; `scripts/dev.ps1` started and awaited the healthy database.
- **Status:** Resolved

### 🐛 BUG-002: Bash startup script depended on unavailable `dirname`
- **Date Discovered:** 2026-09-24
- **Severity:** Low
- **Component:** Development script
- **Symptoms:** Git Bash reported `dirname: command not found` before the intended `.env` check.
- **Root Cause:** The first script version used an external utility to locate the repository root.
- **Fix Applied:** Replaced that call with Bash parameter expansion in `scripts/dev.sh`.
- **Verification:** `bash -n scripts/dev.sh` passed; invoking it without `.env` now reports only the expected missing configuration message, and with `.env` reports the expected missing Docker message.
- **Status:** Resolved
