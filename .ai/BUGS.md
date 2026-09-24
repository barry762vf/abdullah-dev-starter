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

### 🐛 BUG-009: Real client IP depends on unverified production proxy trust
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Deployment / authentication audit
- **Symptoms:** Uvicorn's default loopback trust can accept a forged local `X-Forwarded-For`; an untrusted remote proxy collapses every client to the proxy address.
- **Root Cause:** Uvicorn rewrites ASGI `client.host` before FastAPI based on `--proxy-headers` and `--forwarded-allow-ips`; there is no production launch configuration yet.
- **Fix Applied:** Local launch instructions use `--no-proxy-headers`. Deployment docs require exact trusted ingress IPs, header overwrite and a live audit-IP smoke test, or edge limiting when those cannot be guaranteed.
- **Verification:** Independent Uvicorn middleware probe: loopback + `X-Forwarded-For: 6.6.6.6` resolved as `6.6.6.6`; nontrusted `172.18.0.5` remained the peer.
- **Status:** Active Phase 7 deployment gate; no production ingress was configured in this task.

### 🐛 BUG-010: In-process auth limiter can be bypassed by address churn
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Authentication rate limiting
- **Symptoms:** A blocked IP is allowed again after 4,096 other keys; IPv6 address rotation and multi-worker distribution weaken limits.
- **Root Cause:** Bounded least-recently-used per-IP store with no shared or per-account counter.
- **Fix Applied:** Scope and limitations are now explicit in auth/deployment docs and Phase 7 TODO. The current limiter remains a local starter control.
- **Verification:** Independent probe returned 429 after five attempts and then allowed the original IP after key churn.
- **Status:** Active production hardening; does not block Phase 4 local auth integration.

---

## 3. Resolved Bugs

### 🐛 BUG-008: Default split hosting domains do not carry Lax auth cookies
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Browser deployment integration
- **Symptoms:** A browser SPA on a default Cloudflare Pages domain cannot use the Phase 3 HttpOnly `SameSite=Lax` cookies when calling an unrelated Railway domain.
- **Root Cause:** Such hosts are cross-site; browsers omit Lax cookies on cross-site API fetches.
- **Fix Applied:** ADR 011 chooses one browser-facing origin: Pages serves the SPA and proxies `/api/*` to Railway; the frontend uses relative `/api/v1` URLs. SameSite=Lax remains intact.
- **Verification:** Phase 3 cookie behavior and browser SameSite semantics were checked; the proxy implementation and live deployment test remain Phase 4/7 tasks.
- **Status:** Resolved as an architecture decision; not yet deployed.

### 🐛 BUG-011: Missing ENVIRONMENT selected development guards
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Configuration
- **Symptoms:** Unset `ENVIRONMENT` silently accepted a weak key, insecure cookies, debug and HTTP origins.
- **Root Cause:** Settings defaulted to `development`.
- **Fix Applied:** `ENVIRONMENT` is required; local template/tests set `development` explicitly and deployment docs require `production` verification.
- **Verification:** Focused missing-mode validation test and existing staging/production guard tests pass.
- **Status:** Resolved; copying a development `.env` unchanged remains an operational risk.

### 🐛 BUG-012: Argon2 blocked the async event loop
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Authentication concurrency
- **Symptoms:** Password hashing/verification in registration, login and bootstrap could delay unrelated requests.
- **Root Cause:** Synchronous Argon2 calls ran inside async functions.
- **Fix Applied:** Offloaded hashing/verification to AnyIO worker threads under a dedicated two-operation limiter, retaining Argon2 parameters and the unknown-user dummy path.
- **Verification:** Offload thread-identity unit test and live registration/login/bootstrap integration tests pass.
- **Status:** Resolved.

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
