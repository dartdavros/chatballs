#!/usr/bin/env bash
# logs.sh — обёртка над `docker compose logs` с фильтром сервиса.

cmd_logs() {
  local svc=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--follow) shift; ;;
      *) svc="$1"; shift; ;;
    esac
  done

  if [[ -n "$svc" ]]; then
    run_compose logs --tail=200 "$svc" || die "logs: service not found or not running: $svc" 1
  else
    run_compose logs --tail=200 || die "logs: cannot fetch logs (not deployed yet?)" 1
  fi
}
