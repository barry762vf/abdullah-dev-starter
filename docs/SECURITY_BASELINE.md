# Security baseline

The starter supplies controls for the current API and two shipped proxy topologies. Clone owners must review new routes, data policies, secrets and ingress before deployment. This document describes implemented behavior; see [deployment](DEPLOYMENT_STRATEGY.md) for operator steps and [auth](AUTH_STRATEGY.md) for the session contract.

| Area | Implemented control |
| --- | --- |
| Passwords | Argon2id; request-time work offloaded from the event loop with a bounded worker limiter. |
| Sessions | Signed 15-minute HS256 access JWT; opaque 14-day refresh token stored only as a SHA-256 digest, atomically rotated. Known revoked-token reuse ends that user's active refresh sessions. |
| Authorization | Every protected request loads active user and current roles from PostgreSQL. Admin router has a single role guard; only superadmins change roles/admin accounts. Advisory lock and last-active-superadmin check protect privileged changes. |
| Browser cookies/CSRF | Host-only, HttpOnly, SameSite=Lax cookies; Secure required outside development. Cookie-authenticated mutations, refresh and logout require `X-Requested-With: XMLHttpRequest`; CORS permits explicit origins only. The browser uses one origin. |
| Input/SQL | Pydantic request validation and parameterized SQLAlchemy statements. Admin search escapes SQL LIKE wildcards. Database exception details and bound values are excluded from application logs. |
| Error/logging | RFC 7807 responses, generic unexpected-error text, request IDs, JSON request logs and persistent auth/admin audit events. Audit strings are rendered as text in the UI. |
| HTTP/ingress | API security headers and no-store responses; HSTS outside development. `CLIENT_IP_SOURCE=edge_header` authenticates the proxy's observed IP with a shared secret and rejects direct API requests except liveness. Uvicorn does not trust forwarded headers. |
| Abuse | Local per-process auth limits, PostgreSQL per-account failed-login throttle; bundled Nginx per-IP limits. Cloudflare deployments require WAF rules configured by the operator. |
| Production | Non-root/read-only containers, dropped capabilities, private API/database networks, explicit migration job, production settings validation and no runtime bootstrap password. CI uses throwaway credentials. |

The frontend CSP is configured in `frontend/nginx/` and `frontend/public/_headers`; API CSP denies content by default, with an interactive-docs exception in development. The code does not include a generic SSRF firewall, external security scanner, Dependabot policy, pinned Docker image digests, or global distributed IP limiter. Those controls may be added by a cloned project according to its threat model. Known dependency advisory scope is recorded as BUG-013 in `.ai/BUGS.md`.
