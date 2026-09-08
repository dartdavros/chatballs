#!/usr/bin/env bash
# compose.sh — canonical Docker Compose invocation for a release + instance pair.
# Release files remain immutable; runtime data stays in INSTANCE_DIR.

run_compose() {
  local inst rel
  inst="$(instance_dir)"
  rel="$(release_dir)"
  # Переменных окружения продукт не требует: compose поднимается со значениями
  # по умолчанию, всё остальное человек задаёт в интерфейсе. Единственный
  # env-файл — release.env: в нём digest-пины образов, которые ставит CI.
  (
    cd "$inst" || exit 1
    docker compose \
      --project-directory "$inst" \
      --env-file "$rel/release.env" \
      -f "$rel/compose.yaml" \
      "$@"
  )
}

compose_config_validate() {
  run_compose config -q
}

profile_enabled() {
  local p="$1" profiles
  profiles="${COMPOSE_PROFILES:-}"
  [[ ",$profiles," == *",$p,"* ]]
}
