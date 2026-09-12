#!/bin/sh
# Сервис updater: обновление установки по кнопке из интерфейса (ADR-CHATBALLS-0049).
#
# Приложение не имеет доступа к Docker и не может перезапустить само себя:
# оно кладёт запрос в том chatballs-updates, а этот сервис — единственный,
# у кого смонтирован docker.sock, — забирает запрос, проверяет его и запускает
# `docker compose pull && up` для всего проекта.
#
# Запрос принимается только на официальный релиз: версия проверяется по
# формату, compose.yaml скачивается только со страницы релизов репозитория
# продукта, а все образы в нём обязаны быть закреплены по digest. Больше
# ничего этот сервис делать не умеет, что бы ни лежало в запросе.
#
# Сам сервис тоже входит в проект и пересоздаётся при обновлении, поэтому
# работу выполняет отдельный контейнер вне проекта (chatballs-updater-apply.sh):
# он переживает пересоздание и дописывает статус в том до конца.
set -eu

DIR="${CHATBALLS_UPDATES_DIR:-/run/chatballs/updates}"
REPO="${CHATBALLS_UPDATE_REPO:-dartdavros/chatballs}"
POLL_SECONDS="${CHATBALLS_UPDATER_POLL_SECONDS:-5}"
SOCKET="/var/run/docker.sock"
REQUEST="$DIR/request.json"
STATUS="$DIR/status.json"
HEARTBEAT="$DIR/heartbeat"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) updater: $*"; }

write_status() {
  # $1 status, $2 version, $3 message
  message=$(printf '%s' "$3" | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-900)
  printf '{"status":"%s","version":"%s","message":"%s","at":"%s"}\n' \
    "$1" "$2" "$message" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATUS.tmp"
  mv "$STATUS.tmp" "$STATUS"
}

json_field() {
  # Значение строкового поля $2 из JSON-файла $1 (одна строка, без вложенности).
  sed -n 's/.*"'"$2"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" | head -1
}

mkdir -p "$DIR"
chmod 777 "$DIR"

if [ ! -S "$SOCKET" ]; then
  log "docker.sock не смонтирован — обновление из интерфейса недоступно"
  # Без сокета сервис бесполезен, но и падать в перезапусках незачем.
  while true; do sleep 3600; done
fi

# Имя проекта и рабочий каталог берутся из меток собственного контейнера:
# именно так их видит compose на хосте.
SELF_ID="$(cat /etc/hostname)"
PROJECT="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$SELF_ID" 2>/dev/null || true)"
WORKDIR="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$SELF_ID" 2>/dev/null || true)"
UPDATES_VOLUME="$(docker inspect -f '{{ range .Mounts }}{{ if eq .Destination "'"$DIR"'" }}{{ .Name }}{{ end }}{{ end }}' "$SELF_ID" 2>/dev/null || true)"
SELF_IMAGE="$(docker inspect -f '{{ .Config.Image }}' "$SELF_ID" 2>/dev/null || true)"
if [ -z "$PROJECT" ] || [ -z "$UPDATES_VOLUME" ] || [ -z "$SELF_IMAGE" ]; then
  log "не удалось определить проект compose по меткам контейнера (project=$PROJECT volume=$UPDATES_VOLUME image=$SELF_IMAGE)"
  while true; do sleep 3600; done
fi
log "готов: проект $PROJECT, каталог ${WORKDIR:-?}, том $UPDATES_VOLUME"

while true; do
  touch "$HEARTBEAT"
  if [ -f "$REQUEST" ]; then
    version="$(json_field "$REQUEST" version)"
    compose_url="$(json_field "$REQUEST" compose_url)"
    rm -f "$REQUEST"
    case "$version" in
      ''|*[!0-9A-Za-z.-]*) log "отклонён запрос с недопустимой версией: $version"; write_status failed "$version" "invalid version"; sleep "$POLL_SECONDS"; continue ;;
    esac
    expected="https://github.com/$REPO/releases/download/v$version/compose.yaml"
    if [ "$compose_url" != "$expected" ]; then
      log "отклонён запрос: адрес compose.yaml не со страницы релизов ($compose_url)"
      write_status failed "$version" "compose.yaml address is not the release page"
      sleep "$POLL_SECONDS"; continue
    fi
    if docker ps -q --filter "name=^chatballs-updater-apply$" | grep -q .; then
      log "установка уже идёт — запрос $version пропущен"
      sleep "$POLL_SECONDS"; continue
    fi
    log "установка $version: запуск"
    write_status running "$version" "starting"
    # Помощник вне проекта: свой образ, docker.sock и тот же том; переживает
    # пересоздание этого сервиса и дописывает статус до конца.
    if ! docker run -d --rm --name chatballs-updater-apply \
        -e CHATBALLS_UPDATE_REPO="$REPO" \
        -e CHATBALLS_PROJECT="$PROJECT" \
        -e CHATBALLS_WORKDIR="$WORKDIR" \
        -e CHATBALLS_UPDATES_VOLUME="$UPDATES_VOLUME" \
        -e CHATBALLS_UPDATER_IMAGE="$SELF_IMAGE" \
        -v "$SOCKET:$SOCKET" \
        -v "$UPDATES_VOLUME:$DIR" \
        "$SELF_IMAGE" chatballs-updater-apply.sh "$version" "$expected" >/dev/null 2>"$DIR/apply.err"; then
      write_status failed "$version" "could not start helper: $(cat "$DIR/apply.err" 2>/dev/null | tail -c 400)"
    fi
  fi
  sleep "$POLL_SECONDS"
done
