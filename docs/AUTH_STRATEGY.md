# 🔐 Authentication & Role-Based Authorization Strategy

> **Document:** `AUTH_STRATEGY.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Authentication Architecture & Token Lifecycle

Phase 3 implements short-lived JWT access tokens and rotating opaque refresh tokens. JWT verification is followed by a database lookup for current account and role state on protected requests, so disabling an account or removing a role takes effect on the next request.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant API as FastAPI Backend (/api/v1/auth)
    participant DB as PostgreSQL Database

    Note over User, API: 1. Login Request
    User->>API: POST /auth/login { email, password }
    API->>DB: Query user by email
    DB-->>API: User record (Argon2id hash, roles, is_active)
    API->>API: Verify password with Argon2id
    API->>API: Generate Access Token (JWT: exp 15m)
    API->>API: Generate opaque refresh token with secrets.token_urlsafe(32)
    API->>DB: Store RefreshToken hash (SHA-256, exp 14d)
    API-->>User: 200 OK + Set HTTP-Only Cookies (access_token, refresh_token) + User JSON

    Note over User, API: 2. Authenticated API Call
    User->>API: GET /users/me (Cookie or Bearer header)
    API->>API: Verify JWT signature & expiration
    API->>DB: Load user by primary key; check is_active and current roles
    API-->>User: 200 OK { user_profile }

    Note over User, API: 3. Token Rotation (Access Token Expired)
    User->>API: POST /auth/refresh (HTTP-Only refresh_token cookie)
    API->>DB: Conditionally set is_revoked and revoked_at by hash/expiry (UPDATE RETURNING)
    alt Token Valid
        API->>DB: Insert new refresh-token hash in same transaction
        API->>API: Issue new Access Token (15m) & new Refresh Token (14d)
        API-->>User: 200 OK + New HTTP-Only Cookies
    else Known revoked token reused
        API->>DB: Mass-revoke ALL refresh tokens for this user!
        API-->>User: 401 Unauthorized (Force re-login)
    else Unknown or tampered token
        API-->>User: 401 Unauthorized (No user-wide revocation possible)
    end
```

---

## 2. Token Security & Storage Rules

1. **HTTP-Only, Secure, SameSite Cookies:**
   - By default for web browsers, tokens are set in cookies with:
     - `HttpOnly = True`: JavaScript cannot directly read the token, though XSS can still send authenticated requests.
     - `Secure = True`: Transmitted exclusively over HTTPS (disabled only on local `localhost`).
     - `SameSite = 'Lax'`: Restricts cross-site cookie sending; the custom request header and exact CORS allowlist additionally protect cookie-authenticated mutations.
2. **Dual-Mode Authorization (Header Fallback):**
   - For external mobile clients (e.g. Abdullah's React Native or Android apps) or CLI tools, the API also accepts standard `Authorization: Bearer <token>` headers.
3. **Password Hashing Standard:**
   - **Argon2id** (the OWASP gold standard, memory-hard, GPU-resistant).
   - Salt is cryptographically generated automatically per password.
4. **Opaque Refresh Tokens and Rotation (Phase 3 design):**
   - Generate each raw token with `secrets.token_urlsafe(32)` and persist only its SHA-256 digest. Never log the raw token or digest.
   - In one database transaction, conditionally update the row matching the digest only when `is_revoked = false` and `expires_at > now()`, setting `is_revoked = true` and `revoked_at = now()`, and return its `user_id`. Insert the successor digest before commit. Return cookies only after commit succeeds. A conditional update prevents two requests from both rotating the same token.
   - If the conditional update affects no row, look up the digest to distinguish a known revoked token from unknown or expired input. Known revoked-token reuse revokes that user's remaining refresh tokens in the same transaction; unknown/tampered input cannot be mapped to a user and only receives `401`. Expired input also receives `401` without user-wide revocation.
   - There is no acceptance grace window in this baseline. Concurrent refreshes from two tabs can be interpreted as reuse and force re-login. `revoked_at` records when rotation or logout happened for replay analysis; a later grace policy would need a separate, carefully designed successor relationship to avoid accepting a stolen token.
5. **Current Authorization State (Phase 3 implementation):**
   - `get_current_active_user` loads the user by the JWT subject's primary key on each protected request and checks `is_active` and current role assignments. No JWT role claim is issued. This adds one indexed user lookup plus role loading but avoids stale authorization for up to the 15-minute token lifetime.

### Implemented API contract

- `POST /api/v1/auth/register` returns `201` with a sanitized profile and grants only the seeded `user` role. It does not sign the user in. Passwords require 12–128 characters. Missing baseline roles return `503`; duplicate emails return `409`.
- `POST /api/v1/auth/login` returns a sanitized profile and sets `access_token` (15 minutes, path `/api/v1`) and `refresh_token` (14 days, path `/api/v1/auth`) cookies. Both are HttpOnly and SameSite=Lax; Secure follows `COOKIE_SECURE`, which must be true outside development.
- `POST /api/v1/auth/refresh` rotates the refresh cookie and returns a profile. `POST /api/v1/auth/logout` revokes the presented refresh session, clears both cookies, and returns `204`. Both routes require `X-Requested-With: XMLHttpRequest`; this custom header and the explicit CORS origin allowlist provide the CSRF check for cookie requests.
- `GET /api/v1/users/me` returns the current profile. `PATCH /api/v1/users/me` updates only `full_name` and requires the same custom header when authenticated by cookie. `Authorization: Bearer <access JWT>` is supported on protected routes, including PATCH; refresh and logout use the HttpOnly refresh cookie.
- Access JWTs contain `sub`, `type`, `iat`, and `exp`; no role claims are issued. Current roles are loaded from PostgreSQL. A `superadmin` role satisfies any role guard; other roles must be explicitly allowed. The API does not expose admin-management routes until Phase 5.
- Run `python -m app.core.seed` from `backend/` to seed roles. To create the first superadmin, temporarily provide a valid `INITIAL_ADMIN_EMAIL` and a unique 12–128-character `INITIAL_ADMIN_PASSWORD`, then run `python -m app.core.seed --bootstrap-admin`. The command uses a PostgreSQL transaction lock and never resets an existing superadmin. Remove the bootstrap password afterward; ordinary application startup does not require it.

### Browser refresh coordination contract (Phase 4 implementation requirement)

The approved backend has **no refresh grace window**. Two uses of the same rotated refresh cookie cause known-reuse revocation, including the newly issued session. A response lost after commit can leave the browser with the old cookie and also force re-login. The Phase 4 client must implement the following contract before wiring its Axios interceptor or `AuthGuard`:

1. Use a single in-tab promise for all requests that encounter an expired access cookie. Exclude `/auth/login`, `/auth/refresh`, and `/auth/logout` from automatic 401 interception, and retry an original request at most once. Send `X-Requested-With: XMLHttpRequest` on every API request; the browser never reads the HttpOnly tokens.
2. Serialize browser session mutations across tabs on the **same frontend origin** with `navigator.locks.request("abdullah-auth-session", async () => ...)`. Use this lock for refresh and logout, and for login when it replaces a session. Hold it until the response and cookies have been processed. The same-origin production topology below ensures tabs share the lock and cookie jar.
3. After acquiring the lock for a 401, call `GET /api/v1/users/me` first. If it succeeds, another tab already refreshed; release the lock and retry the original request once. If it returns 401, call `POST /api/v1/auth/refresh` **once** with the custom header, then release the lock and retry the original request once after success. Do not replay the original mutation merely to test whether another tab refreshed.
4. Use `BroadcastChannel` only for non-secret state signals (`auth-updated`, `signed-out`, `refresh-uncertain`). A successful refresh/login broadcasts `auth-updated`; receivers re-fetch `/users/me`. Logout runs under the same lock, clears client user/query caches, then broadcasts `signed-out`; other tabs clear their caches and stop queued retries without calling logout or refresh again. Maintain an in-memory auth generation in each tab; after acquiring the lock, a queued refresh must abort if it observed a sign-out while waiting. Browser cookies are shared automatically.
5. A refresh 401 means re-login is required; clear client state and broadcast `signed-out`. On a network error or timeout, the server may already have committed rotation: **never automatically retry `/auth/refresh`**. Broadcast `refresh-uncertain` so other tabs also stop automatic refresh. One `/users/me` probe may confirm a received new access cookie; if that fails, require a fresh login. Do not broadcast a global sign-out for an ambiguous network error alone.
6. Web Locks provides the cross-tab exclusion. BroadcastChannel does not. If Web Locks is unavailable, do not invent a racing localStorage lease or automatic cross-tab refresh. The safe fallback is in-tab single-flight plus re-login when access expires; a cloned project may add a separately tested coordination mechanism. No access or refresh token belongs in localStorage, sessionStorage, BroadcastChannel, or application state.

On initial page load, discover the session with `GET /users/me`; use its roles for UI display only. The backend remains authoritative. A logout does not invalidate an already issued access JWT carried as a Bearer header; it may remain valid for up to 15 minutes, so every tab must clear its in-memory user data and caches.

### Browser-facing origin (ADR 011)

The starter's production browser calls use relative `/api/v1/...` on the Cloudflare Pages hostname. A Pages `/api/*` edge route forwards to FastAPI on Railway, preserving cookie paths and separate `Set-Cookie` headers. The browser therefore sees one origin and can send host-only Secure, HttpOnly, SameSite=Lax cookies without credentialed cross-origin fetch. Local Vite uses an `/api` development proxy to keep the same browser URL shape. The edge route and its live cookie behavior must be built and tested before deployment. A project using separate same-site custom subdomains may choose that variant deliberately, with exact credentialed CORS and sibling-domain cookie review. See `docs/DEPLOYMENT_STRATEGY.md` for the deployment gates.

Phase 4 implements the browser coordinator in `frontend/src/lib/api.ts`. It serializes refresh, login, and logout with Web Locks where available; no-Web-Locks browsers require re-login when access expires. Login and logout emit their `auth-updated` / `signed-out` signal before releasing the lock, so a refresh queued behind them observes the new state. Session calls time out after 20 seconds so a hung request cannot hold the cross-tab lock; a timed-out refresh is treated as ambiguous and never retried. `BroadcastChannel` carries only the three state signals above, and the only browser storage keys are language and theme preferences. The API client normalizes RFC 7807 responses into `ApiError`. Frontend route guards use `/users/me` for user experience; the backend remains authoritative.

---

## 3. Role-Based Access Control (RBAC) Hierarchy

The authorization model supports fine-grained hierarchical permissions:

| Role | Scope & Permissions | Example Endpoints Allowed |
| :--- | :--- | :--- |
| **`superadmin`** | Full system control, role modifications, tenant creation, database health. | `DELETE /api/v1/users/{id}`, `GET /api/v1/admin/audit-logs` |
| **`admin`** | User management, audit log viewing, content moderation. | `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{id}/status` |
| **`manager`** | Optional extension role for client projects; not seeded by the foundation. | Project-specific endpoints |
| **`user`** | Standard end-user. Access to own resources and public endpoints. | `GET /api/v1/users/me`, `PATCH /api/v1/users/me` |
| **`guest`** | Unauthenticated public visitor, not a persisted/seeded role. | `POST /api/v1/auth/login`, `GET /api/v1/health` |

Only `superadmin`, `admin`, and `user` are seeded in the base installation. The database session dependency is currently `app.core.database.get_db`; Phase 3 can import it into `app/api/deps.py` alongside authentication dependencies.

### FastAPI Dependency Guards (`app/api/deps.py`):
```python
# Route requiring any authenticated user
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Route strictly requiring admin or superadmin
@router.get("/admin/users")
async def list_users(
    admin_user: User = Depends(require_role(["admin", "superadmin"])),
    db: AsyncSession = Depends(get_db)
):
    return await admin_service.get_users(db)
```

---

## 4. Frontend Route Guards & Role-Gated UI

1. **`AuthGuard` (`frontend/src/features/auth/AuthGuard.tsx`):**
   - Wraps authenticated routes (e.g., `/dashboard`, `/profile`).
   - If user is unauthenticated, redirects to `/login` preserving the `returnUrl`.
2. **`RoleGuard` (`frontend/src/features/admin/RoleGuard.tsx`):**
   - Inspects `user.roles`. If the user lacks the required role, renders an unauthorized screen (`403 Forbidden`) or redirects to `/dashboard`.
3. **Dynamic Navigation Filtering:**
   - The navigation sidebar dynamically hides administrative links (such as "إدارة المستخدمين" / "لوحة التحكم") from regular users to keep the interface uncluttered and clean.

---

## 5. Brute Force Defense & Rate Limiting

- **Endpoint Rate Limiting:**
  - `/api/v1/auth/login`: Maximum 5 attempts per 60 seconds per IP address (returns `429 Too Many Requests`).
  - `/api/v1/auth/register`: Maximum 3 registrations per hour per IP.
- **Audit Logging for Security Events:**
  - All failed login attempts, password changes, role elevations, and account suspensions trigger an entry in the `audit_logs` table recording the IP address, timestamp, and user agent.

Phase 3 records registration, successful and failed login, refresh, known refresh reuse, logout, and bootstrap events. Password changes, role elevations, and account suspensions belong to later account-management phases.

The current rate limiter attempts login 5/minute/IP and registration 3/hour/IP within one process using `request.client.host`; it is a starter-level abuse control, not a distributed anti-bot boundary. The app does not parse `X-Forwarded-For`, but Uvicorn can rewrite `client.host` before the app sees it: Uvicorn 0.34.2 defaults to proxy headers enabled and trusts `127.0.0.1`. Local direct development must run with `--no-proxy-headers`. A production reverse proxy must overwrite untrusted forwarding headers, and Uvicorn must use `--proxy-headers --forwarded-allow-ips=<exact trusted ingress IPs>`; never use `*` for an internet-reachable service. If exact ingress addresses cannot be established, do not claim the in-process per-IP limit or audit IP is client-accurate; provide edge/shared limiting before public deployment. The 4,096-key in-process cap can evict an active bucket during IP churn, IPv6 clients can rotate addresses, and there is no per-account throttle. These limitations and multi-worker enforcement remain Phase 7 deployment work.

Registration intentionally returns 409 for an existing email. Browser login and registration send JSON, not HTML forms; FastAPI currently rejects form and `text/plain` bodies for these routes. Refresh and logout require cookies even for non-browser clients; Bearer fallback applies to access-token protected routes only.
