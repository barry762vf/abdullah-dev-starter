# Authentication and authorization contract

## Session flow

`POST /api/v1/auth/register` creates a user with the seeded `user` role and does not sign them in. `POST /auth/login` checks Argon2id credentials, creates a 15-minute signed access JWT and a 14-day opaque refresh token, and sets host-only HttpOnly SameSite=Lax cookies. Outside development, Secure cookies are mandatory. `POST /auth/refresh` atomically consumes a refresh digest and issues a successor; known revoked-token reuse revokes that user's active refresh sessions. Unknown or expired tokens return 401 without identifying a user. `POST /auth/logout` revokes the presented refresh session and clears both cookies. Cookie refresh/logout require `X-Requested-With: XMLHttpRequest`.

`GET /api/v1/users/me` returns the current user. `PATCH /users/me` changes only `full_name`. Protected API routes accept an access cookie or an `Authorization: Bearer` access JWT; cookie-authenticated mutations require the custom header. JWTs carry identity and lifetime, not roles. Every protected request loads the current active user and roles from PostgreSQL, so disabling or demoting an account affects its next request. Logout does not invalidate an already issued Bearer access JWT before its short expiry.

The browser uses relative `/api/v1` paths and one origin. Its API client serializes refresh/login/logout with Web Locks across tabs and sends only non-secret state through BroadcastChannel. A lost refresh response is ambiguous and is never automatically replayed; browsers without Web Locks require re-login when access expires. Access and refresh tokens are not stored in JavaScript storage. The backend remains authoritative even when frontend route guards hide UI.

## Roles and administration

The role seed inserts `user`, `admin` and `superadmin`. A superadmin satisfies reusable role guards. `GET /api/v1/admin/users`, `/stats`, and `/audit-logs` are available to admins and superadmins. `PATCH /api/v1/admin/users/{id}` can set `is_active`, `is_verified`, or the complete `roles` set. Only a superadmin may change roles or administrator accounts. No actor can change their own account through this route; at least one active superadmin must remain. Privileged changes are serialized with a PostgreSQL advisory lock and audited. There is no user-deletion, password-change, or role-management UI in this starter.

Run `python -m app.core.seed` after migration. Before opening registration, set a unique `INITIAL_ADMIN_EMAIL` and 12–128 character `INITIAL_ADMIN_PASSWORD`, run `python -m app.core.seed --bootstrap-admin` once, and remove the password. It never promotes an existing account. Production API startup rejects a leftover bootstrap password.

## Abuse controls and deployment

The API has per-process IP limits and a PostgreSQL-backed per-account failed-login throttle. The bundled Nginx proxy adds shared per-IP limits; Cloudflare deployments need WAF rules configured on the host. `CLIENT_IP_SOURCE=edge_header` accepts the observed client IP only from a proxy authenticated with `EDGE_PROXY_SECRET`; Uvicorn does not trust arbitrary forwarding headers. See [deployment](DEPLOYMENT_STRATEGY.md) and [security](SECURITY_BASELINE.md).
