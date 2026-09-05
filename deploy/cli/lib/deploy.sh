#!/usr/bin/env bash
# deploy.sh — canonical deployment workflow (ADR-HUB-0028 / SPEC-HUB-0019).

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
  [[ -f "$(instance_env_file)" ]] || { log_err "instance .env missing"; return 1; }
  [[ -f "$(release_env_file)" ]] || { log_err "release.env missing"; return 1; }

  verify_release_checksums || return 1
  validate_release_image_refs || return 1

  local app_domain platform_domain
  app_domain="$(env_get "$(instance_env_file)" CHATBALLS_APP_DOMAIN)"
  platform_domain="$(env_get "$(instance_env_file)" CHATBALLS_PLATFORM_DOMAIN)"
  [[ -n "$app_domain" ]] || { log_err "CHATBALLS_APP_DOMAIN not set"; return 1; }
  [[ -n "$platform_domain" ]] || { log_err "CHATBALLS_PLATFORM_DOMAIN not set"; return 1; }
  [[ "$app_domain" != "$platform_domain" ]] || {
    log_err "app and platform domains must be distinct"
    return 1
  }

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
  local env_file pg_user pg_db
  env_file="$(instance_env_file)"
  pg_user="$(env_get "$env_file" POSTGRES_USER)"
  pg_db="$(env_get "$env_file" POSTGRES_DB)"
  [[ -n "$pg_user" ]] || { log_err "POSTGRES_USER not set"; return 1; }
  [[ -n "$pg_db" ]] || { log_err "POSTGRES_DB not set"; return 1; }
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
  local app_domain platform_domain
  app_domain="$(env_get "$(instance_env_file)" CHATBALLS_APP_DOMAIN)"
  platform_domain="$(env_get "$(instance_env_file)" CHATBALLS_PLATFORM_DOMAIN)"

  run_compose exec -T backend-app python - <<'PY' >/dev/null 2>&1 || {
import os
import urllib.error
import urllib.request

app_domain = os.environ["CHATBALLS_APP_DOMAIN"]
platform_domain = os.environ["CHATBALLS_PLATFORM_DOMAIN"]
app_health_host = os.environ.get("CHATBALLS_APP_HEALTHCHECK_HOST") or app_domain
platform_health_host = os.environ.get("CHATBALLS_PLATFORM_HEALTHCHECK_HOST") or platform_domain
app_health_request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/health/ready/",
    headers={"Host": app_health_host, "X-Forwarded-Proto": "https"},
)
with urllib.request.urlopen(app_health_request, timeout=5) as response:
    assert response.status == 200

platform_health_request = urllib.request.Request(
    "http://backend-platform:8000/api/v1/health/ready/",
    headers={"Host": platform_health_host, "X-Forwarded-Proto": "https"},
)
with urllib.request.urlopen(platform_health_request, timeout=5) as response:
    assert response.status == 200

with urllib.request.urlopen("http://frontend/", timeout=5) as response:
    assert response.status == 200

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None

opener = urllib.request.build_opener(NoRedirect)
for domain in (app_domain, platform_domain):
    gateway_request = urllib.request.Request("http://gateway/", headers={"Host": domain})
    try:
        opener.open(gateway_request, timeout=5)
    except urllib.error.HTTPError as error:
        assert error.code in {301, 302, 303, 307, 308}
        assert error.headers.get("Location", "").startswith(f"https://{domain}")
    else:
        raise AssertionError(f"gateway did not redirect HTTP to HTTPS for {domain}")
PY
    log_err "smoke: internal app/platform/frontend/gateway checks failed"
    return 1
  }
  log_ok "smoke: app, platform, frontend and gateway"

  if command -v curl >/dev/null 2>&1; then
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
