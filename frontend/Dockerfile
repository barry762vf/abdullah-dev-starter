# Production web image: static SPA plus the same-origin /api/* proxy (ADR 011/014).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# Runs as the unprivileged nginx user (uid 101) on port 8080.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
ENV NGINX_ENVSUBST_FILTER="^(API_UPSTREAM|EDGE_PROXY_SECRET)$"
COPY --chmod=0755 nginx/10-require-proxy-config.sh /docker-entrypoint.d/10-require-proxy-config.sh
COPY nginx/templates /etc/nginx/templates
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
