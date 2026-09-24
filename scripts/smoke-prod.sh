#!/usr/bin/env bash
# Smoke-test a running docker-compose.prod.yml stack (CI and local).
# Usage: scripts/smoke-prod.sh [env-file]   (default deploy/production.env)
set -euo pipefail

env_file="${1:-deploy/production.env}"
compose=(docker compose --env-file "$env_file" -f docker-compose.prod.yml)
base="http://127.0.0.1:${WEB_PORT:-8080}"
fail() { echo "FAIL: $*" >&2; exit 1; }

curl -fsS "$base/healthz" >/dev/null || fail "web healthz"
curl -fsS "$base/api/v1/health" | grep -q '"environment":"production"' || fail "API health via proxy"
curl -fsS "$base/api/v1/ready" | grep -q '"database":"connected"' || fail "readiness via proxy"
curl -fsS "$base/admin/users" | grep -q '<div id="root">' || fail "SPA fallback"
curl -fsS -D - -o /dev/null "$base/api/v1/health" | grep -qi '^cache-control: no-store' || fail "API no-store"

email="smoke-$RANDOM$RANDOM@example.com"
password="Smoke-check-password-$RANDOM!"
curl -fsS -o /dev/null -H 'Content-Type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"$password\",\"full_name\":\"Smoke\"}" \
  "$base/api/v1/auth/register" || fail "register"
headers=$(curl -fsS -D - -o /dev/null -H 'Content-Type: application/json' \
  -H 'X-Forwarded-For: 6.6.6.6' \
  -d "{\"email\":\"$email\",\"password\":\"$password\"}" "$base/api/v1/auth/login") || fail "login"
[ "$(grep -ci '^set-cookie:' <<<"$headers")" -eq 2 ] || fail "two Set-Cookie headers"
grep -i '^set-cookie: access_token=' <<<"$headers" | grep -qi 'httponly' || fail "HttpOnly"
grep -i '^set-cookie: access_token=' <<<"$headers" | grep -qi 'secure' || fail "Secure"
access=$(grep -i '^set-cookie: access_token=' <<<"$headers" | sed -E 's/^[Ss]et-[Cc]ookie: (access_token=[^;]+).*/\1/')
curl -fsS -H "Cookie: $access" "$base/api/v1/users/me" | grep -q "$email" || fail "/users/me via proxy"

# Bypassing the proxy must be refused; liveness stays open for platform checks.
"${compose[@]}" exec -T web sh -c \
  'wget -S -qO- http://api:8000/api/v1/users/me 2>&1 | grep -q "403 Forbidden"' || fail "bypass not refused"
"${compose[@]}" exec -T web sh -c 'wget -qO- http://api:8000/api/v1/health >/dev/null' || fail "liveness"

[ "$("${compose[@]}" exec -T api id -u | tr -d '\r')" = "10001" ] || fail "api not uid 10001"
[ "$("${compose[@]}" exec -T web id -u | tr -d '\r')" = "101" ] || fail "web not uid 101"
if "${compose[@]}" exec -T api sh -c 'touch /app/app/x' 2>/dev/null; then fail "api filesystem writable"; fi

echo "production smoke test passed"
