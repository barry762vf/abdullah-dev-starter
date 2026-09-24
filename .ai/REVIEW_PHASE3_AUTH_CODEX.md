# Codex verification of the Phase 3 independent security audit

> Date: 2026-09-24
> Source: `.ai/REVIEW_PHASE3_AUTH_CLAUDE.md` (preserved unchanged)
> Scope: Phase 4 authentication integration readiness; no Phase 4 implementation.

The findings below were checked against the committed Phase 3 code and current ADRs. The original audit remains available for its full evidence and all 11 LOW items.

| Finding | Classification | Independent evidence | Decision |
| :--- | :--- | :--- | :--- |
| HIGH-01, concurrent refresh | **CONFIRMED behavior; EXPECTED DESIGN TRADEOFF** | `auth_service.refresh` consumes a digest with conditional `UPDATE ... RETURNING`. The live two-connection test gets one success and one 401; the second request's known-reuse branch revokes the successor. ADR 009 expressly excludes a grace window. | No backend replay relaxation. `docs/AUTH_STRATEGY.md` now defines in-tab single-flight, same-origin Web Lock serialization, `/users/me` probe before one refresh, state-only BroadcastChannel messages, network-error handling, logout coordination, and a safe no-Web-Locks fallback. |
| HIGH-02, BUG-008 hosting | **CONFIRMED** | `auth.py` sets HttpOnly host-only SameSite=Lax cookies. Cross-site fetch from a default Pages hostname to a Railway hostname omits Lax cookies. | ADR 011 chooses one browser-facing origin, relative `/api/v1`, and a Cloudflare Pages `/api/*` proxy to Railway. Local Vite uses the same route. BUG-008 closes at the architecture level; the proxy must still be built/tested before deployment. |
| MEDIUM-01, event-loop Argon2 | **CONFIRMED** | Registration, login and admin bootstrap previously called synchronous Argon2 inside async functions. | `hash_password_async` and `verify_password_async` use AnyIO worker threads with a two-operation capacity limiter. Registration, login (including dummy hash), and bootstrap use them. Argon2 parameters are unchanged. |
| MEDIUM-02, forwarded-IP trust | **CONFIRMED** | Installed Uvicorn 0.34.2 defaults to `proxy_headers=True`, `forwarded_allow_ips=127.0.0.1`. A direct middleware probe showed loopback peer + `X-Forwarded-For: 6.6.6.6` becomes `6.6.6.6`; nontrusted `172.18.0.5` stays that peer. | Local launch instructions now use `--no-proxy-headers`. Production requires exact trusted ingress IPs, proxy header overwrite, blocked direct bypass, and audit-IP smoke test. If stable trust cannot be established, use edge limiting and do not claim app-level client-IP accuracy. This is a Phase 7 deployment gate, not an app route fix. |
| MEDIUM-03, IP rotation and key churn | **CONFIRMED, bounded starter tradeoff** | An independent probe got 429 after five attempts, then allowed the same IP after 4,096 other keys evicted it. The implementation has per-IP keys only; IPv6 rotation and multi-worker bypass remain. | Documented as best-effort local control. Shared/edge and account-aware abuse controls are Phase 7 work; no CAPTCHA, Redis or fingerprinting was added in this checkpoint. It does not block Phase 4 local integration. |
| MEDIUM-04, default development mode | **CONFIRMED** | `Settings.environment` had a `development` default, so missing `ENVIRONMENT` skipped key/cookie/debug/HTTPS-origin guards. | The field is now required; missing mode fails validation. `.env.example` and tests explicitly set development. Production deployment must explicitly set and verify production; copying the development template unchanged remains an operational risk. |

## LOW item dispositions

- Addressed for Phase 4: LOW-01 documented the 15-minute Bearer JWT lifetime after logout and required client-cache clearing; LOW-02 added bootstrap-before-public-registration guidance; LOW-06 unified token and cookie lifetime constants; LOW-08 added a JSON-only public-auth regression test; LOW-09 is reduced by the same-origin topology; LOW-10 and LOW-11 are documented API behavior.
- Deferred with scope: LOW-03 bootstrap outcome and disabled-admin recovery; LOW-04 potential future misuse of `get_current_user`; LOW-05 richer audit reason codes and untrusted user-agent display; LOW-07 rehash policy and Unicode password normalization. Test gaps in the original audit beyond the focused changes remain in `.ai/TODO.md` for the relevant phase.

## Readiness

Phase 4 shell is unblocked. Local frontend authentication integration is unblocked **if** it implements the documented refresh contract and relative `/api/v1` URL with a Vite `/api` proxy. Production deployment is not yet approved: the edge proxy, trusted ingress, real-client-IP behavior, and stronger/shared rate limiting require implementation and live verification in Phase 4/7.
