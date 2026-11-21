# syntax=docker/dockerfile:1

FROM node:24-slim

# Prevent telemetry and suppress non-essential npm overhead
ENV NEXT_TELEMETRY_DISABLED=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

WORKDIR /app/frontend

COPY frontend/package*.json ./

# Install dependencies fast: no audit, no funding messages, use cache if available
RUN --mount=type=cache,id=npm-cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY frontend/ ./

RUN --mount=type=cache,id=next-cache,target=/app/frontend/.next/cache \
    npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
