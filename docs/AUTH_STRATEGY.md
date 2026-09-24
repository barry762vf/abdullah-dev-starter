# 🔐 Authentication & Role-Based Authorization Strategy

> **Document:** `AUTH_STRATEGY.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Authentication Architecture & Token Lifecycle

Phase 3 will implement short-lived JWT access tokens and rotating opaque refresh tokens. JWT verification is followed by a database lookup for current account and role state on protected requests, so disabling an account or removing a role takes effect on the next request.

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
     - `HttpOnly = True`: JavaScript cannot read the token (eliminates XSS token theft).
     - `Secure = True`: Transmitted exclusively over HTTPS (disabled only on local `localhost`).
     - `SameSite = 'Lax'`: Protects against Cross-Site Request Forgery (CSRF).
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
5. **Current Authorization State (Phase 3 design):**
   - `get_current_active_user` will load the user by the JWT subject's primary key on each protected request and check `is_active` and current role assignments. JWT role claims, if included, are informational rather than the authority for RBAC. This adds one indexed user lookup plus role loading but avoids stale authorization for up to the 15-minute token lifetime.

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
