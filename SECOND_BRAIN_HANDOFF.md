# Abdullah Developer Core — Foundation Handoff

## Milestones

Phase 0 established the repository and local PostgreSQL development environment. Phase 1 provides the FastAPI foundation. Phase 2 adds the async PostgreSQL identity layer and reversible migrations. Phase 3 now provides authentication and database-backed role authorization.

An independent review of Phases 0–2 was verified before authentication work. The foundation now enforces case-insensitive email identity, safe user/role deletion behavior, and sanitized database-error logging. Migration revision 002 records these changes and token revocation time. All changes were verified on the isolated PostgreSQL test database.

## Durable decisions and lessons

ADR 008 keeps baseline role seeding explicit and idempotent while reserving administrator account creation for Phase 3, when Argon2id hashing is available. Integration tests use a dedicated PostgreSQL database and guard against running schema changes on the development database. Application liveness and database readiness are separate endpoints.

ADR 009 defines the Phase 3 security boundary: protected requests check current account and role state in PostgreSQL; refresh rotation is atomic; only reuse of a known revoked token can identify a user for mass revocation. Raw refresh tokens will be opaque and cryptographically random, while only their digests are stored. The baseline has no replay grace window. Staging shares the non-development security guards.

Phase 3 implements that boundary with Argon2id passwords, 15-minute signed access tokens, and 14-day rotating opaque refresh tokens. First-superadmin provisioning is an explicit one-time command; no bootstrap password must remain configured. ADR 010 records the transaction lock, database-current role guards, and scoped authentication limits.

The approved SameSite=Lax cookie model requires same-site SPA and API hosts or a same-origin proxy. Default Cloudflare Pages and Railway hostnames are cross-site. This must be resolved before browser auth integration; a shared limiter and trusted proxy settings are needed when deployment scales beyond one backend process.

## Verification milestone

Docker Compose started PostgreSQL 16. The isolated test database passed migration round-trips and drift checks; Phase 3's concurrent refresh test confirmed one-time consumption. The full backend suite passed 40 tests.

## Next direction

Implement Phase 4 frontend shell and bilingual RTL/LTR behavior, choosing the browser/API domain arrangement before connecting authentication. The current task state is in `.ai/AGENT_HANDOFF.md` and `.ai/CURRENT_STATE.md`.
