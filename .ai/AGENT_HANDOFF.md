# Agent handoff — Abdullah Developer Kit v1.0.0

> State: stable reusable baseline · Phases 0–8 complete · architecture frozen · v1.0.0 published

## Release verification

- `main` is clean and tracks `origin/main`; release-preparation code commit `14598e9` passed all three GitHub workflows: [backend-ci](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155712) (136 tests, 95% coverage, migration drift), [frontend-ci](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155774), and [containers](https://github.com/barry762vf/abdullah-dev-starter/actions/runs/35978155862) (healthy production stack, smoke script).
- Local backend: 91 unit tests, 136 full PostgreSQL tests at 95%, Ruff lint/format, pip check and guarded Alembic drift passed. Frontend: 54 tests, 97.91% line/statement and 90.51% branch coverage, typecheck, ESLint and production build passed. `npm ci --dry-run` passed.
- No confirmed high/critical application issue remains. Known accepted risks: npm BUG-013 (8 full-tree advisories; 2 moderate in production dependencies), old backend direct pins/no Python vulnerability scanner, and historic personal context in earlier public commits. No credentials were found in the current tree.
- Annotated tag `v1.0.0` is pushed to commit `462a5bb`; the public [GitHub release](https://github.com/barry762vf/abdullah-dev-starter/releases/tag/v1.0.0) is published from `docs/RELEASE_NOTES_v1.0.0.md`. GitHub is public with template mode enabled. Optional providers and Cloudflare/Railway live behavior remain deployment-specific. The security scan plugin did not start its Python helper; manual security review and repository tests were used.

## Frozen architecture and version policy

v1 freezes FastAPI, PostgreSQL/SQLAlchemy/Alembic, auth/refresh rotation, RBAC, administration, React/Vite/TypeScript, Arabic/English RTL/LTR, tests, Docker/CI, same-origin production proxies, optional provider slots and `.ai/` handoffs. Bug fixes are patch releases (`1.0.x`); compatible reusable improvements are minor releases (`1.x.0`); breaking architecture changes are major releases (`2.0.0`). Product-specific features belong in clones. See `.ai/DECISIONS.md` ADR 016 and `docs/ARCHITECTURE.md`.

## Exact next action

For a new product, use GitHub **Use this template**, clone the new repository, follow the root README quickstart, and customize it using `docs/CUSTOMIZATION.md`. Keep product-specific work in that clone; do not start another implementation phase in the starter.
