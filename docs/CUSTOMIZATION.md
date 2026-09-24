# Customize a clone

Keep the security and session contracts in [auth](AUTH_STRATEGY.md) and [deployment](DEPLOYMENT_STRATEGY.md) in view as you adapt the starter.

| Change | Where to start |
| --- | --- |
| Project/application name | Rename the repository and package metadata in `backend/pyproject.toml` and `frontend/package.json`; update the FastAPI title in `backend/app/main.py`, page title in `frontend/index.html`, README and CI/deploy labels. Regenerate `frontend/package-lock.json` with npm after changing package metadata. |
| Branding | Replace text and symbols in `frontend/src/components/layout/` and pages; review public assets in `frontend/public/` and `frontend/index.html`. |
| Languages | Edit `frontend/src/locales/{en,ar}/translation.json` and `src/lib/i18n.ts`; review `useDirection.ts`, fonts and logical CSS in `src/index.css` when adding a direction. Test both directions. |
| Colors/theme | Edit `frontend/tailwind.config.cjs`, `src/index.css` and `src/stores/uiStore.ts`; check light/dark contrast. |
| Domain | Set `PUBLIC_ORIGIN` for self-hosting or `CORS_ORIGINS` and Pages `API_ORIGIN` for split infrastructure. Keep the browser on one public origin for SPA and `/api/*`. Use HTTPS and new `EDGE_PROXY_SECRET` in production. |
| Database | Set a new `DATABASE_URL` and separate `_test` `TEST_DATABASE_URL`; migrate with Alembic. Add project tables with new migrations; do not edit released revisions. |
| Roles | `backend/app/core/seed.py` seeds baseline roles. Add project roles and guards deliberately; review `app/api/deps.py`, admin role-change policy, frontend role labels and tests. Frontend guards are UX only. |
| First administrator | Run the one-off `python -m app.core.seed --bootstrap-admin` with temporary unique credentials after migration/role seed, before exposing registration. Remove the bootstrap password afterward. |
| Integrations | Leave provider selectors disabled until needed. Configure credentials in private environment variables and follow [integrations](INTEGRATIONS.md) for handler, quotas and data-policy requirements. |
| Deployment | Use the bundled self-hosted Compose stack or Cloudflare Pages plus a container host. Follow [deployment](DEPLOYMENT_STRATEGY.md), including TLS, WAF/edge limits and live smoke tests. |

Review the license, footer, privacy/data retention needs and project-specific threat model before presenting a clone as a finished product. Do not copy example secrets or local development settings into production.
