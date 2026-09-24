# Abdullah Developer Kit — v1.0.0 durable handoff

The roadmap is complete through Phase 8. **Abdullah Developer Kit v1.0.0 is the stable reusable baseline.** Its frozen foundation includes FastAPI; PostgreSQL, SQLAlchemy and Alembic; authentication with refresh-token rotation; database-backed RBAC and administration; a React/Vite/TypeScript client; Arabic/English RTL/LTR; regression tests; Docker and CI; same-origin proxy deployment; optional integration slots; and the `.ai/` multi-agent handoff system.

Keep this starter generic. Product-specific schemas, workflows, roles and screens belong in cloned repositories. Optional Gemini, Telegram, Supabase Storage and SMTP adapters are disabled by default and require project credentials, policy and live verification.

Version policy: bug fixes use patch releases (`1.0.x`); backward-compatible reusable improvements use minor releases (`1.x.0`); breaking architecture changes use major releases (`2.0.0`). The annotated Git tag is the canonical release identifier.

The test and CI gates passed for the release code commit. Annotated tag `v1.0.0` and the GitHub release are published; GitHub is public and template-enabled. The first live deployment, WAF setup and enabled-provider calls remain per-project work. Earlier public Git history may retain removed personal context; the history was not rewritten. Detailed verification is recorded in `.ai/AGENT_HANDOFF.md`.
