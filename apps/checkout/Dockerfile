FROM node:22-alpine

WORKDIR /app

COPY package.json tsconfig.base.json ./
COPY apps/checkout/package.json ./apps/checkout/package.json
COPY packages/ui/package.json ./packages/ui/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/shared/package.json ./packages/shared/package.json
RUN npm install

COPY apps/checkout ./apps/checkout
COPY packages ./packages

WORKDIR /app/apps/checkout
EXPOSE 5174
