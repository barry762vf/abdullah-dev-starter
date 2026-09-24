# AI Agent Handoff — Phase 4 frontend shell complete

> From: Claude Code (took over Phase 4 from Codex after Codex reached its usage limit)
> Date: 2026-09-24
> Status: Phases 0–4 complete and verified. Phase 5 administration is next; no Phase 5 code was added.

## 1. State at takeover

`main` was at `e5327a2` (Phase 3 audit fixes), tracking `origin/main`. Codex's Phase 4 work was entirely **uncommitted**: an untracked `frontend/` plus edits to `.ai/*`, `README.md`, `.gitignore`, `SECOND_BRAIN_HANDOFF.md`, `docs/AUTH_STRATEGY.md` and `docs/FOLDER_STRUCTURE.md`. Codex's handoff said the work was "a separate commit"; it was not. All of Codex's work was preserved.

Codex had completed nearly every roadmap item:
- React 18 + Vite 5 + TypeScript static SPA; Tailwind 3 with logical utilities; Cairo/Inter with system fallbacks.
- i18next English/Arabic with root `lang`/`dir` switching and persistence.
- Shell: `AppShell`, `Navbar`, `Sidebar`, `LanguageToggle`, `ThemeToggle`; loading/error/empty/not-found states.
- Routes: `/`, `/login`, `/register`, a guarded `/dashboard`, and a catch-all.
- Relative `/api/v1` Axios client with RFC 7807 errors and the ADR 011 refresh coordinator.
- Vite `/api` proxy; 17 Vitest tests.

## 2. What Claude completed and changed

Every change is a small correction inside Codex's design; there is no redesign.

| Change | Why |
| :--- | :--- |
| `lib/api.ts`: `login`/`logout` now emit `auth-updated`/`signed-out` **inside** the Web Lock | A new test showed a refresh queued behind logout acquired the lock before `signed-out` was emitted, so it ran `/users/me` and `/auth/refresh` against the contract in `docs/AUTH_STRATEGY.md`. The logout response has already cleared the refresh cookie, so the stray refresh would get a plain 401, not trigger reuse revocation; still a contract violation. |
| `lib/api.ts`: 20 s timeout on `authTransport` only | A hung session request could hold the cross-tab lock indefinitely. A timed-out refresh follows the existing ambiguous-failure path and is never retried. |
| `lib/i18n.ts` sets root `lang`/`dir` at module load; `useDirection` and the theme class use `useLayoutEffect` | Previously `useEffect` ran after paint, so Arabic users saw one LTR frame (and dark-mode users one light frame). |
| `Sidebar.tsx`: mobile drawer is a real modal dialog | Verified in the browser: focus stayed behind the overlay, Escape did nothing, no dialog semantics. Now `role="dialog"`, `aria-modal`, focus moves to Close, Tab stays inside, Escape closes, focus returns to the menu button. The menu button has `aria-expanded`/`aria-controls`. |
| `LanguageToggle.tsx`: accessible name is "Language: العربية" and the label carries `lang` | `aria-label="Language"` hid the visible label (WCAG 2.5.3 label-in-name) and screen readers had no language hint for the Arabic word. `index.css` renders inline `[lang]` text in Cairo or Inter. |
| `Navbar.tsx`: sign-in/sign-out arrow icons mirror in RTL; header is `relative`, so the sign-out error sits under it | Directional icons pointed the wrong way in Arabic; the alert was positioned relative to the page. |
| Login status messages travel as translation keys (`messageKey`), allowlisted | A translated string in router state stayed in the old language after a switch. |
| Registration: client check for >128-character passwords; server 422 shows a specific "details not accepted" message | The generic "try again" message was misleading for input the user can fix. A live `.test` email (rejected by the backend's email validator) exposed this. |
| `StatePanel` `headingLevel`; the not-found page uses an `h1` | The page previously had no `h1`. |
| Tests: 8 added, 1 updated | See §4. The updated test used the old language-button accessible name. |

`docs/AUTH_STRATEGY.md` gained one sentence on in-lock signals and the timeout. No backend code, cookies or ADR 009 refresh rules were changed.

## 3. Status by area

- **Stack:** React 18, Vite 5, TypeScript, Tailwind 3, i18next/react-i18next, React Router 6, TanStack Query, Zustand. Static SPA, as in ADR 002.
- **Routing:**
  - Public: `/`. Auth: `/login`, `/register`. Protected: `/dashboard` behind `AuthGuard`. Not found: `*`.
  - Role-gated routes and `RoleGuard` are Phase 5. The nested-layout structure accepts them without change.
  - Guards are UX only; the backend remains authoritative.
- **i18n:**
  - English and Arabic dictionaries have identical key sets.
  - Runtime switching needs no reload. The saved language is applied before first render.
- **RTL/LTR:**
  - One stylesheet with logical utilities (`start-`, `end-`, `border-e`, `-end-16`, `rtl:-scale-x-100`); no physical left/right classes.
  - Email and password inputs stay `dir="ltr"`.
- **Language persistence:** the `abdullah-kit-language` localStorage key. The only other storage key is `abdullah-kit-theme`.
- **API client:**
  - Relative `/api/v1`; no hostname or environment URL.
  - JSON, `X-Requested-With`, cookie credentials, RFC 7807 → `ApiError`.
  - No token in any JavaScript-accessible storage.
- **Vite proxy:** `/api` → `127.0.0.1:8000`, verified live (below). The production Pages `/api/*` proxy is **not** implemented; it is a Phase 7 gate under ADR 011.
- **Refresh coordination:** fully implemented per ADR 011 and `docs/AUTH_STRATEGY.md`:
  - in-tab single-flight;
  - Web Lock `abdullah-auth-session` shared by refresh, login and logout;
  - `/users/me` probe under the lock and at most one refresh;
  - BroadcastChannel carrying only `auth-updated`, `signed-out` and `refresh-uncertain`;
  - a queued refresh aborts after an observed sign-out;
  - no retry after an ambiguous failure or timeout;
  - without Web Locks, re-login is required.

## 4. Verification (exact commands and results)

**Frontend** (from `frontend/`, Node 26.0.0, npm 11.12.1):
- `npm run test`: **25 passed** (2 files).
- `npm run typecheck`: exit 0.
- `npm run lint`: exit 0.
- `npm run build`: passed (Vite 5; `dist/` is ignored).
- `npm audit --audit-level=high`: 7 advisories (5 moderate, 1 high, 1 critical), unchanged from Codex's run (BUG-013).
- `npm audit --omit=dev --audit-level=high`: exit 0, with 2 moderate Router advisories.

The 8 new tests cover:
- the saved Arabic `dir` applied at i18n load;
- mobile dialog focus, Tab containment and Escape;
- the login message following a language switch;
- the password over 128 characters;
- the 422 message;
- one lock name across login, refresh and logout, and a queued refresh aborting after logout (this test failed before the fix);
- one retry of the original request, with `/auth/*` never intercepted;
- state-only broadcasts plus the auth timeout.

**Backend** (from `backend/`; Docker PostgreSQL was restarted for this):
- `pytest -q`: **43 passed**. Backend code was untouched; run as a regression check.
- `ruff check .`: passed.

**Live browser checks** (built-in browser; Vite dev server plus a local FastAPI):
- **Proxy:** `/api/v1/health` returned 200 JSON through Vite; `/users/me` returned a 401 `application/problem+json` response.
- **End-to-end:** FastAPI ran with `DATABASE_URL` set to the guarded `abdullah_core_test`. The run went register → login (dashboard "Welcome back, Browser Check.") → `/users/me` 200 → `POST /auth/refresh` 200 → `/users/me` 200 → navbar logout (back to `/login`) → `/users/me` 401 → refresh 401.
  - `document.cookie` was empty throughout (HttpOnly).
  - Storage keys were only language and theme.
  - The test user was deleted afterwards; the test database has 0 users.
  - The development database was not touched.
- **Layout, measured (overflow, sidebar side, control order, fonts) and screenshotted:**
  - English LTR and Arabic RTL at 1440 px desktop, 768 px tablet and 375 px mobile.
  - No horizontal overflow at any width.
  - Sidebar and drawer on the left in LTR, on the right in RTL; header controls mirror.
  - Headings use Cairo in Arabic and Inter in English.
  - Dark theme checked on mobile English.

## 5. Unresolved issues

- **BUG-013:** npm advisories in the ADR 002 major versions (Vite 5 / Vitest 2 / React Router 6). Not a Phase 4 blocker; review before shared or public use.
- **BUG-009 / BUG-010:** production client-IP trust and shared/edge rate limiting remain deployment gates.
- The Cloudflare Pages `/api/*` edge proxy is not built (Phase 7).
- Google Fonts is loaded from a third-party CDN. A future production CSP must allow it, or the fonts must be self-hosted.

## 6. Git

One Phase 4 commit on `main` (see `git log`), pushed normally to `origin/main` if authentication was available. No force-push, no history rewrite. `node_modules/`, `dist/`, `*.tsbuildinfo` and `.env` are ignored and untracked.

## 7. Exact next task

Implement **Phase 5 administration only** per `docs/DEVELOPMENT_ROADMAP.md`:
- Backend `/api/v1/admin/users`, `/stats` and `/audit-logs` behind `require_role`, with server-side authorization tests.
- A frontend `RoleGuard` (UX only), admin dashboard, user table and audit viewer, reusing the Phase 4 API client, `StatePanel` and bilingual patterns.
- Render audit user agents as plain text.

Do not start Phase 6/7 or deployment work.
