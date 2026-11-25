# Очистка локальных образов официальных релизов после успешного запуска стека.

updater_manifest_images() {
  awk '$1 == "image:" { print $2 }' "$@"
}

updater_project_image_ids() (
  containers=$(docker container ls --all --quiet \
    --filter "label=com.docker.compose.project=$PROJECT") || return 1
  [ -n "$containers" ] || return 1
  # ls --quiet выдаёт только идентификаторы, по одному на строку.
  docker container inspect --format '{{.Image}}' $containers
)

updater_retained_images() (
  # Версию определяет образ запущенного updater. Манифест на диске может
  # отставать от контейнеров после неудачного обновления или ручного запуска.
  prefix="ghcr.io/$REPO/updater:"
  case "$SELF_IMAGE" in
    "$prefix"*@sha256:*) previous=${SELF_IMAGE#"$prefix"}; previous=${previous%%@*} ;;
    *) return 1 ;;
  esac
  case "$previous" in
    ''|*[!0-9A-Za-z.-]*|"$VERSION") return 1 ;;
  esac

  # При переезде основного файла у updater может остаться скачанный манифест.
  previous_file=""
  for manifest in "${CHATBALLS_PREVIOUS_COMPOSE:-}" "$DIR/compose.$previous.yaml"; do
    [ -f "$manifest" ] && [ -r "$manifest" ] || continue
    previous_images=$(updater_manifest_images "$manifest") || continue
    if printf '%s\n' "$previous_images" | grep -Fxq -- "$SELF_IMAGE"; then
      previous_file=$manifest
      break
    fi
  done
  [ -n "$previous_file" ] || return 1

  # Сохраняем как официальные образы, так и образы после применения overrides.
  previous_effective=$(FILE="$previous_file" compose --profile '*' config --images) || return 1
  current_effective=$(compose --profile '*' config --images) || return 1
  current_images=$(updater_manifest_images "$FILE") || return 1
  previous_containers=$(updater_project_image_ids) || return 1
  printf '%s\n' "$previous" "$previous_images" "$current_images" \
    "$previous_effective" "$current_effective" "$previous_containers"
)

updater_cleanup_images() (
  retained=$1
  previous=$(printf '%s\n' "$retained" | head -n 1)
  history=$(updater_manifest_images "$DIR"/compose.*.yaml) || return 1
  # Полный список позволяет увидеть чужие теги, ссылающиеся на тот же ID.
  inventory=$(docker image ls --all --digests --no-trunc \
    --format '{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}}') || return 1
  candidates=$(
    {
      printf '%s\n' "$retained" | sed '1d; s/^/keep /'
      printf '%s\n' "$history" | sed 's/^/history /'
      printf '%s\n' "$inventory" | sed 's/^/image /'
    } | LC_ALL=C awk -v root="ghcr.io/$REPO/" -v previous="$previous" -v current="$VERSION" \
      -f "$(dirname "$0")/chatballs-updater-images.awk"
  ) || return 1

  failed=0
  for image_id in $candidates; do
    containers=$(docker container ls --all --quiet --filter "ancestor=$image_id") || return 1
    [ -z "$containers" ] || continue
    # По неизменяемому ID, без force и без рекурсивного удаления родителей.
    # Docker повторно проверяет ссылки контейнеров при самом удалении.
    if ! docker image rm --no-prune "$image_id" >>"$LOG" 2>&1; then
      failed=1
    fi
  done
  return "$failed"
)
