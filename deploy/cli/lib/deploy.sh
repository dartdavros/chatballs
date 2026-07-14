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

  log "deploy: running one-shot init (migrate)"
  run_compose run --rm init || die "deploy: init (migrate) failed" 1

  log "deploy: starting application services"
  local app_services=(backend worker frontend gateway)
  if profile_enabled calls; then
    app_services+=(coturn)
  fi
  run_compose up -d "${app_services[@]}" || die "deploy: application start failed" 1

  log "deploy: waiting for application health"
  _wait_healthy backend 90 || die "deploy: backend did not become healthy" 1
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

  local domain
  domain="$(env_get "$(instance_env_file)" CUSTOCRM_DOMAIN)"
  [[ -n "$domain" ]] || { log_err "CUSTOCRM_DOMAIN not set"; return 1; }

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
  local domain
  domain="$(env_get "$(instance_env_file)" CUSTOCRM_DOMAIN)"

  run_compose exec -T backend python - <<'PY' >/dev/null 2>&1 || {
import os
import urllib.error
import urllib.request

health_host = os.environ.get("HUB_HEALTHCHECK_HOST") or os.environ["CUSTOCRM_DOMAIN"]
health_request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/health/ready/",
    headers={"Host": health_host, "X-Forwarded-Proto": "https"},
)
with urllib.request.urlopen(health_request, timeout=5) as response:
    assert response.status == 200

with urllib.request.urlopen("http://frontend/", timeout=5) as response:
    assert response.status == 200

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None

opener = urllib.request.build_opener(NoRedirect)
domain = os.environ["CUSTOCRM_DOMAIN"]
gateway_request = urllib.request.Request("http://gateway/", headers={"Host": domain})
try:
    opener.open(gateway_request, timeout=5)
except urllib.error.HTTPError as error:
    assert error.code in {301, 302, 303, 307, 308}
    assert error.headers.get("Location", "").startswith(f"https://{domain}")
else:
    raise AssertionError("gateway did not redirect HTTP to HTTPS")
PY
    log_err "smoke: internal backend/frontend/gateway checks failed"
    return 1
  }
  log_ok "smoke: backend, frontend and gateway"

  if command -v curl >/dev/null 2>&1; then
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "https://$domain/" 2>/dev/null || true)"
    if [[ "$code" =~ ^(200|30[12378])$ ]]; then
      log_ok "smoke: public HTTPS endpoint"
    else
      log_warn "smoke: public HTTPS endpoint is not reachable yet (HTTP $code)"
    fi
  fi
}

_state_file() { printf '%s/applied_release' "$(state_dir)"; }

_record_release() {
  local ver
  ver="$(env_get "$(release_env_file)" CUSTOCRM_VERSION)"
  printf 'applied_version=%s\napplied_at=%s\n' "${ver:-unknown}" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)" > "$(_state_file)"
}

_applied_version_target() {
  env_get "$(release_env_file)" CUSTOCRM_VERSION || printf 'unknown'
}
