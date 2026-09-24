#!/bin/sh
# Fail closed before templates render: the proxy must authenticate itself to the API.
set -eu
if [ ! -w /etc/nginx/conf.d ]; then
    # Otherwise the template step only logs an error and nginx starts without the proxy config.
    echo "/etc/nginx/conf.d must be writable by the nginx user (uid 101)" >&2
    exit 1
fi
if [ -z "${API_UPSTREAM:-}" ]; then
    echo "API_UPSTREAM is required (for example http://api:8000)" >&2
    exit 1
fi
if [ "${#EDGE_PROXY_SECRET}" -lt 32 ]; then
    echo "EDGE_PROXY_SECRET must be set to at least 32 characters" >&2
    exit 1
fi
