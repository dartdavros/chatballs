FROM node:22-alpine

WORKDIR /app

COPY package.json tsconfig.base.json ./
COPY apps/internal-ui/package.json ./apps/internal-ui/package.json
COPY packages/ui/package.json ./packages/ui/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/shared/package.json ./packages/shared/package.json
RUN npm install

COPY apps/internal-ui ./apps/internal-ui
COPY packages ./packages

WORKDIR /app/apps/internal-ui
EXPOSE 5173
