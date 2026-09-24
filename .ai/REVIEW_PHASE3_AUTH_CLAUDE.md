# Independent Security Review: Phase 3 Authentication & RBAC

> **Reviewer:** Claude Code (Claude Opus 5.5). Independent application-security reviewer; did not implement Phase 3.
> **Date:** 2026-09-24
> **Commit reviewed:** `9a6d65a` (`feat: implement phase 3 authentication and RBAC`), with `b91412d` (pre-Phase-3 hardening) as its base.
> **Scope:** Phase 3 authentication, sessions and RBAC only. This is not a general architecture review. No fixes were implemented, and Phase 4 was not started.
> **Repository changes during the review:** this report and new follow-up items in `.ai/TODO.md`. No application code, tests, migrations or the Obsidian vault were modified.

---

## 1. Executive Summary

Phase 3 is **well implemented**. The core security mechanisms are correct and I verified them directly:

- **Passwords:** Argon2id with RFC 9106 parameters. Passwords never appear in responses, logs or audit rows.
- **JWT:** the algorithm is pinned; signature, expiry and required claims are enforced; the token type is checked.
- **Current state from the database:** every protected request loads the account and its roles from PostgreSQL (ADR 009). Role claims in the JWT are ignored.
- **Refresh tokens:** opaque 256-bit tokens; only SHA-256 digests are stored.
- **Rotation:** one atomic conditional `UPDATE … RETURNING` per refresh, with the successor token and audit row committed in the same transaction.
- **Reuse handling:** only a *known* revoked token triggers user-wide revocation. Unknown and expired tokens are rejected without side effects.
- **Bootstrap:** explicit command only, serialized with an advisory lock, and it never resets or promotes an existing account.

I found **no authentication bypass, privilege escalation, session takeover or secret exposure**.

| Severity | Count |
| :--- | :--- |
| CRITICAL | **0** |
| HIGH | **2** (both are browser-integration *design* items; neither is a backend code defect) |
| MEDIUM | **4** |
| LOW | **11** |

- **Phase 4 frontend shell:** safe to begin now.
- **Browser authentication integration:** safe to begin **locally** once the refresh-coordination contract (HIGH-01) is written into `AUTH_STRATEGY.md`. The production hostname/proxy topology (HIGH-02, BUG-008) must be decided before the API client's base-URL design is finalized, and before any deployment.

### How the review was done

- **Documents read:** everything in `.ai/` (including the earlier `REVIEW_CLAUDE.md` and Codex's appended resolution section), `AI_CONTEXT.md`, and the six requested guides in `docs/`.
- **Code and tests read:** every Phase 3 source file and test.
- **Commands and probes:**

| Check | Result |
| :--- | :--- |
| `.venv/Scripts/python.exe -m pytest -q` | **40 passed** (60.6 s) |
| Live probes against `abdullah_core_test` only. App probes ran inside a rolled-back outer transaction (the same pattern as `test_auth.py`). The bootstrap race used real commits and cleaned up after itself. | Results are cited per finding as **probe**. Afterwards the test database had 0 users, 0 tokens and 0 audit rows. |
| Uvicorn `ProxyHeadersMiddleware`, exercised with its default settings | Results in MEDIUM-02 |
| Installed versions | argon2-cffi 25.1.0, PyJWT 2.10.1, Uvicorn 0.34.2 |

The normal development database was not touched.

---

## 2. Password Security

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Argon2id configured correctly | ✅ | `security.py:18` uses the `PasswordHasher()` defaults: `Type.ID`, t=3, m=64 MiB, p=4 (the RFC 9106 low-memory profile). Probe: about 35 ms per verify. |
| No plaintext passwords stored | ✅ | `auth_service.py:49`, `seed.py:58`. Test asserts the stored value starts with `$argon2id$`. |
| Hashes never returned | ✅ | `profile()` builds `UserResponse` field by field (`user_service.py:21-30`); it has no password field. |
| Hashes never logged | ✅ | `hide_parameters=True`; database errors are logged by class only (`exceptions.py`). `test_auth.py:108-116` scans captured logs for the password, hash, raw token, digest and signing key. |
| Verification behavior | ✅ | Mismatch, invalid-hash and verification errors all return `False` (`security.py:25-29`). |
| Registration policy matches the docs | ✅ | 12–128 characters (`schemas/auth.py:19`). The login field is capped at 128 characters, which bounds Argon2 cost per request. |
| Bootstrap uses the same mechanism | ✅ | `seed.py:58` calls `hash_password`, with the same 12–128 rule plus sample-password rejection. |
| Accidental copies (schemas, exceptions, repr, audit) | ✅ none found | Audit `details` is always `{}`; `Settings` uses `SecretStr`; validation errors omit input values. |

Findings: MEDIUM-01 (hashing blocks the event loop) and LOW-07 (no rehash check or Unicode normalization).

---

## 3. Registration

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Email normalization | ✅ | Trimmed and lowercased before `EmailStr` validation (`schemas/auth.py:12-15`). |
| Case-insensitive duplicate protection | ✅ | Database unique index `ux_users_email_lower`. Test: `PERSON@example.com` after `Person@Example.Com` returns 409. |
| Race conditions | ✅ | Two simultaneous registrations are resolved by the unique index; the loser gets `23505` → 409 (`auth_service.py:58-61`). |
| Default role | ✅ | Only the role named `user` is looked up and assigned (`auth_service.py:44-55`). |
| Missing baseline role | ✅ | Returns 503; a concurrent role deletion (`23503`) also maps to 503. Tested. |
| Rollback | ✅ | The user, role assignment and audit row commit together. Any `IntegrityError` rolls back first; other errors propagate and `get_db` closes the session, which rolls back. |
| Mass assignment / privilege escalation | ✅ none possible | `extra="forbid"`. Test: posting `"roles": ["admin"]` returns 422. There is no request path that can reach `superadmin` or `admin`. |
| Error leakage | ✅ | The 409 and 503 messages are fixed strings. |

**Can a malicious request obtain a privileged role? No.** Role assignment comes only from a server-side lookup of the `user` role, and `PATCH /users/me` accepts only `full_name` (`extra="forbid"`).

Findings: LOW-02 (squatting the intended admin email before bootstrap) and LOW-10 (409 reveals that an account exists; this is inherent and documented).

---

## 4. Login

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Credential verification | ✅ | Case-insensitive lookup via `func.lower(User.email)`, which uses the functional index. |
| Nonexistent user | ✅ | A precomputed dummy Argon2 hash is still verified (`auth_service.py:24,75-77`), so timing matches a wrong password. |
| Wrong password, disabled account | ✅ uniform | Probe: all three cases returned `401 Unauthorized "Invalid credentials."`. Disabled accounts are rejected only *after* password verification, so status and timing are the same. |
| Account-existence leakage | ✅ none from login | Registration does reveal existence (LOW-10). |
| Audit | ✅ | `auth.login_failed` (with `user_id` when the account exists) is committed before the 401. `auth.login` is committed with the refresh token. |
| Rate limiting | ⚠️ | See §13, MEDIUM-02 and MEDIUM-03. |
| Transactions and token issuance | ✅ | The refresh digest and audit row commit together; the access JWT and cookies are produced only after the commit. |
| Login CSRF | ✅ in practice | Probe: login with `Content-Type: text/plain` or `application/x-www-form-urlencoded` returns **422**, because FastAPI parses a JSON body only for JSON content types. A cross-site HTML form therefore can't log the victim into an attacker's account. This depends on implicit framework behavior and has no test (LOW-08). |

---

## 5. JWT

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Algorithm constrained | ✅ | `algorithms=["HS256"]`. Probes: `alg: none` → 401; HS512 with the same key → 401. |
| Key source | ✅ | `settings.secret_key` (`SecretStr`). Outside `development` it must be at least 64 hex characters (256 bits). See MEDIUM-04 for the default environment. |
| Signature mandatory | ✅ | Tampered token → 401 (test and probe). |
| Expiry mandatory | ✅ | `options={"require": ["sub","type","iat","exp"]}`, `leeway=0`. Probes: missing `exp` → 401; expired → 401 (tested). |
| Token type checked | ✅ | `type != "access"` is rejected (unit test with `type: refresh`). Probe: missing `type` → 401. |
| Malformed input fails safely | ✅ | Every `PyJWTError`, `ValueError`, `TypeError` and `KeyError` becomes `ValueError`, then 401. Probes: `sub` = `"admin"` → 401; `sub` = `5` → 401; `iat` in the future → 401. |
| User ID handling | ✅ | `UUID(payload["sub"])` is used only as a primary-key parameter. Unknown UUID → 401 (probe). |
| No trust in stale claims | ✅ | No role claim is issued. Probe: a validly signed token carrying an extra `"roles": ["superadmin"]` claim was served as an ordinary `["user"]` profile. |
| Disabled after issuance | ✅ | Next request → 401 (test). |
| Role removed after issuance | ✅ | Admin guard: 200 → role removed → 403 (test). |
| User deleted | ✅ | `load_user` returns `None` → 401 (code path; the probe with an unknown UUID covers the same branch). |

Findings: LOW-01 (a JWT stays valid until it expires after logout or reuse detection) and LOW-06 (lifetimes duplicated as literals).

---

## 6. Current User / RBAC

- **`get_current_user`** (`deps.py:23-42`):
  - If an `Authorization` header is present, it must be `Bearer <token>`; otherwise 401, and the cookie is *not* used as a fallback (probe: valid cookie plus `Basic abc` → 401). This is strict but unambiguous.
  - For cookie-authenticated unsafe methods it calls `require_cookie_csrf`.
  - It decodes the JWT, then loads the user and role assignments with explicit `selectinload` (`user_service.py:13-18`), which is compatible with `lazy="raise"`.
- **`get_current_active_user`** rejects `is_active = false` with 401.
- **`require_role`** (`deps.py:53-64`):
  - Refuses an empty role list when the guard is built.
  - Compares exact role names from the database, as a set.
  - A current database membership in `superadmin` satisfies any guard (ADR 010).
  - Multiple roles are handled as a set intersection.
  - Depends on `get_current_active_user`, so disabled accounts cannot pass a role guard.
- **Escalation vectors checked:** request input, JWT claims, cached roles (none cached, since roles are loaded per request), superadmin matching (exact string from the database), and string comparison mistakes. **None found.**
- **Missing dependencies:** every route in `router.py` was enumerated.
  - `/health`, `/ready` and `/auth/*` are intentionally public.
  - `GET` and `PATCH /users/me` both use `get_current_active_user`.
  - No route requires a role yet; `require_role` is exercised only through a test route.
  - **No protected route lacks its dependency.**

Finding: LOW-04 (`get_current_user` is exported without an `is_active` check and could be misused later).

---

## 7. Refresh Token Storage

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Cryptographically random | ✅ | `secrets.token_urlsafe(32)`, 256 bits (`security.py:57-58`). |
| Raw token never stored or logged | ✅ | Only `refresh_digest(raw)` is persisted. Test scans logs for the raw token. |
| SHA-256 digest only | ✅ | An unsalted SHA-256 is appropriate for a 256-bit random secret; HMAC or salting would add nothing. |
| Digest uniqueness | ✅ | Unique index plus `CHECK length = 64`. |
| Expiry enforced | ✅ | `expires_at > now()` inside the conditional UPDATE, using database time. |
| Revocation state | ✅ | `is_revoked` and `revoked_at` are always set together (rotation, reuse, disabled account, logout). |
| Digest leakage through database exceptions | ✅ | `hide_parameters=True`, and database errors are logged by class only because PostgreSQL `DETAIL` lines can contain the digest. Test: `test_database_error_logging.py`. |

---

## 8. Rotation & Concurrency

Implementation: `auth_service.py:96-148`.

1. A single `UPDATE refresh_tokens SET is_revoked = true, revoked_at = now() WHERE token_hash = :d AND NOT is_revoked AND expires_at > now() RETURNING user_id`.
2. The user is loaded; a disabled or deleted user causes all of their tokens to be revoked, then a 401 is returned.
3. The successor digest and the `auth.refresh` audit row are added.
4. A single `COMMIT`.
5. Cookies are set on the response only after the service returns, which is after the commit.

**Can two requests both rotate the same token?** No. Under PostgreSQL's default READ COMMITTED isolation, a second `UPDATE` on the same row waits for the first transaction's row lock. When the first commits, PostgreSQL re-checks the `WHERE` clause against the new row version (`is_revoked` is now true), so the second updates 0 rows.

Evidence:
- `test_concurrent_refresh_consumes_token_once` (independent connections): exactly one success and one 401.
- Code: there is no read-then-write gap.

The undesirable states from the review brief:

| State | Reachable? | Why |
| :--- | :--- | :--- |
| Old token revoked, successor not committed | No | Same transaction. Any exception before the commit leaves the session to close, which rolls back the UPDATE. |
| Successor committed while old token remains usable | No | Same transaction. |
| Two successors created | No | Row-lock re-check, as above. |
| Audit committed independently of token state | No, in refresh | Same commit. (A failed *login* commits its audit row alone, which is intended.) |
| Cookie returned before commit | No | The service commits before returning (`auth_service.py:147-148`). |
| Rollback leaves inconsistent session | No | `get_db` closes the session, which rolls back any open transaction. |

**Residual risk (not a defect):** if the commit succeeds but the response never reaches the browser (a dropped connection or a tab closed mid-request), the browser keeps the old cookie. Its next refresh is then treated as known reuse, and **all of the user's sessions are revoked**. This, together with multi-tab races, is HIGH-01.

---

## 9. Reuse Detection

| Input | Required (ADR 009) | Actual | Evidence |
| :--- | :--- | :--- | :--- |
| Unknown token | 401, no user-wide revocation | ✅ | No row matches, so there is no `user_id` to act on (`auth_service.py:111-120`). Test: after an unknown-token attempt, the successor is still valid. |
| Expired token | 401, no mass revocation | ✅ | Excluded by `known.unexpired` (`:120`). Test: another valid session is unaffected. |
| Known revoked, unexpired token | Treated as reuse; revoke all | ✅ | Revokes every token of `known.user_id` and writes the `auth.refresh_reuse` audit row in one commit. Test: the successor is revoked with `revoked_at` set. |
| Identity recovery | From the stored row only | ✅ | Taken from the digest's database row, never from input. |
| Can an attacker target another user? | Must not | ✅ Not without possessing that user's previously valid raw refresh token | Knowing an email or user ID is not enough. |
| Concurrent refresh | Documented: may force re-login | ✅ matches | The concurrent test asserts both rows end revoked. |

**Denial-of-service analysis:** only the holder of a genuine, previously valid refresh token can trigger mass revocation. There is **no attacker-without-token way to log out another user**. The only realistic triggers are benign: multi-tab races and lost responses (HIGH-01).

---

## 10. Logout

Implementation: `auth_service.py:151-163`, `auth.py:108-117`.

- Revokes only the token whose digest matches the presented cookie, and only if it is still active. It returns the `user_id` for the audit row and commits.
- **Unknown token:** 204, nothing changes (test). **Already-revoked token:** 204, no audit, and no reuse cascade, which is reasonable for logout. **Missing cookie:** 204, and the cookies are still cleared.
- Cookies are cleared with the same `path`, `secure`, `httponly` and `samesite` attributes they were set with (`auth.py:53-60`).
- **CSRF:** requires `X-Requested-With: XMLHttpRequest`. Also, SameSite=Lax cookies are not sent on cross-site POSTs.
- **Can attacker-controlled data revoke another user's sessions? No.** The data must be that user's exact raw refresh token.
- **Limitation:** the access JWT stays valid for up to 15 minutes after logout. Probe: using the old access token as a Bearer token after logout returned 200 (LOW-01).

---

## 11. Cookie / Browser Security

Probe with `COOKIE_SECURE=true`:

```text
access_token=…;  HttpOnly; Max-Age=900;     Path=/api/v1;      SameSite=lax; Secure
refresh_token=…; HttpOnly; Max-Age=1209600; Path=/api/v1/auth; SameSite=lax; Secure
```

| Attribute | Access cookie | Refresh cookie | Assessment |
| :--- | :--- | :--- | :--- |
| HttpOnly | ✅ | ✅ | JavaScript cannot read either token. |
| Secure | follows `COOKIE_SECURE` | same | Forced true outside `development` (config guard). |
| SameSite | Lax | Lax | Not sent on cross-site subrequests or cross-site POSTs. |
| Path | `/api/v1` | `/api/v1/auth` | The refresh token is not sent to ordinary API routes. Good scoping. |
| Max-Age | 900 s | 1,209,600 s | Matches the token lifetimes. |
| Domain | not set (host-only) | not set | Correct. See LOW-09 for sibling subdomains. |

### What `X-Requested-With: XMLHttpRequest` does, and does not, provide

**Provides:**
- The header is not CORS-safelisted, so a browser must send a preflight before any cross-origin request that carries it. `CORSMiddleware` only approves preflights from the explicit `CORS_ORIGINS` allowlist.
- An HTML form, image, link or `fetch` in `no-cors` mode from any other origin cannot attach the header. Cookie-authenticated `PATCH /users/me`, `/auth/refresh` and `/auth/logout` are therefore refused with 403.
- This matters most for **same-site but cross-origin** attackers, such as a sibling subdomain. SameSite=Lax does *not* stop those, because to the browser they are "same-site".

**Does not provide:**
1. Protection against XSS on an allowlisted origin: script there can set the header freely.
2. Protection if `CORS_ORIGINS` is too broad or includes a compromised origin.
3. Protection for state-changing `GET` routes. Only unsafe methods are checked, so `GET` routes must never change state.
4. Coverage of `/auth/login` and `/auth/register`. Those are protected only by the JSON content-type behavior (LOW-08).
5. Any user-intent guarantee. It is not a secret-token CSRF defense; it relies on the browser's CORS enforcement.

### Is this safe in the intended same-site SPA/API topology?

**Yes**, provided three conditions hold:
- The SPA and API are same-site (custom subdomains of one registrable domain) or same-origin (a reverse proxy).
- `CORS_ORIGINS` lists exactly the SPA origin.
- No untrusted content is served from a sibling subdomain (LOW-09).

The design correctly avoids `SameSite=None`.

---

## 12. Superadmin Bootstrap

Implementation: `seed.py:35-92`.

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Explicit invocation only | ✅ | Runs only with `--bootstrap-admin`; the app never calls it at startup. |
| No insecure defaults | ✅ | `.env.example` has empty `INITIAL_ADMIN_*` values. |
| Blank or sample credentials rejected | ✅ | Blank email, password under 12 or over 128 characters, and `Admin123!Secure` are all rejected (tested). |
| Argon2id | ✅ | `hash_password`. |
| First-admin race | ✅ | `pg_advisory_xact_lock` is taken before the "does a superadmin exist?" check. **Probe:** two parallel bootstraps with *different* emails on independent connections returned `[True, False]`, leaving exactly 1 superadmin. |
| Lock correctness | ✅ | Transaction-scoped: released on commit or rollback, so it cannot leak. The key is a fixed constant shared by all callers. |
| Repeated invocation | ✅ | Returns `False` if any superadmin assignment exists; the password is not needed then (tested). |
| Existing admin not reset | ✅ | No update path exists. |
| Existing account not promoted | ✅ | An email that already belongs to an account raises an error (`seed.py:52-53`). An attacker who pre-registers that email cannot be promoted by the bootstrap. |
| Correct role | ✅ | Looked up by exact name `superadmin`. |
| Transaction | ✅ | Role seed, lock, user, assignment and audit row all run in `factory.begin()` and commit once. |
| Password removable afterward | ✅ | Startup no longer requires it (ADR 010). |
| Credentials in logs | ✅ none | The error messages contain no values. |

Findings: LOW-02 (operator procedure when the admin email is already taken) and LOW-03 (silent outcome; a *disabled* superadmin also counts as existing).

---

## 13. Rate Limiting

Implementation: `rate_limit.py`, called at `auth.py:70,82`.

- **Acceptable starter behavior:**
  - One process, one worker; state lives in process memory.
  - Memory is bounded at 4,096 keys.
  - A thread lock makes each check-and-append atomic within the process.
  - A restart resets all counters. With N workers the effective limit is N times higher.
  - ADR 010 states all of this honestly.
- **Production limitations:**
  - The limiter is not global across workers or instances (tracked in the Phase 7 TODO).
  - **Eviction bypass, confirmed by probe:** after five failed logins, a sixth from the same IP returns 429. After 4,096 requests from *other* keys, that same IP was allowed again, because least-recently-used eviction discarded its history.
  - **IPv6:** a single attacker can use as many /128 addresses as they like, so a per-address limit is nearly meaningless against IPv6 clients.
  - **No per-account throttle:** a distributed credential-stuffing attack against one account is not limited at all.

  These are MEDIUM-03.
- **Peer-IP resolution:** the app reads only `request.client.host` and never parses forwarded headers itself (tested in-process with a spoofed `X-Forwarded-For`). However, **Uvicorn rewrites `client.host` before the app sees it** (MEDIUM-02):
  - Uvicorn 0.34.2 defaults to `proxy_headers=True` with trusted proxies `127.0.0.1`.
  - Probe: a loopback peer sending `X-Forwarded-For: 6.6.6.6` appears to the app as `6.6.6.6`.
  - Probe: a peer at `172.18.0.5` (a typical container-network reverse proxy) is *not* trusted, so every client would share the proxy's address.

---

## 14. Audit Logging

| Event | Recorded | `user_id` | Committed with state? |
| :--- | :--- | :--- | :--- |
| Registration | `auth.register` | new user | ✅ same commit |
| Successful login | `auth.login` | user | ✅ with refresh token |
| Failed login | `auth.login_failed` | user if the email exists, else null | ✅ committed before the 401 |
| Refresh | `auth.refresh` | user | ✅ with successor |
| Known reuse | `auth.refresh_reuse` | token owner | ✅ with mass revocation |
| Logout | `auth.logout` | token owner (only if a token was actually revoked) | ✅ |
| Bootstrap | `auth.bootstrap` | new admin | ✅ |
| Disabled account at refresh | **not recorded** | — | Tokens are revoked silently (LOW-05). |

- **Never stored:** plaintext passwords, password hashes, raw tokens, token digests or signing secrets. `details` is always `{}`, and the stored fields are fixed strings plus the IP and user agent.
- **Attacker-controlled fields:** the `User-Agent` header is stored verbatim (truncated to 512 characters) and can contain misleading or control characters. There is no injection risk in the database (parameterized) or in the JSON logs (escaped). The Phase 5 audit viewer must render it as text and should strip control characters (LOW-05).
- The IP comes from the peer address, subject to the Uvicorn behavior in MEDIUM-02.

---

## 15. Transaction Safety

| Flow | Boundary | Failure behavior |
| :--- | :--- | :--- |
| Register | Flush user → add role and audit → commit | `IntegrityError` → explicit rollback → 409/503. Anything else → session close rolls back. No partial user can remain. |
| Login | Success: token and audit in one commit. Failure: audit-only commit, then 401 | Intended. |
| Refresh | UPDATE → load → insert successor and audit → commit | Atomic (§8). |
| Reuse | UPDATE (0 rows) → SELECT → mass revoke and audit → commit → 401 | Atomic. |
| Inactive user at refresh | UPDATE → revoke all → commit → 401 | Atomic. |
| Logout | UPDATE → audit → commit | Atomic. |
| Profile update | Mutate loaded user → commit | FastAPI caches dependencies within a request, so `get_current_active_user` and the handler share one session. |
| Bootstrap | `factory.begin()` | `ValueError` or `IntegrityError` → rollback, and the lock is released. |
| `get_db` lifecycle | `async with session_factory()` | Closing the session rolls back any open transaction. The earlier review's request for a direct `get_db` exception test is still open (Phase 6 TODO). |

**No path leaves partial state.**

---

## 16. Test Gaps

The 40 tests are behavior-focused and exercise live PostgreSQL. That is good. Security properties that are **not** pinned by any test:

1. **Refresh race strength:** the concurrent test cannot tell a true race from sequential execution (both pass the same way). The *property* holds by code inspection; a test using an `asyncio.Event` barrier or `pg_sleep` inside the transaction would prove it.
2. **JWT edge cases not tested:** `alg: none`; HS512 substitution; missing `exp`, `sub` or `type`; non-UUID or integer `sub`; valid signature for a deleted user. (All verified by probe here, but none are regression-tested.)
3. **Extra `roles` claim ignored:** not tested (probe only).
4. **Cookie attributes:** `Path`, `Max-Age` and `Secure` when `COOKIE_SECURE=true` are not asserted; the tests check only `httponly` and `samesite`. Logout's clearing attributes are not asserted either.
5. **Login/register CSRF by content type:** `text/plain` and form-encoded bodies returning 422 is not tested (LOW-08).
6. **Bootstrap concurrency** (advisory lock), an existing-email bootstrap, and a disabled-superadmin bootstrap are not tested.
7. **Disabled account at refresh revokes every session:** only the 401 is asserted, not the revocation (probe confirmed 0 remaining).
8. **Access token after logout** is still accepted: behavior is not pinned (LOW-01).
9. **Route inventory:** no test checks that every non-public route depends on `get_current_active_user` (LOW-04).
10. **Limiter:** eviction, the `unknown` IP bucket, and Uvicorn proxy-header behavior are not tested (MEDIUM-02, MEDIUM-03).
11. **Rollback:** no test forces a failure *after* the conditional UPDATE and before the commit (for example a failing successor insert) to prove the old token stays valid.
12. **Log redaction** is checked only in the happy-path test; the reuse and bootstrap paths are not scanned.
13. `test_rate_limits` sends `X-Forwarded-For`, which proves only that the *app* ignores it, not the Uvicorn deployment behavior.

---

## 17. Critical Findings

**None.**

---

## 18. High Findings

### HIGH-01: The SPA refresh contract is undefined; ordinary browser behavior will trigger reuse detection and revoke every session

- **Component:** `backend/app/services/auth_service.py:110-128` (reuse branch); `docs/AUTH_STRATEGY.md` §2.4; the Phase 4 API client.
- **Problem:** ADR 009 deliberately has no grace window, so any second use of a rotated token revokes **all** of that user's refresh tokens, on every device. Browsers produce second uses in normal operation:
  - Several tabs share the cookies. When the access token expires, each tab's next request gets a 401 and each tab calls `/auth/refresh` with the same token.
  - If a refresh response is lost after the server commits, the browser keeps the old cookie.
- **Evidence:** `test_concurrent_refresh_consumes_token_once` asserts that after two concurrent refreshes, *both* rows are revoked (`test_auth.py:352`), which includes the winner's new successor. `AUTH_STRATEGY.md` acknowledges "Concurrent refreshes from two tabs … force re-login" but defines no client behavior that avoids it.
- **Consequence:** users are logged out on all devices whenever two tabs refresh together. The `auth.refresh_reuse` audit events fill with false positives, hiding real token theft. This is a self-inflicted denial of service, not a vulnerability.
- **Reproduction:** the existing concurrent test.
- **Recommended fix** (frontend contract only; **no backend or ADR 009 change**). Add a "Browser refresh contract" subsection to `AUTH_STRATEGY.md`:
  1. Serialize refresh across all tabs with the Web Locks API (`navigator.locks.request("auth-refresh", …)`); also single-flight within a tab.
  2. After acquiring the lock, **first retry the original request**: another tab may already have rotated the shared cookie. Call `/auth/refresh` only if the retry still returns 401.
  3. Never automatically retry `/auth/refresh` after a network error. On a refresh 401, treat the session as ended and route to login.
  4. Send `X-Requested-With: XMLHttpRequest` on every request (Axios does not add it by default).

  Optionally, check `document.visibilityState` to avoid refresh storms from background tabs.
- **Blocks Phase 4 shell:** No.
- **Blocks browser auth integration:** **Yes.** The contract must exist before the Axios interceptor is written.

### HIGH-02: Production SPA/API topology is not chosen (BUG-008); the API client design depends on it

- **Component:** deployment topology; `docs/DEPLOYMENT_STRATEGY.md`; Phase 4 `src/lib/api.ts`.
- **Problem:** already recorded as BUG-008 (not a new defect). SameSite=Lax cookies are not sent on cross-site `fetch`. The default `*.pages.dev` and `*.up.railway.app` hosts are different registrable domains, so browser auth cannot work across them.
- **Evidence:** `auth.py:31-50` (`samesite="lax"`); BUG-008; `DEPLOYMENT_STRATEGY.md` §1.
- **Consequence:** if the frontend is built assuming an absolute cross-site API URL, production auth fails. The tempting workaround, `SameSite=None`, would weaken CSRF protection and must not be used.
- **Recommended decision, required before the API client is finalized:** choose one:
  - **(a) Same-origin reverse proxy:** the SPA and `/api` are served from one host. This is recommended: no CORS in production, host-only cookies, and no sibling-subdomain cookie issues (LOW-09).
  - **(b) Same-site custom subdomains:** for example `app.example.com` and `api.example.com`, with `CORS_ORIGINS=https://app.example.com` exactly.

  For local development, use a **relative `/api` base URL through the Vite dev proxy**. It works today and matches option (a) exactly. Note that `localhost:5173` → `localhost:8000` is also same-site, so direct calls also work locally.
- **Blocks Phase 4 shell:** No.
- **Blocks browser auth integration:** **Local integration: no. Production: yes.** Decide before finalizing `api.ts` and before any deployment.

---

## 19. Medium Findings

### MEDIUM-01: Argon2 hashing runs on the event loop and stalls all concurrent requests

- **Component:** `backend/app/services/auth_service.py:49, 75-77`; `backend/app/core/security.py:21-29`.
- **Problem:** `hash_password` and `verify_password` are synchronous, CPU- and memory-heavy calls (about 35 ms each, 64 MiB) made directly inside `async def` handlers.
- **Evidence (probe):** `/health`, which never touches the database, took **1.8 ms at idle and 63.9 ms** when issued during a burst of 10 concurrent failed logins. The batch took 595 ms, meaning the logins ran one after another.
- **Consequence:** with a single worker, login and registration traffic stalls every other request. An attacker spread over many IPs (see MEDIUM-03) can degrade the whole API with about 25 logins per second.
- **Fix:** run them in a worker thread, for example `await anyio.to_thread.run_sync(verify_password, …)` or Starlette's `run_in_threadpool`. argon2-cffi releases the GIL while hashing. Keep the dummy-hash path identical so timing stays uniform.
- **Blocks shell:** No. **Blocks browser auth integration:** No. Fix before production.

### MEDIUM-02: Uvicorn's default proxy handling contradicts the documented peer-IP rule

- **Component:** runtime configuration (no launch configuration exists yet); `docs/AUTH_STRATEGY.md` §5; ADR 010.
- **Problem:** the documentation says the limiter "never parses arbitrary `X-Forwarded-For` headers" and that "direct development requests use the socket peer IP". Uvicorn 0.34.2 defaults to `proxy_headers=True` and trusts `127.0.0.1`, and it rewrites `client.host` before the app runs.
- **Evidence (probe with Uvicorn's own `ProxyHeadersMiddleware`):**
  - Loopback peer, `X-Forwarded-For: 6.6.6.6` → app sees `6.6.6.6`.
  - Loopback peer, `6.6.6.6, 7.7.7.7` → app sees `7.7.7.7`.
  - Peer `172.18.0.5` → app sees `172.18.0.5`.
- **Consequence:**
  1. **Locally or behind a same-host proxy:** any local process can choose its apparent IP, bypassing the limiter and writing a forged `ip_address` into audit rows.
  2. **In a container behind a reverse proxy on another address** (the Phase 7 plan): *every* client appears as the proxy. The 5-per-minute login limit becomes global, so a single attacker can lock out all logins site-wide.
- **Fix:**
  - Document and pin the launch flags: `--no-proxy-headers` for direct exposure, or `--proxy-headers --forwarded-allow-ips=<exact proxy IP>` behind a proxy, with the proxy overwriting (not appending to) client-supplied forwarding headers.
  - Correct the documentation wording.
  - Add a deployment smoke test that checks the IP recorded in the audit log.
- **Blocks shell:** No. **Blocks browser auth integration:** No. **Blocks production deployment:** Yes.

### MEDIUM-03: The limiter can be bypassed by key churn and IPv6, and has no per-account throttle

- **Component:** `backend/app/core/rate_limit.py:15-28`.
- **Problem and evidence (probe):** after 5 attempts, the sixth from IP X returns 429. After 4,096 checks from other keys (simulated IPv6 addresses), IP X was **allowed again**: `popitem(last=False)` evicted its history. Each IPv6 address gets its own bucket. Login attempts are counted per IP only, never per target account.
- **Consequence:** the documented "5/minute/IP" guarantee does not hold against a moderately resourced attacker. Password spraying or credential stuffing against a single account is unthrottled.
- **Fix, keeping the design small:**
  - Group IPv6 clients by /64 prefix.
  - When the store is full, evict buckets whose newest event is older than the window, rather than the least-recently-used bucket.
  - Add a second counter keyed by the normalized login email (for example 10 per 15 minutes) that returns the same generic 429.
  - The shared limiter for multiple workers remains a Phase 7 task.
- **Blocks shell:** No. **Blocks browser auth integration:** No. Fix before production.

### MEDIUM-04: `ENVIRONMENT` defaults to `development`, which disables every security guard (fail-open)

- **Component:** `backend/app/core/config.py:21` (`environment … = "development"`) and the validator's early `return` for development.
- **Problem:** a deployment that forgets to set `ENVIRONMENT` runs with no minimum signing-key length, `DEBUG` allowed, `COOKIE_SECURE=false` allowed, and HTTP origins allowed. A copied `.env.example` also supplies a publicly known `SECRET_KEY`.
- **Evidence:** code; the `.env.example` placeholder key; the validator exempts only `development` (BUG-007 fix).
- **Consequence:** with the public sample key, anyone can mint a valid access JWT for any user whose UUID they learn, taking over that account. Auth cookies would also be sent over HTTP. UUIDs are not publicly listed today, but Phase 5 admin views and audit logs will display them.
- **Fix:** make `ENVIRONMENT` required (no default), or default to `production` so developers opt *into* `development` through `.env`. Also reject the `.env.example` placeholder key in every environment except `development`; the hex/length check already covers this.
- **Blocks shell:** No. **Blocks browser auth integration:** No. Fix before any deployment.

---

## 20. Low Findings

| ID | Component | Problem and evidence | Consequence | Fix | Blocks shell / integration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| LOW-01 | `security.py`, `auth_service.py` logout/reuse | Access JWTs are not revoked by logout, reuse detection or refresh-time disabling. Probe: old access token → 200 after logout. (Disabling an account *is* immediate, via the database check.) | A stolen access token stays usable for up to 15 minutes after logout or theft detection. | Accept and document it as part of the short-lived-JWT design. If needed later, add a `users.sessions_invalid_before` timestamp compared against `iat`. That timestamp is also the natural hook for future password change/reset. | No / No |
| LOW-02 | `seed.py:52-53`; operations | Registration is open before bootstrap. An attacker can pre-register the intended `INITIAL_ADMIN_EMAIL`. The bootstrap then correctly refuses, but an operator might "fix" it by manually granting `superadmin` to the attacker-owned account. | Operator-assisted privilege escalation. | Documentation: run `--bootstrap-admin` before exposing registration. Never grant `superadmin` to an account that was not created by the bootstrap. If the email is taken, bootstrap with a different email. | No / No |
| LOW-03 | `seed.py:45-46, 81` | `main()` ignores the return value and prints nothing, so operators can't tell "created" from "skipped". A *disabled* sole superadmin counts as existing, so a recovery attempt silently does nothing. | Operator confusion; failed recovery. | Print `created` / `skipped: superadmin exists (active=…)`, with no secrets. Document how to recover. | No / No |
| LOW-04 | `deps.py:23` | `get_current_user` does not check `is_active` but is importable next to the active variant. | A future route using it would accept disabled accounts. | Rename it to `_get_token_user` (private), or document it; add a route-inventory test (§16.9). | No / No |
| LOW-05 | `auth_service.py:27-40, 130-137` | The audit `details` are always empty: no failure reason, and no attempted email for unknown-account failures. Refresh-time revocation for a disabled account is not audited. The `User-Agent` is stored verbatim. | Weaker investigations; the Phase 5 viewer must treat the user agent as untrusted. | Add a small fixed `reason` code (`bad_password`, `inactive`, `unknown_account`) with no secrets. Audit `auth.refresh_denied_inactive`. Strip control characters from the user agent at write time or in the viewer. | No / No |
| LOW-06 | `security.py:35`; `auth_service.py:87,143` | Lifetimes appear as `timedelta(minutes=15)` and `days=14` literals, separate from the `ACCESS_TOKEN_MINUTES` and `REFRESH_TOKEN_DAYS` constants that the cookies use. | A future edit could make cookie and token lifetimes disagree. | Use the constants everywhere. | No / No |
| LOW-07 | `security.py:21-29` | No `check_needs_rehash` on successful login; no Unicode normalization (NFKC) of passwords; 12 spaces is an accepted password. | Parameter upgrades won't reach old hashes; the same password typed on different keyboards/platforms may not match. | Rehash on login when needed; normalize with NFKC before hashing and verifying; optionally reject whitespace-only passwords. | No / No |
| LOW-08 | `auth.py:63-87` | Login and register CSRF resistance relies implicitly on FastAPI parsing JSON only for JSON content types (probe: `text/plain` and form-encoded → 422). No test pins this. | A future `Form(...)` auth endpoint would be CSRF-able. | Add a regression test. Document that auth forms must use JSON, or require `X-Requested-With` on them too. | No / No |
| LOW-09 | Cookie scoping under topology (b) | Host-only cookies can still be shadowed by `Domain=example.com` cookies set from any sibling subdomain (cookie tossing), with a longer path such as `/api/v1/auth`. | A compromised or untrusted sibling subdomain could fix a victim's session to the attacker's account. | Prefer topology (a). If using (b), serve no untrusted or user content on sibling subdomains. `__Host-` would force `Path=/` and widen the refresh cookie's scope, so it is not recommended here. | No / No (topology decision input) |
| LOW-10 | `auth_service.py:60-61` | Registration returns 409 for an existing email, revealing that the account exists. | Account enumeration, limited to 3 per hour per IP. | Accept and document. The alternative (always 202 plus an email) needs email verification, which is out of scope. | No / No |
| LOW-11 | `AUTH_STRATEGY.md` §2.2 | The docs promise Bearer support "for mobile clients", but `/auth/refresh` accepts only the cookie. | Non-browser clients must manage a cookie jar to refresh. | Clarify in the docs. Add a body-token refresh variant only if a real mobile client needs it. | No / No |

---

## 21. Good Decisions / Keep As-Is

Do **not** rewrite these:

1. **Argon2id through argon2-cffi defaults**, with a dummy-hash comparison for unknown accounts and one generic 401 for unknown, wrong-password and disabled accounts.
2. **A minimal JWT** (`sub`, `type`, `iat`, `exp`) with HS256 pinned, required claims, `leeway=0` and a token-type check. No role claims.
3. **ADR 009's database-authoritative identity:** each request loads the user and roles by primary key; disabling and role removal take effect immediately.
4. **Opaque refresh tokens** from `secrets.token_urlsafe(32)`, stored only as SHA-256 digests with a unique index and length check.
5. **Rotation by a single conditional `UPDATE … RETURNING`** in one transaction with the successor and audit row, and cookies set only after the commit. This is the correct race-safe pattern; do not replace it with SELECT-then-UPDATE.
6. **Separate handling of unknown, expired and known-revoked tokens.** Only a known revoked token identifies a user for mass revocation.
7. **No grace window (ADR 009).** Solve multi-tab behavior on the client (HIGH-01) rather than weakening replay detection.
8. **Cookie scoping:** HttpOnly, SameSite=Lax, host-only, Secure enforced outside development, access cookie on `/api/v1`, refresh cookie on `/api/v1/auth`.
9. **A custom-header CSRF check on cookie-authenticated unsafe methods**, combined with a strict CORS allowlist. It is simple and correct for the intended topology.
10. **`extra="forbid"` on every input schema**, and profiles built field by field. Mass assignment and field leakage are structurally prevented.
11. **An explicit bootstrap command** with a transaction-scoped advisory lock, rejection of sample credentials, no promotion of existing accounts, and no permanent bootstrap secret (ADR 010).
12. **Sanitized database error logging** (`hide_parameters` plus logging the exception class only).
13. **A deliberately small in-process limiter**, with its limits honestly documented. Keep it, and fix MEDIUM-03 in place rather than adding a dependency.
14. **Library choices:** PyJWT and argon2-cffi only; no passlib or python-jose; no hand-written cryptography. PyJWT 2.10.1 includes the fix for the 2.10.0 `iss` advisory (which does not apply here, since `iss` is unused).

---

## 22. Phase 4 Shell Readiness

**Safe to begin now.** The shell (scaffold, Tailwind with right-to-left support, i18n, `useDirection`, layout, the static Login and Register pages) needs no authentication decisions.

Two recommendations that keep options open at no cost:
- Use a **relative `/api` base URL through the Vite dev proxy**. It matches the recommended production topology.
- Configure the Axios instance to always send `X-Requested-With: XMLHttpRequest`.

---

## 23. Browser Auth Integration Readiness

**Can begin locally once HIGH-01's contract is written into `AUTH_STRATEGY.md`.** Decisions required before the interceptor and `AuthGuard` are wired:

1. **The refresh contract (HIGH-01):** Web Locks single-flight across tabs, retry the original request before refreshing, no automatic retry of `/auth/refresh`, and a refresh 401 means logged out.
2. **The production topology (HIGH-02):** same-origin proxy (recommended) or same-site custom subdomains. This sets the API base URL, whether CORS matters in production, and the LOW-09 constraints.
3. **Session discovery:** the SPA cannot read its cookies, so on load it must call `GET /users/me`; a 401 means signed out. Use `roles` from that response for UI gating only. The server remains authoritative.
4. **Logout UX:** the access token stays valid for up to 15 minutes elsewhere (LOW-01). Also clear client state and caches (the TanStack Query cache) on logout.

**Not required** for integration: fixing MEDIUM-01 through MEDIUM-04. They are production-readiness items.

---

## 24. Recommended Fix Order

1. **HIGH-01:** add the browser refresh contract to `docs/AUTH_STRATEGY.md` (documentation only).
2. **HIGH-02:** record the topology decision (ADR 011); resolve BUG-008 on paper.
3. **Test hardening (§16):** JWT edge cases, cookie attributes, login content-type CSRF, bootstrap lock race, disabled-refresh revocation, route inventory, rollback after the conditional UPDATE. These are cheap and lock in the current guarantees.
4. **MEDIUM-01:** move Argon2 into a thread pool.
5. **MEDIUM-04:** make `ENVIRONMENT` fail closed.
6. **MEDIUM-03:** limiter pruning, IPv6 /64 grouping and a per-account counter.
7. **MEDIUM-02:** pin the Uvicorn proxy flags and correct the docs (together with the Phase 7 deployment work).
8. **LOW items**, in order of convenience; LOW-02 and LOW-03 are the most operationally useful.

Items 1–2 unblock integration. Items 3–7 should land before any public deployment.

---

## 25. Second Brain Summary

*For Abdullah to copy into the vault manually; this review did not modify the vault.*

> **Phase 3 auth independent review (2026-09-24):** No critical issues. Argon2id, a minimal HS256 JWT, database-authoritative roles (ADR 009), opaque SHA-256-stored refresh tokens, and atomic `UPDATE … RETURNING` rotation were all verified correct, including under concurrency. Key lesson: with strict reuse detection and no grace window, **multi-tab SPAs must single-flight refresh across tabs (Web Locks) and retry before refreshing**, or users get logged out on every device. Deployment lessons: Uvicorn trusts `X-Forwarded-For` from 127.0.0.1 by default, and behind a container proxy all clients collapse to one IP, making per-IP login limits global. Argon2 must run off the event loop. `ENVIRONMENT` should fail closed. Next: write the refresh contract and choose a same-origin proxy topology, then Phase 4.
