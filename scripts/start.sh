#!/usr/bin/env sh
# Локальный запуск Chatballs из исходников (Linux/macOS).
#
# Это путь разработчика: стек собирается из репозитория. Установка продукта
# выглядит иначе и этого скрипта не требует — там один compose.yaml со
# страницы релиза и `docker compose up -d --wait` (см. README).
#
# Ни одной переменной задавать не нужно и негде: .env у продукта нет. Секреты
# инстанса генерирует первый старт (сервис secrets), всё остальное —
# организацию, владельца, домены, почту, интеграции — человек настраивает в UI.
#
# Режим поставки: --mode cloud (по умолчанию) или --mode self-hosted.
set -eu

cd "$(dirname "$0")/.."

mode="CLOUD"
while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      shift
      case "${1:-}" in
        cloud|CLOUD) mode="CLOUD" ;;
        self-hosted|SELF_HOSTED|selfhosted) mode="SELF_HOSTED" ;;
        *) echo "Неизвестный режим: ${1:-}. Допустимо: cloud, self-hosted" >&2; exit 2 ;;
      esac
      shift
      ;;
    -h|--help)
      echo "Использование: $0 [--mode cloud|self-hosted]" >&2
      exit 0
      ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 2 ;;
  esac
done

echo "Сборка из исходников, режим поставки: $mode."
CHATBALLS_DELIVERY_MODE="$mode" \
  exec docker compose -f compose.yaml -f compose.dev.yaml up --build
