#!/usr/bin/env bash
# common.sh — shared helpers for the Chatballs deployment CLI.

CHATBALLS_NON_INTERACTIVE=0
CHATBALLS_JSON=0

log() { printf '[chatballs] %s\n' "$*" >&2; }
log_ok() { printf '[chatballs] OK: %s\n' "$*" >&2; }
log_warn() { printf '[chatballs] WARN: %s\n' "$*" >&2; }
log_err() { printf '[chatballs] ERROR: %s\n' "$*" >&2; }

die() {
  local msg="$1"
  local code="${2:-1}"
  if [[ "$CHATBALLS_JSON" == "1" ]]; then
    printf '{"status":"error","error":%s}\n' "$(json_escape "$msg")"
  else
    log_err "$msg"
  fi
  exit "$code"
}

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '"%s"' "$s"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1" 2
}

release_dir() {
  printf '%s' "${CHATBALLS_RELEASE_DIR:?CHATBALLS_RELEASE_DIR is not set}"
}

instance_dir() {
  printf '%s' "${CHATBALLS_INSTANCE_DIR:?CHATBALLS_INSTANCE_DIR is not set}"
}

release_env_file() { printf '%s/release.env' "$(release_dir)"; }
release_checksums_file() { printf '%s/checksums.txt' "$(release_dir)"; }
compose_file() { printf '%s/compose.yaml' "$(release_dir)"; }
state_dir() { printf '%s/state' "$(instance_dir)"; }
data_dir() { printf '%s/data' "$(instance_dir)"; }

ensure_instance_dirs() {
  local d
  for d in "$(instance_dir)" "$(state_dir)" "$(data_dir)" \
           "$(instance_dir)/backups" "$(instance_dir)/logs"; do
    mkdir -p "$d" || die "cannot create directory: $d"
  done
}

LOCK_FD=9
acquire_lock() {
  local lock_file
  lock_file="$(state_dir)/deploy.lock"
  exec 9>"$lock_file" || die "cannot open lock file: $lock_file"
  if ! flock -n 9; then
    die "another operation is in progress (lock held): $lock_file" 3
  fi
}

release_lock() {
  flock -u 9 2>/dev/null || true
  exec 9>&- 2>/dev/null || true
}

env_get() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 0
  awk -F= -v k="$key" '$1==k && $0 !~ /^#/ {sub(/^[^=]*=/,""); print; exit}' "$file"
}

verify_release_checksums() {
  local checksums
  checksums="$(release_checksums_file)"
  [[ -f "$checksums" ]] || {
    log_err "release checksums missing: $checksums"
    return 1
  }
  command -v sha256sum >/dev/null 2>&1 || {
    log_err "required command not found: sha256sum"
    return 1
  }
  (
    cd "$(release_dir)" || exit 1
    sha256sum -c checksums.txt >/dev/null
  ) || {
    log_err "release checksum verification failed"
    return 1
  }
}

validate_calls_network_boundary() {
  # Профиль calls включают переменной окружения — тем же способом, каким её
  # читает сам compose. Файла с конфигурацией у установки нет.
  local web_ip turn_ip
  web_ip="${CHATBALLS_WEB_LISTENING_IP:-}"
  turn_ip="${CHATBALLS_TURN_LISTENING_IP:-}"

  [[ -n "$web_ip" ]] || {
    log_err "CHATBALLS_WEB_LISTENING_IP is required for calls profile"
    return 1
  }
  [[ "$web_ip" != "0.0.0.0" ]] || {
    log_err "CHATBALLS_WEB_LISTENING_IP cannot be 0.0.0.0 when calls profile uses TURN TLS on 443"
    return 1
  }
  [[ "$web_ip" != "$turn_ip" ]] || {
    log_err "web and TURN listeners must use different public IP addresses"
    return 1
  }
}

release_image_keys() {
  printf '%s\n' \
    CHATBALLS_BACKEND_IMAGE \
    CHATBALLS_FRONTEND_IMAGE \
    CHATBALLS_POSTGRES_IMAGE \
    CHATBALLS_REDIS_IMAGE \
    CHATBALLS_GATEWAY_IMAGE \
    CHATBALLS_COTURN_IMAGE
}

validate_release_image_refs() {
  local key ref failed=0
  while IFS= read -r key; do
    ref="$(env_get "$(release_env_file)" "$key")"
    if [[ ! "$ref" =~ @sha256:[0-9a-fA-F]{64}$ ]]; then
      log_err "$key must be an immutable @sha256 reference"
      failed=1
    fi
  done < <(release_image_keys)
  [[ "$failed" == "0" ]]
}
