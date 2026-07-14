#!/usr/bin/env bash
# compose.sh — canonical Docker Compose invocation for a release + instance pair.
# Release files remain immutable; runtime data and .env stay in INSTANCE_DIR.

run_compose() {
  local inst rel
  inst="$(instance_dir)"
  rel="$(release_dir)"
  (
    cd "$inst" || exit 1
    docker compose \
      --project-directory "$inst" \
      --env-file "$inst/.env" \
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
  profiles="$(env_get "$(instance_env_file)" COMPOSE_PROFILES)"
  [[ ",$profiles," == *",$p,"* ]]
}
