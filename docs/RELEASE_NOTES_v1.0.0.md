# Abdullah Developer Kit v1.0.0

The first release provides a reusable FastAPI/PostgreSQL backend and React/TypeScript SPA. It includes English LTR and Arabic RTL UI, authentication with Argon2id passwords and rotating HttpOnly-cookie sessions, database-backed RBAC and administration, explicit Alembic migrations, and audit events.

The repository includes backend and frontend regression suites, GitHub Actions workflows, a hardened Docker/Nginx production stack, and a same-origin Cloudflare Pages proxy option. Optional Gemini, Telegram, Supabase Storage and SMTP adapters are disabled by default. See [integrations](INTEGRATIONS.md) for the exact shipped behavior.

**Security and operations:** validated production configuration, proxy-authenticated client IP, layered authentication limits, generic error responses, non-root/read-only containers, one-shot migration job and explicit first-superadmin bootstrap. See [security](SECURITY_BASELINE.md) and [deployment](DEPLOYMENT_STRATEGY.md).

**Known limits:** The first Cloudflare Pages/Railway deployment, WAF rules and host-specific cookie/IP behavior require live verification. Optional providers need real project credentials, quotas and integration tests before production use. BUG-013 records eight accepted full-tree npm findings; the production dependency gate passes with two moderate React Router findings. Direct backend pins, including FastAPI, should be reviewed in a later dependency-maintenance pass. The starter does not ship a business data model, password recovery, product-specific roles, or live provider credentials.

The Git tag `v1.0.0` is the canonical release identifier; backend and frontend package metadata are aligned to `1.0.0`. Bug fixes use patch releases (`1.0.x`); compatible reusable improvements use minor releases (`1.x.0`); breaking architecture changes use major releases (`2.0.0`). Product-specific features belong in cloned projects.
