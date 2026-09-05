#!/usr/bin/env sh
# Локальный запуск Chatbolls (Linux/macOS): canonical compose.yaml + dev override.
# Параметры не нужны: владельца и демо-данные создаёт мастер первого запуска
# в браузере (http://localhost). Режим поставки: ./scripts/start.sh [cloud|self-hosted]
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

MODE="${1:-cloud}"
case "$MODE" in
  cloud) export CUS_DELIVERY_MODE=CLOUD ;;
  self-hosted) export CUS_DELIVERY_MODE=SELF_HOSTED ;;
  *) echo "usage: $0 [cloud|self-hosted]" >&2; exit 2 ;;
esac

exec docker compose -f compose.yaml -f compose.dev.yaml --env-file .env.example --env-file .env up --build
