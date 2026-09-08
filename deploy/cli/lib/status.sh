#!/usr/bin/env bash
# status.sh — observability: версия, состояние сервисов, profiles, последняя
# ошибка (SPEC-HUB-0019 §29). Installation-status (NEW/READY/…) — этап 2.

cmd_status() {
  local inst rel applied target
  inst="$(instance_dir)"
  rel="$(release_dir)"
  target="$(env_get "$(release_env_file)" CHATBALLS_VERSION)"
  applied="$(env_get "$(_state_file)" applied_version)"

  if [[ "$CHATBALLS_JSON" == "1" ]]; then
    printf '{"status":"info","instance":%s,"release_dir":%s,"target_version":%s,"applied_version":%s}\n' \
      "$(json_escape "$inst")" "$(json_escape "$rel")" \
      "$(json_escape "${target:-unknown}")" "$(json_escape "${applied:-none}")"
    return 0
  fi

  printf 'Chatballs status\n'
  printf '  instance dir: %s\n' "$inst"
  printf '  release dir: %s\n' "$rel"
  printf '  target version:  %s\n' "${target:-unknown}"
  printf '  applied version: %s\n' "${applied:-none}"
  printf '  profiles: %s\n' "${COMPOSE_PROFILES:-none}"

  if [[ -f "$(_state_file)" ]]; then
    printf '  last applied at: %s\n' "$(env_get "$(_state_file)" applied_at)"
  else
    printf '  last applied at: (none)\n'
  fi

  if docker info >/dev/null 2>&1; then
    printf '\nServices:\n'
    run_compose ps 2>/dev/null || log_warn "compose ps failed (not deployed yet?)"
  else
    printf '\nServices: (docker daemon not reachable)\n'
  fi
}

_state_file() { printf '%s/applied_release' "$(state_dir)"; }
