# Abdullah Developer Kit — v1.0.0 backlog

> State: **Stable reusable baseline** · Phases 0–8 complete · No new phase is planned.

## Completed for v1.0.0

- [x] Repository, backend, PostgreSQL/Alembic, auth/refresh, RBAC, administration, bilingual RTL/LTR frontend and typed optional provider slots.
- [x] Backend/frontend test suites, CI, hardened Docker deployment and same-origin proxy architecture.
- [x] Clone setup, customization, security and deployment documentation; public template hygiene review.
- [x] Release audit: 136 backend tests (95% coverage), 54 frontend tests, local checks and all GitHub workflows green for release code commit `14598e9`.
- [x] Freeze the current architecture as the reusable v1 baseline and document semver policy.
- [x] GitHub repository is public and template mode is enabled.
- [x] Create and publish the annotated `v1.0.0` tag and GitHub release from stable freeze commit `462a5bb`.

## Future version improvement

- Reassess accepted npm advisories (BUG-013) and older pinned backend dependencies in a reviewed, tested maintenance update.
- Add seed CLI branch tests, refused-admin-attempt audit events, or schema metadata improvements only when a concrete reusable requirement justifies them.
- Consider broader optional integrations or framework improvements through the minor/major release policy in ADR 016; do not add product-specific functionality to the starter.

## Deployment-specific

- For each deployment, verify TLS, same-origin cookies, direct API bypass refusal, audit client IP, rate limits/WAF and backups on the chosen hosts.
- Configure provider credentials, quotas, egress controls and real service tests only when enabling an integration. Install a durable Telegram update handler before configuring the webhook.

## Project-specific in cloned repositories

- Add business data models, routes, workflows, roles, authorization policy, branding and privacy/data-retention rules for the product being built.
- Decide whether to expose registration, add recovery flows, or customize the dashboard. Keep these changes in the clone rather than the reusable v1 foundation.
