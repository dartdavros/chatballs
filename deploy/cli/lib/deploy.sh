#!/usr/bin/env bash
# deploy.sh — canonical deployment workflow (ADR-CHATBALLS-0028 / SPEC-CHATBALLS-0019).

cmd_deploy() {
  ensure_instance_dirs
  acquire_lock
  trap release_lock EXIT

  log "deploy: validating release and instance config"
  _deploy_validate || die "deploy: validation failed" 1

  log "deploy: pulling immutable images"
  run_compose pull || die "deploy: image pull failed" 1

  log "deploy: starting infrastructure (postgres, redis)"
  run_compose up -d postgres redis || die "deploy: infrastructure start failed" 1
  _wait_healthy postgres 60 || die "deploy: postgres did not become healthy" 1
  _wait_healthy redis 30 || die "deploy: redis did not become healthy" 1

  log "deploy: normalizing schema ownership for migrations"
  _normalize_schema_ownership || die "deploy: schema ownership normalization failed" 1

  log "deploy: running one-shot init (migrate)"
  run_compose run --rm init || die "deploy: init (migrate) failed" 1

  log "deploy: starting application services"
  local app_services=(backend-app backend-platform backend-admin worker frontend gateway)
  if profile_enabled calls; then
    app_services+=(coturn)
  fi
  run_compose up -d "${app_services[@]}" || die "deploy: application start failed" 1

  log "deploy: waiting for application health"
  _wait_healthy backend-app 90 || die "deploy: app backend did not become healthy" 1
  _wait_healthy backend-platform 90 || die "deploy: platform backend did not become healthy" 1
  _wait_running backend-admin 30 || die "deploy: admin backend did not start" 1
  _wait_running frontend 30 || die "deploy: frontend did not start" 1
  _wait_running gateway 30 || die "deploy: gateway did not start" 1
  if profile_enabled calls; then
    _wait_healthy coturn 60 || die "deploy: coturn did not become healthy" 1
  fi

  log "deploy: running smoke checks"
  _smoke || die "deploy: smoke checks failed" 1

  _record_release
  log_ok "deploy: complete (release: $(_applied_version_target))"
}

_deploy_validate() {
  [[ -f "$(compose_file)" ]] || { log_err "compose.yaml missing"; return 1; }
  [[ -f "$(release_env_file)" ]] || { log_err "release.env missing"; return 1; }

  verify_release_checksums || return 1
  validate_release_image_refs || return 1

  # Домены здесь не проверяются: установка отвечает по адресу сервера, а свой
  # домен владелец задаёт в «Настройках» — снаружи его знать неоткуда.

  if profile_enabled calls; then
    validate_calls_network_boundary || return 1
  fi

  compose_config_validate >/dev/null 2>&1 || {
    log_err "compose config invalid"
    return 1
  }
}

_wait_healthy() {
  local svc="$1" timeout="$2" waited=0 state
  while [[ "$waited" -lt "$timeout" ]]; do
    state="$(run_compose ps --format json "$svc" 2>/dev/null | _first_json_service_state)"
    [[ "$state" == "healthy" ]] && return 0
    sleep 3
    waited=$((waited + 3))
  done
  return 1
}

_wait_running() {
  local svc="$1" timeout="$2" waited=0 state
  while [[ "$waited" -lt "$timeout" ]]; do
    state="$(run_compose ps --format json "$svc" 2>/dev/null | _first_json_service_state)"
    case "$state" in
      healthy|running|Up*) return 0 ;;
    esac
    sleep 3
    waited=$((waited + 3))
  done
  return 1
}

_normalize_schema_ownership() {
  # Приводит владение объектов public-схемы к роли chatballs_schema, в которую
  # входит migration-user. Идемпотентно: безопасно на каждом деплое. Без этого
  # миграции от migration-user падают на таблицах, созданных не им
  # («must be owner of table …»). Выполняется под суперпользователем POSTGRES_USER.
  # Те же значения по умолчанию, что и у compose: задавать их человеку негде
  # и незачем. Раньше они читались из .env — и без него deploy падал здесь,
  # хотя сама установка была исправна.
  local pg_user pg_db
  pg_user="${POSTGRES_USER:-chatballs_bootstrap}"
  pg_db="${POSTGRES_DB:-chatballs}"
  run_compose exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U "$pg_user" -d "$pg_db" \
    -f /chatballs-reassign-ownership.sql >/dev/null
}

_first_json_service_state() {
  local line
  IFS= read -r line || return 0
  if [[ $line =~ \"Health\":\"([^\"]*)\" ]] && [[ -n "${BASH_REMATCH[1]}" ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  elif [[ $line =~ \"State\":\"([^\"]*)\" ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  elif [[ $line =~ \"Status\":\"([^\"]*)\" ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  fi
}

_smoke() {
  # Установка домена не знает — он задаётся в «Настройках». Проверяем её так
  # же, как её открывает человек до этого: по адресу сервера, без https.
  local app_domain platform_domain
  app_domain="localhost"
  platform_domain="localhost"

  # Значения передаём через env внутри контейнера, а не флагами -e: так
  # команда остаётся привычной формы «exec -T backend-app …».
  run_compose exec -T backend-app \
    env SMOKE_APP_HOST="$app_domain" SMOKE_PLATFORM_HOST="$platform_domain" \
    python - <<'PY' >/dev/null 2>&1 || {
import os
import urllib.request

app_host = os.environ["SMOKE_APP_HOST"]
platform_host = os.environ["SMOKE_PLATFORM_HOST"]

app_health = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/health/ready/",
    headers={"Host": app_host},
)
with urllib.request.urlopen(app_health, timeout=5) as response:
    assert response.status == 200

platform_health = urllib.request.Request(
    "http://backend-platform:8000/api/v1/health/ready/",
    headers={"Host": platform_host},
)
with urllib.request.urlopen(platform_health, timeout=5) as response:
    assert response.status == 200

with urllib.request.urlopen("http://frontend/", timeout=5) as response:
    assert response.status == 200

# Шлюз обязан отвечать по http на любом адресе: домена и сертификата у свежей
# установки нет, а человек открывает её сразу после docker compose up.
gateway = urllib.request.Request("http://gateway/", headers={"Host": app_host})
with urllib.request.urlopen(gateway, timeout=5) as response:
    assert response.status == 200
PY
    log_err "smoke: internal app/platform/frontend/gateway checks failed"
    return 1
  }
  log_ok "smoke: app, platform, frontend and gateway"

  # Публичные https-адреса проверяем, только если домен задан: у свежей
  # установки его нет, и «недоступен» здесь ничего не значит.
  if [[ "$app_domain" != "localhost" ]] && command -v curl >/dev/null 2>&1; then
    local app_code platform_code
    app_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$app_domain/" 2>/dev/null || true)"
    platform_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$platform_domain/api/v1/health/live/" 2>/dev/null || true)"
    if [[ "$app_code" =~ ^(200|30[12378])$ ]] && [[ "$platform_code" == "200" ]]; then
      log_ok "smoke: public app and platform HTTPS endpoints"
    else
      log_warn "smoke: public HTTPS endpoints are not reachable yet (app $app_code, platform $platform_code)"
    fi
  fi
}

_state_file() { printf '%s/applied_release' "$(state_dir)"; }

_record_release() {
  local ver
  ver="$(env_get "$(release_env_file)" CHATBALLS_VERSION)"
  printf 'applied_version=%s\napplied_at=%s\n' "${ver:-unknown}" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)" > "$(_state_file)"
}

_applied_version_target() {
  env_get "$(release_env_file)" CHATBALLS_VERSION || printf 'unknown'
}
