#!/bin/sh
# Помощник обновления: скачать релизный compose.yaml, проверить, применить.
# Запускается сервисом updater отдельным контейнером вне проекта compose, чтобы
# пережить пересоздание самого updater'а. Пишет статус в том chatballs-updates.
set -u

VERSION="${1:?version}"
COMPOSE_URL="${2:?compose url}"
DIR="${CHATBALLS_UPDATES_DIR:-/run/chatballs/updates}"
REPO="${CHATBALLS_UPDATE_REPO:?}"
PROJECT="${CHATBALLS_PROJECT:?}"
WORKDIR="${CHATBALLS_WORKDIR:-}"
OVERRIDE_FILES="${CHATBALLS_OVERRIDE_FILES:-}"
VOLUME="${CHATBALLS_UPDATES_VOLUME:?}"
SELF_IMAGE="${CHATBALLS_UPDATER_IMAGE:?}"
STATUS="$DIR/status.json"
LOG="$DIR/apply.log"
FILE="$DIR/compose.$VERSION.yaml"
. "$(dirname "$0")/chatballs-updater-compose.sh"
. "$(dirname "$0")/chatballs-updater-images.sh"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) apply $VERSION: $*" | tee -a "$LOG"; }

write_status() {
  message=$(printf '%s' "$2" | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-900)
  printf '{"status":"%s","version":"%s","message":"%s","at":"%s"}\n' \
    "$1" "$VERSION" "$message" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATUS.tmp"
  mv "$STATUS.tmp" "$STATUS"
}

fail() {
  log "ОШИБКА: $1"
  write_status failed "$1"
  exit 1
}

: > "$LOG"
write_status running "downloading"
log "скачивание $COMPOSE_URL"
if ! wget -q -T 60 -O "$FILE" "$COMPOSE_URL"; then
  fail "compose.yaml не скачался"
fi

# Файл релиза обязан ссылаться на образы только по digest и только из
# реестра продукта (свои образы) или из закреплённых сторонних (redis, coturn).
if grep -E '^\s*image:' "$FILE" | grep -vqE '@sha256:[0-9a-f]{64}'; then
  fail "в compose.yaml есть образ без digest"
fi
if grep -E '^\s*image:\s*ghcr\.io/' "$FILE" | grep -vq "ghcr.io/$REPO/"; then
  fail "в compose.yaml есть образ из чужого реестра"
fi

# Профиль звонков включён, если coturn уже работает в проекте.
PROFILE_ARGS=""
if docker ps -q --filter "label=com.docker.compose.project=$PROJECT" --filter "label=com.docker.compose.service=coturn" | grep -q .; then
  PROFILE_ARGS="--profile calls"
fi

if ! compose $PROFILE_ARGS config -q >>"$LOG" 2>&1; then
  fail "compose.yaml не прошёл проверку"
fi

retained_images=""
if ! retained_images=$(updater_retained_images 2>>"$LOG"); then
  log "очистка образов пропущена: не удалось определить образы двух релизов"
fi

write_status running "pulling"
log "загрузка образов"
if ! compose $PROFILE_ARGS pull >>"$LOG" 2>&1; then
  fail "не удалось загрузить образы: $(tail -n 3 "$LOG" | tr '\n' ' ')"
fi

write_status running "restarting"
log "перезапуск сервисов"
if ! compose $PROFILE_ARGS up -d --wait >>"$LOG" 2>&1; then
  fail "стек не поднялся: $(tail -n 3 "$LOG" | tr '\n' ' ')"
fi

# Файл на хосте должен соответствовать работающей версии: иначе следующий
# ручной `docker compose up` откатил бы установку.
if [ -n "$WORKDIR" ]; then
  # Входную точку образа подменяем: иначе вместо копирования запустится цикл
  # ожидания запросов, и контейнер никогда не завершится.
  if docker run --rm --entrypoint /bin/sh \
      -v "$WORKDIR:/host" -v "$VOLUME:/updates" "$SELF_IMAGE" \
      -c "cp /updates/compose.$VERSION.yaml /host/compose.yaml" >>"$LOG" 2>&1; then
    log "compose.yaml в $WORKDIR обновлён"
  else
    log "предупреждение: не удалось обновить compose.yaml в $WORKDIR"
    retained_images=""
  fi
fi

if [ -n "$retained_images" ] && ! updater_cleanup_images "$retained_images"; then
  log "предупреждение: очистка старых образов завершилась с ошибкой"
fi

write_status done "updated"
log "готово"
