# Abdullah Developer Kit — durable handoff

The foundation roadmap is complete through Phase 8. The v1.0.0 release candidate combines a FastAPI/PostgreSQL backend, React bilingual SPA, database-backed auth and administration, guarded migrations, CI, a production container topology and disabled-by-default integration slots.

The durable architecture is one browser-facing origin for SPA and `/api/*`, with an authenticated proxy conveying the observed client IP. Roles come from the current database, refresh tokens rotate once, and the first administrator is bootstrapped explicitly. Optional Gemini, Telegram, Supabase Storage and SMTP adapters require project credentials and policies; the core starts without them.

Release preparation removed machine-specific and private profile context from the current public template while preserving `.ai/` engineering handoffs. The Git tag is the canonical release version. Historical commits were not rewritten and may retain early context. The first live Cloudflare/Railway deployment, WAF configuration and provider calls remain project-specific verification. BUG-013 records accepted dependency advisory scope pending a planned upgrade.

Next direction: confirm the release-preparation CI, publish `v1.0.0` when green, then use the deployment runbook for each chosen host. Keep day-to-day commands and exact test evidence in `.ai/AGENT_HANDOFF.md`.
