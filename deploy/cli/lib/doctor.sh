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
      [[ "$CHATBALLS_JSON" == "1" ]] || log_ok "$msg"
    else
      [[ "$CHATBALLS_JSON" == "1" ]] || log_err "$msg"
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

  # .env не требуется: продукт поднимается без переменных окружения.
  if [[ -f "$(instance_env_file)" ]]; then
    _doctor_report 1 "instance .env present (overrides)"
  else
    _doctor_report 1 "instance .env absent (not required)"
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

  local app_domain platform_domain
  app_domain="$(env_get "$(instance_env_file)" CHATBALLS_APP_DOMAIN)"
  platform_domain="$(env_get "$(instance_env_file)" CHATBALLS_PLATFORM_DOMAIN)"
  if [[ -n "$app_domain" ]]; then
    _doctor_report 1 "CHATBALLS_APP_DOMAIN set: $app_domain"
  else
    _doctor_report 0 "CHATBALLS_APP_DOMAIN not set"
  fi
  if [[ -n "$platform_domain" ]]; then
    _doctor_report 1 "CHATBALLS_PLATFORM_DOMAIN set: $platform_domain"
  else
    _doctor_report 0 "CHATBALLS_PLATFORM_DOMAIN not set"
  fi
  if [[ -n "$app_domain" ]] && [[ "$app_domain" != "$platform_domain" ]]; then
    _doctor_report 1 "app and platform domains are distinct"
  else
    _doctor_report 0 "app and platform domains must be distinct"
  fi

  local acme_email
  acme_email="$(env_get "$(instance_env_file)" CHATBALLS_ACME_EMAIL)"
  if [[ -n "$acme_email" ]]; then
    _doctor_report 1 "CHATBALLS_ACME_EMAIL set"
  else
    _doctor_report 0 "CHATBALLS_ACME_EMAIL not set"
  fi

  local pg_pwd
  pg_pwd="$(env_get "$(instance_env_file)" POSTGRES_PASSWORD)"
  if [[ -n "$pg_pwd" ]]; then
    _doctor_report 1 "POSTGRES_PASSWORD set"
  else
    _doctor_report 0 "POSTGRES_PASSWORD empty"
  fi

  local secret
  secret="$(env_get "$(instance_env_file)" CHATBALLS_SECRET_KEY)"
  if [[ -n "$secret" ]] && [[ "$secret" != "change-me-long-random-secret" ]]; then
    _doctor_report 1 "CHATBALLS_SECRET_KEY set"
  else
    _doctor_report 0 "CHATBALLS_SECRET_KEY default/empty"
  fi

  if profile_enabled calls; then
    local missing=0 k
    for k in CHATBALLS_CALL_TURN_SECRET CHATBALLS_CALL_TURN_REALM CHATBALLS_TURN_EXTERNAL_IP CHATBALLS_TURN_LISTENING_IP; do
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

  if [[ "$CHATBALLS_JSON" == "1" ]]; then
    printf '{"status":"ok","checks":"passed"}\n'
  else
    log_ok "doctor: all checks passed"
  fi
}
