FROM node:22-alpine

WORKDIR /app

COPY package.json tsconfig.base.json ./
COPY apps/web-chat/package.json ./apps/web-chat/package.json
COPY packages/ui/package.json ./packages/ui/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/shared/package.json ./packages/shared/package.json
RUN npm install

COPY apps/web-chat ./apps/web-chat
COPY packages ./packages

WORKDIR /app/apps/web-chat
EXPOSE 5175
