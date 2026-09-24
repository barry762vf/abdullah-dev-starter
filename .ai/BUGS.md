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

*No active application bugs. BUG-009, BUG-010 and BUG-013 were resolved or formally accepted in Phase 7 (see ADR 014). Phase 8 provider network behavior is mocked; no paid-service credentials were used. The first live provider and Cloudflare/Railway checks remain deployment tasks.*

## 3. Resolved Bugs

### 🐛 BUG-017: Misconfigured API container stayed "up" while workers crash-looped
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Backend container
- **Symptoms:** With missing production settings, `uvicorn --workers 2` kept its parent process running (container "Up (unhealthy)") while each worker died on the Settings ValidationError.
- **Root Cause:** Uvicorn's multi-process supervisor does not exit when workers fail at import.
- **Fix Applied:** The image runs `python -m app.preflight` first; it validates settings and startup guards once and exits 1, printing field names and messages without input values.
- **Verification:** Container exits 1 with `startup refused: secret_key: Field required`; unit tests prove failure and that a DATABASE_URL password is never printed.
- **Status:** Resolved

### 🐛 BUG-018: Nginx could start without the proxy configuration
- **Date Discovered:** 2026-09-24
- **Severity:** Medium (found before release)
- **Component:** Web container
- **Symptoms:** On a read-only filesystem the template step logged "conf.d is not writable" and Nginx started with no server block.
- **Root Cause:** The nginx entrypoint treats template failures as non-fatal; tmpfs mounts were root-owned.
- **Fix Applied:** tmpfs mounts owned by uid 101; the image's `10-require-proxy-config.sh` fails closed on a non-writable config directory, missing `API_UPSTREAM`, or an `EDGE_PROXY_SECRET` shorter than 32 characters.
- **Verification:** Container refuses to start without or with a short secret; stack healthy and smoke-tested with correct configuration.
- **Status:** Resolved

### 🐛 BUG-019: Tests compared Python time with a frozen transaction clock
- **Date Discovered:** 2026-09-24
- **Severity:** Low (test-only flake)
- **Component:** Backend tests
- **Symptoms:** `test_expired_refresh_and_unknown_logout` failed once under load.
- **Root Cause:** Inside the rollback fixture PostgreSQL `now()` is the outer transaction's start; an "expired 1 s ago" Python timestamp could still be later than it on a slow run. The new login-throttle test hit the same effect.
- **Fix Applied:** One-day expiry margin; time-window tests use committed rows and real transactions.
- **Verification:** Full backend suite 118 passed.
- **Status:** Resolved

### 🐛 BUG-009: Real client IP depends on unverified production proxy trust
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Deployment / authentication audit
- **Symptoms:** Uvicorn's default loopback trust can accept a forged local `X-Forwarded-For`; an untrusted remote proxy collapses every client to the proxy address.
- **Root Cause:** Uvicorn rewrites ASGI `client.host` before FastAPI based on `--proxy-headers` and `--forwarded-allow-ips`; there is no production launch configuration yet.
- **Fix Applied:** Local launch instructions use `--no-proxy-headers`. Deployment docs require exact trusted ingress IPs, header overwrite and a live audit-IP smoke test, or edge limiting when those cannot be guaranteed.
- **Verification:** Independent Uvicorn middleware probe: loopback + `X-Forwarded-For: 6.6.6.6` resolved as `6.6.6.6`; nontrusted `172.18.0.5` remained the peer.
- **Phase 7 resolution:** `CLIENT_IP_SOURCE` is required outside development. Both shipped proxies (Nginx image, Cloudflare Pages Function) overwrite `X-Edge-Client-IP` with the observed peer / `CF-Connecting-IP` and authenticate with `EDGE_PROXY_SECRET`; the API refuses requests without it (403, liveness exempt) and strips the credential. Uvicorn always runs `--no-proxy-headers`. Verified live: audit IP = real peer while `X-Forwarded-For`/`X-Edge-Client-IP` spoofing was ignored; direct API access refused.
- **Status:** Resolved (Phase 7)

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
- **Phase 7 resolution:** shared per-IP limits at the proxy/edge (Nginx `limit_req`; Cloudflare WAF rules documented) and a PostgreSQL per-account throttle shared by every worker/instance (10 failures / 15 min since last success → 429 before hashing, tested). The in-process limiter remains local defence in depth. Accepted tradeoff: a known email can be throttled by an attacker; edge per-IP limits bound it.
- **Status:** Resolved for the starter (Phase 7); add CAPTCHA or a shared store per project if needed

### 🐛 BUG-013: Selected frontend major versions have unresolved npm advisories
- **Date Discovered:** 2026-09-24
- **Severity:** High for development tooling; Medium for shipped SPA dependency
- **Component:** Frontend dependencies
- **Symptoms:** `npm audit --audit-level=high` reports 7 advisories (5 moderate, 1 high, 1 critical) in the locked Vite 5/Vitest 2 toolchain and React Router 6. Production-only audit reports two moderate React Router advisories.
- **Root Cause:** ADR 002 and the folder architecture select older major versions; npm's proposed fixes require Vite 8, Vitest 5, and React Router 7, which are major upgrades outside Phase 4's approved stack.
- **Fix Applied:** Vite dev server binds only `127.0.0.1`; no Vite/Vitest server is shipped in the static production bundle. The only post-login navigation target is the fixed `/dashboard` path, and all app links use fixed internal paths; the SSR hydration advisory does not apply to this SPA. No forced major upgrade was made silently.
- **Verification:** Full npm audit failed with 7 findings. `npm audit --omit=dev --audit-level=high` exited 0 but still reported two moderate Router findings. Frontend tests, typecheck, lint and static build pass.
- **Phase 6 note:** Adding `@vitest/coverage-v8@2.1.9` (dev only, matched to Vitest 2.1.9) raises the full audit to 8 entries (2 critical). The new entry is inherited from the existing Vitest advisory, not a new underlying vulnerability; the production audit is unchanged (2 moderate Router findings).
- **Phase 7 disposition:** every affected package is at the latest release of its major (react-router-dom 6.30.6, vite 5.4.21, vitest 2.1.9); all fixes require major upgrades. Production: the Router backslash open redirect needs untrusted `<Link>`/`navigate()` targets — the app uses fixed paths and an exact login allowlist (regression tests include backslash variants); the `deserializeErrors` advisory is SSR-only and this is a client-rendered SPA. Dev tooling (Vite/esbuild/Vitest) affects dev/UI servers only: Vite binds 127.0.0.1, Vitest UI is not installed, production images ship only static files behind Nginx. CI gates `npm audit --omit=dev --audit-level=high`. Reassess at the next major-version ADR.
- **Status:** Resolved — accepted with documented scope (ADR 014)

### 🐛 BUG-015: Admin table sr-only labels widened the mobile page
- **Date Discovered:** 2026-09-24
- **Severity:** Low
- **Component:** Frontend admin tables
- **Symptoms:** At 375 px the admin users page scrolled horizontally to 561 px even though the table was inside an `overflow-x-auto` region.
- **Root Cause:** Absolutely positioned `sr-only` labels inside the wide table had no positioned ancestor within the scroll region, so they extended the document.
- **Fix Applied:** Table scroll regions are `relative`.
- **Verification:** Live browser measurement: users and audit pages at 375 px have document width 375 in Arabic and English.
- **Status:** Resolved

### 🐛 BUG-016: Last-superadmin check blocked unrelated admin changes
- **Date Discovered:** 2026-09-24
- **Severity:** Medium (caught before commit)
- **Component:** `backend/app/services/admin_service.py`
- **Symptoms:** On an installation without any superadmin, an admin disabling an ordinary user received 409.
- **Root Cause:** The invariant was evaluated after every change instead of only changes that remove an active superadmin.
- **Fix Applied:** The check runs only when the target currently holds `superadmin` and loses it or is disabled.
- **Verification:** `test_admin_status_change_is_immediate_revokes_sessions_and_is_audited` (no superadmin present) and the concurrent-demotion test pass.
- **Status:** Resolved

### 🐛 BUG-014: Logout signal emitted after releasing the session Web Lock
- **Date Discovered:** 2026-09-24
- **Severity:** Low
- **Component:** Frontend auth coordinator (`frontend/src/lib/api.ts`)
- **Symptoms:** A refresh queued behind logout acquired the Web Lock before `signed-out` was emitted and called `/users/me` and `/auth/refresh`, contrary to the ADR 011 contract.
- **Root Cause:** `login()` and `logout()` emitted their BroadcastChannel signal after `navigator.locks.request` resolved.
- **Fix Applied:** Signals are emitted inside the locked operation. Impact was limited: the logout response had already cleared the refresh cookie, so the stray refresh received a 401 and could not trigger reuse revocation.
- **Verification:** A new Vitest test with a serializing lock fails before and passes after the fix; the live logout left `/users/me` and `/auth/refresh` at 401.
- **Status:** Resolved

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
