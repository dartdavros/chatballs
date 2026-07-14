#!/usr/bin/env bash
# doctor.sh — read-only pre-flight checks before deployment.

cmd_doctor() {
  local failures=0 inst rel
  inst="$(instance_dir)"
  rel="$(release_dir)"

  _doctor_report() {
    local ok="$1"
    shift
    local msg="$*"
    if [[ "$ok" == "1" ]]; then
      [[ "$CUSTOCRM_JSON" == "1" ]] || log_ok "$msg"
    else
      [[ "$CUSTOCRM_JSON" == "1" ]] || log_err "$msg"
      failures=$((failures + 1))
    fi
  }

  require_cmd docker
  _doctor_report 1 "docker found"
  require_cmd flock
  _doctor_report 1 "flock found"

  if command -v sha256sum >/dev/null 2>&1; then
    _doctor_report 1 "sha256sum found"
  else
    _doctor_report 0 "sha256sum missing"
  fi

  if docker info >/dev/null 2>&1; then
    _doctor_report 1 "docker daemon reachable"
  else
    _doctor_report 0 "docker daemon not reachable"
  fi

  if docker compose version >/dev/null 2>&1; then
    _doctor_report 1 "docker compose plugin available"
  else
    _doctor_report 0 "docker compose plugin missing"
  fi

  local arch
  arch="$(uname -m 2>/dev/null || echo unknown)"
  if [[ "$arch" == "x86_64" ]]; then
    _doctor_report 1 "host arch x86_64"
  else
    _doctor_report 0 "unsupported host arch: $arch (target: x86_64)"
  fi

  if [[ -d "$inst" ]] && [[ -w "$inst" ]]; then
    _doctor_report 1 "instance dir writable: $inst"
  else
    _doctor_report 0 "instance dir not writable: $inst"
  fi

  if [[ -f "$(compose_file)" ]]; then
    _doctor_report 1 "compose.yaml present in release: $rel"
  else
    _doctor_report 0 "compose.yaml missing in release: $rel"
  fi

  if [[ -f "$(instance_env_file)" ]]; then
    _doctor_report 1 "instance .env present"
  else
    _doctor_report 0 "instance .env missing: $(instance_env_file)"
  fi

  if [[ -f "$(release_env_file)" ]]; then
    _doctor_report 1 "release.env present"
  else
    _doctor_report 0 "release.env missing: $(release_env_file)"
  fi

  if verify_release_checksums; then
    _doctor_report 1 "release checksums valid"
  else
    _doctor_report 0 "release checksums invalid"
  fi

  if validate_release_image_refs; then
    _doctor_report 1 "release image references are immutable"
  else
    _doctor_report 0 "release image references are invalid"
  fi

  local domain
  domain="$(env_get "$(instance_env_file)" CUSTOCRM_DOMAIN)"
  if [[ -n "$domain" ]]; then
    _doctor_report 1 "CUSTOCRM_DOMAIN set: $domain"
  else
    _doctor_report 0 "CUSTOCRM_DOMAIN not set"
  fi

  local pg_pwd
  pg_pwd="$(env_get "$(instance_env_file)" POSTGRES_PASSWORD)"
  if [[ -n "$pg_pwd" ]]; then
    _doctor_report 1 "POSTGRES_PASSWORD set"
  else
    _doctor_report 0 "POSTGRES_PASSWORD empty"
  fi

  local secret
  secret="$(env_get "$(instance_env_file)" HUB_SECRET_KEY)"
  if [[ -n "$secret" ]] && [[ "$secret" != "change-me-long-random-secret" ]]; then
    _doctor_report 1 "HUB_SECRET_KEY set"
  else
    _doctor_report 0 "HUB_SECRET_KEY default/empty"
  fi

  if profile_enabled calls; then
    local missing=0 k
    for k in HUB_CALL_TURN_SECRET HUB_CALL_TURN_REALM HUB_TURN_EXTERNAL_IP HUB_TURN_LISTENING_IP; do
      if [[ -z "$(env_get "$(instance_env_file)" "$k")" ]]; then
        _doctor_report 0 "$k required for calls profile"
        missing=1
      fi
    done
    if [[ "$missing" == "0" ]] && validate_calls_network_boundary; then
      _doctor_report 1 "calls profile network boundary valid"
    else
      _doctor_report 0 "calls profile network boundary invalid"
    fi
  fi

  if { [[ -d "$inst/backups" ]] && [[ -w "$inst/backups" ]]; } || [[ -w "$inst" ]]; then
    _doctor_report 1 "backup dir available"
  else
    _doctor_report 0 "backup dir not creatable: $inst/backups"
  fi

  if compose_config_validate >/dev/null 2>&1; then
    _doctor_report 1 "compose config valid"
  else
    _doctor_report 0 "compose config invalid"
  fi

  if [[ "$failures" != "0" ]]; then
    die "doctor: $failures check(s) failed" 1
  fi

  if [[ "$CUSTOCRM_JSON" == "1" ]]; then
    printf '{"status":"ok","checks":"passed"}\n'
  else
    log_ok "doctor: all checks passed"
  fi
}
