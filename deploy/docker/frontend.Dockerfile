FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json tsconfig.base.json ./
COPY apps/internal-ui/package.json ./apps/internal-ui/package.json
COPY apps/web-chat/package.json ./apps/web-chat/package.json
COPY packages/ui/package.json ./packages/ui/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/shared/package.json ./packages/shared/package.json
RUN npm ci

COPY apps/internal-ui ./apps/internal-ui
COPY apps/web-chat ./apps/web-chat
COPY packages ./packages

# Build-time домен не привязывается (ADR-HUB-0028 §10): один образ работает на любом
# домене; сниппет/WS/API выводятся от текущего origin в рантайме.
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm --workspace @chatballs/internal-ui run build
RUN npm --workspace @chatballs/web-chat run build

FROM nginx:1.27-alpine

COPY deploy/nginx/frontend.production.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/internal-ui/dist /usr/share/nginx/html
COPY --from=builder /app/apps/web-chat/dist /usr/share/nginx/html/chat

EXPOSE 80
