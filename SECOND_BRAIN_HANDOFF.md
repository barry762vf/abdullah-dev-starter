# Abdullah Developer Core — Foundation Handoff

## Milestones

Phase 0 established the repository and local PostgreSQL development environment. Phase 1 provides the FastAPI foundation. Phase 2 adds the async PostgreSQL identity layer and reversible migrations. Phase 3 provides authentication and database-backed role authorization. Phase 4 adds a reusable static React shell with Arabic/English direction parity and browser authentication integration.

An independent review of Phases 0–2 was verified before authentication work. The foundation now enforces case-insensitive email identity, safe user/role deletion behavior, and sanitized database-error logging. Migration revision 002 records these changes and token revocation time. All changes were verified on the isolated PostgreSQL test database.

## Durable decisions and lessons

ADR 008 keeps baseline role seeding explicit and idempotent while reserving administrator account creation for Phase 3, when Argon2id hashing is available. Integration tests use a dedicated PostgreSQL database and guard against running schema changes on the development database. Application liveness and database readiness are separate endpoints.

ADR 009 defines the Phase 3 security boundary: protected requests check current account and role state in PostgreSQL; refresh rotation is atomic; only reuse of a known revoked token can identify a user for mass revocation. Raw refresh tokens will be opaque and cryptographically random, while only their digests are stored. The baseline has no replay grace window. Staging shares the non-development security guards.

Phase 3 implements that boundary with Argon2id passwords, 15-minute signed access tokens, and 14-day rotating opaque refresh tokens. First-superadmin provisioning is an explicit one-time command; no bootstrap password must remain configured. ADR 010 records the transaction lock, database-current role guards, and scoped authentication limits.

The independent Phase 3 security audit confirmed that strict one-use refresh rotation can revoke a session when tabs race; the browser must serialize refresh using a shared Web Lock and avoid replay after an ambiguous network failure. ADR 011 chooses one browser-facing origin: Cloudflare Pages will proxy `/api/*` to Railway while the SPA uses relative API URLs. This settles the SameSite=Lax architecture decision before Phase 4 browser work, though the edge route is not deployed yet.

ADR 012 makes runtime mode explicit and moves costly Argon2 work to a bounded worker pool. Production remains gated on verifying the proxy's forwarded IP trust and adding stronger shared or edge abuse controls; the existing per-process IP limiter is a starter control.

Phase 4 follows ADR 002 and ADR 005: React 18 and Vite 5 produce static assets; i18next switches Arabic RTL and English LTR at the document root; Tailwind logical properties keep one layout rather than parallel stylesheets. Cairo and Inter have system fallbacks. The frontend requests relative `/api/v1` paths and uses Vite's `/api` proxy locally. Browser refresh follows ADR 011 with Web Locks and state-only cross-tab signals, while tokens remain in HttpOnly cookies. The production edge route still needs deployment verification.

The selected older frontend major versions currently have npm advisories (BUG-013). Local development binds Vite to loopback and the shipped SPA uses fixed internal routes, but the version risk needs a deliberate review before broader use or public deployment.

## Verification milestone

Docker Compose started PostgreSQL 16. The isolated test database passed migration round-trips and drift checks; Phase 3's concurrent refresh test confirmed one-time consumption. After the security audit fixes, the full backend suite passed 43 tests with Ruff, dependency and schema-drift checks passing.

Phase 4 passed 25 frontend tests, TypeScript, lint, and a static production build, with the 43 backend tests still green. The full register, login, refresh and logout cycle worked through the local Vite proxy with HttpOnly cookies, and desktop, tablet and mobile checks confirmed English LTR and Arabic RTL behavior.

Lessons from finishing Phase 4: broadcast cross-tab session signals while the Web Lock is still held, or a queued refresh can act before it learns of a sign-out. Apply the saved text direction before the first paint. Bilingual modal menus need real dialog focus handling.

Phase 5 adds administration (ADR 013). The backend is the only security boundary: one router-level role guard covers every admin endpoint. Admins can view users, statistics and audit logs, and can enable, disable or verify ordinary accounts. Only a superadmin can change roles or manage other administrators, and no one can modify their own account through the admin API. Privileged changes are serialized with the same PostgreSQL advisory lock as the superadmin bootstrap and re-check the actor inside it, so at least one active superadmin always remains even when two superadmins act at the same moment. Disabling an account also ends its refresh sessions, and every effective change is recorded in the audit log. The frontend role guard and hidden navigation are conveniences only, and audit data is always rendered as plain text.

Lessons from Phase 5: invariants such as "at least one active superadmin" must be enforced only by the changes that can break them, or they block unrelated work; and absolutely positioned screen-reader text inside horizontally scrolling tables needs a positioned container, or it widens mobile pages.

Phase 6 turned the suites into a regression net: 99 backend and 45 frontend tests, with coverage reported but not enforced. Two durable testing lessons: concurrency tests must *prove* the overlap (for example, wait until PostgreSQL shows the second transaction blocked on the lock) or they can silently pass sequentially; and coverage for SQLAlchemy async code needs greenlet tracing, or executed code looks untested and misdirects effort.

Phase 7 (ADR 014) makes the starter deployable with one browser-facing origin: either the bundled Nginx image (SPA plus `/api/*` proxy) in front of an internal-only API and database, or Cloudflare Pages with a Pages Function proxy. The API learns the client IP only from its own proxy, which authenticates with a shared secret; requests that bypass the proxy are refused, so forwarded headers never need to be trusted and hosts with changing ingress IPs still work. Login abuse is limited at the edge per IP and in PostgreSQL per account, with no extra infrastructure. Migrations run once per release under a lock, and production refuses to start with unsafe settings instead of limping along.

Deployment lessons: a multi-worker Uvicorn parent keeps running when workers crash, so validate configuration once before starting it; the nginx template step does not fail on errors, so guard it explicitly; and `now()` inside a long test transaction is frozen, so time-window tests need real transactions.

## Next direction

Continue with Phase 8 integration slots. Before a public launch, run the documented live checks on the real hosts and add Cloudflare WAF limits. Build and verify the edge proxy before deployment; resolve the remaining production ingress, rate-limit, and dependency gates. The current task state is in `.ai/AGENT_HANDOFF.md` and `.ai/CURRENT_STATE.md`.
