#!/usr/bin/env bash
# Миграция существующей установки CustoCRM/hub → Chatballs (2026-09-05).
#
# Что переименовывается на работающей БД (данные не трогаются):
#   • роли Postgres: custocrm_bootstrap/app/platform/migration → chatballs_*,
#     групповые custocrm_runtime_app / custocrm_runtime_platform / custocrm_schema → chatballs_*;
#   • схема custocrm (функции RLS, directory-view) → chatballs; GUC custocrm.organization_id → chatballs.organization_id;
#   • база edevs_hub → chatballs;
#   • .env: ключи CUS_* и CUSTOCRM_* → CHATBALLS_*, COMPOSE_PROJECT_NAME, POSTGRES_DB, имена ролей;
#   • compose-проект: старые контейнеры/сеть удаляются, данные в bind-mount ${INSTANCE_DIR}/data остаются на месте.
#
# Запуск из каталога релиза (где compose.yaml), инстанс — каталог с .env и data/:
#   CHATBALLS_INSTANCE_DIR=/opt/chatballs/instance deploy/migrate/rename-to-chatballs.sh
# Для dev-стека: CHATBALLS_COMPOSE_ARGS="-f compose.dev.yaml" …
#
# На проде перед запуском: mv /opt/custocrm /opt/chatballs (каталог релизов и инстанса).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RELEASE_DIR="${CHATBALLS_RELEASE_DIR:-${CUSTOCRM_RELEASE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}}"
INSTANCE_DIR="${CHATBALLS_INSTANCE_DIR:-${CUSTOCRM_INSTANCE_DIR:-$PWD}}"
ENV_FILE="$INSTANCE_DIR/.env"
COMPOSE_ARGS="${CHATBALLS_COMPOSE_ARGS:-}"

log() { printf '[chatballs migrate] %s\n' "$*" >&2; }
die() { printf '[chatballs migrate] ERROR: %s\n' "$*" >&2; exit 1; }
env_get() { grep -E "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2- || true; }

[[ -f "$ENV_FILE" ]] || die ".env не найден: $ENV_FILE"
[[ -f "$RELEASE_DIR/compose.yaml" ]] || die "compose.yaml не найден в $RELEASE_DIR"

# --- 1. Старые значения ------------------------------------------------------
OLD_PROJECT="$(env_get COMPOSE_PROJECT_NAME)"; OLD_PROJECT="${OLD_PROJECT:-edevs_hub}"
OLD_DB="$(env_get POSTGRES_DB)"; OLD_DB="${OLD_DB:-edevs_hub}"
OLD_SUPER="$(env_get POSTGRES_USER)"; OLD_SUPER="${OLD_SUPER:-custocrm_bootstrap}"
SUPER_PW="$(env_get POSTGRES_PASSWORD)"
OLD_APP="$(env_get POSTGRES_APP_USER)"; APP_PW="$(env_get POSTGRES_APP_PASSWORD)"
OLD_PLATFORM="$(env_get POSTGRES_PLATFORM_USER)"; PLATFORM_PW="$(env_get POSTGRES_PLATFORM_PASSWORD)"
OLD_MIGRATION="$(env_get POSTGRES_MIGRATION_USER)"; MIGRATION_PW="$(env_get POSTGRES_MIGRATION_PASSWORD)"
[[ -n "$SUPER_PW" && -n "$APP_PW" && -n "$PLATFORM_PW" && -n "$MIGRATION_PW" ]] || die "в .env нет паролей Postgres"

rename_value() { printf '%s' "$1" | sed -e 's/^custocrm_/chatballs_/'; }
NEW_SUPER="$(rename_value "$OLD_SUPER")"
NEW_APP="$(rename_value "$OLD_APP")"
NEW_PLATFORM="$(rename_value "$OLD_PLATFORM")"
NEW_MIGRATION="$(rename_value "$OLD_MIGRATION")"
NEW_DB="chatballs"; [[ "$OLD_DB" == "edevs_hub" || "$OLD_DB" == "custocrm" ]] || NEW_DB="$OLD_DB"

if grep -qE '^(CUS_|CUSTOCRM_)' "$ENV_FILE" || [[ "$OLD_PROJECT" != "chatballs" ]]; then
  log "старый проект: $OLD_PROJECT · база: $OLD_DB · суперпользователь: $OLD_SUPER"
else
  log ".env уже переименован — повторный запуск"
fi

# --- 2. Остановить старый стек (bind-mount data/ остаётся) --------------------
log "останавливаю compose-проект $OLD_PROJECT"
docker compose -p "$OLD_PROJECT" ls >/dev/null 2>&1 || true
docker ps -aq --filter "label=com.docker.compose.project=$OLD_PROJECT" | xargs -r docker rm -f >/dev/null
docker network ls -q --filter "label=com.docker.compose.project=$OLD_PROJECT" | xargs -r docker network rm >/dev/null 2>&1 || true

# --- 3. Переписать .env --------------------------------------------------------
cp "$ENV_FILE" "$ENV_FILE.bak-custocrm"
log "переписываю .env (резервная копия: $ENV_FILE.bak-custocrm)"
PY_BIN="$(command -v python3 >/dev/null 2>&1 && python3 -c "print(1)" >/dev/null 2>&1 && echo python3 || echo python)"
"$PY_BIN" - "$ENV_FILE" "$NEW_DB" "$NEW_SUPER" "$NEW_APP" "$NEW_PLATFORM" "$NEW_MIGRATION" <<'PY'
import re, sys
path, new_db, new_super, new_app, new_platform, new_migration = sys.argv[1:]
values = {"COMPOSE_PROJECT_NAME": "chatballs", "POSTGRES_DB": new_db, "POSTGRES_USER": new_super,
          "POSTGRES_APP_USER": new_app, "POSTGRES_PLATFORM_USER": new_platform, "POSTGRES_MIGRATION_USER": new_migration}
out = []
for line in open(path, encoding="utf-8").read().splitlines():
    line = re.sub(r"^(#\s*)?(CUSTOCRM_|CUS_)", lambda m: (m.group(1) or "") + "CHATBALLS_", line)
    m = re.match(r"^([A-Z_]+)=", line)
    if m and m.group(1) in values:
        line = f"{m.group(1)}={values[m.group(1)]}"
    out.append(line)
open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
PY

compose() { docker compose -f "$RELEASE_DIR/compose.yaml" $COMPOSE_ARGS --env-file "$ENV_FILE" "$@"; }
psql_as() { # user db
  compose exec -T -e PGPASSWORD="$SUPER_PW" postgres psql -v ON_ERROR_STOP=1 -qAt -U "$1" -d "$2"
}

# --- 5. Поднять только Postgres нового проекта ---------------------------------
log "поднимаю postgres (проект chatballs)"
compose up -d postgres >/dev/null
for _ in $(seq 1 60); do
  compose exec -T postgres pg_isready -U "$OLD_SUPER" -d postgres >/dev/null 2>&1 && break
  sleep 1
done
compose exec -T postgres pg_isready -U "$OLD_SUPER" -d postgres >/dev/null || die "postgres не поднялся"

role_exists() { psql_as "$1" postgres <<<"SELECT 1 FROM pg_roles WHERE rolname = '$2'" | grep -q 1; }
rename_role() { # who old new
  if [[ "$2" != "$3" ]] && role_exists "$1" "$2"; then
    log "роль $2 → $3"; psql_as "$1" postgres <<<"ALTER ROLE $2 RENAME TO $3;"
  fi
}

# --- 6. Суперпользователь initdb владеет системными объектами — его нельзя пересоздать,
# только переименовать из-под временной роли (свою сессионную роль переименовать нельзя).
TMP_SUPER="chatballs_migrator_tmp"
if [[ "$OLD_SUPER" != "$NEW_SUPER" ]] && role_exists "$OLD_SUPER" "$OLD_SUPER"; then
  log "переименовываю суперпользователя $OLD_SUPER → $NEW_SUPER"
  psql_as "$OLD_SUPER" postgres <<SQL
DROP ROLE IF EXISTS $TMP_SUPER;
CREATE ROLE $TMP_SUPER SUPERUSER LOGIN PASSWORD '$SUPER_PW';
SQL
  psql_as "$TMP_SUPER" postgres <<SQL
ALTER ROLE $OLD_SUPER RENAME TO $NEW_SUPER;
ALTER ROLE $NEW_SUPER PASSWORD '$SUPER_PW';
SQL
  psql_as "$NEW_SUPER" postgres <<<"DROP ROLE $TMP_SUPER;"
fi
SUPER="$NEW_SUPER"

# --- 7. Роли, база, схема -------------------------------------------------------
rename_role "$SUPER" "$OLD_APP" "$NEW_APP"
rename_role "$SUPER" "$OLD_PLATFORM" "$NEW_PLATFORM"
rename_role "$SUPER" "$OLD_MIGRATION" "$NEW_MIGRATION"
rename_role "$SUPER" custocrm_runtime_app chatballs_runtime_app
rename_role "$SUPER" custocrm_runtime_platform chatballs_runtime_platform
rename_role "$SUPER" custocrm_schema chatballs_schema
# Переименование сбрасывает MD5-пароли — задаём заново из .env (SCRAM оно не трогает, но так надёжнее).
psql_as "$SUPER" postgres <<SQL
ALTER ROLE $NEW_APP PASSWORD '$APP_PW';
ALTER ROLE $NEW_PLATFORM PASSWORD '$PLATFORM_PW';
ALTER ROLE $NEW_MIGRATION PASSWORD '$MIGRATION_PW';
SQL

if [[ "$OLD_DB" != "$NEW_DB" ]] && psql_as "$SUPER" postgres <<<"SELECT 1 FROM pg_database WHERE datname = '$OLD_DB'" | grep -q 1; then
  log "база $OLD_DB → $NEW_DB"
  psql_as "$SUPER" postgres <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$OLD_DB' AND pid <> pg_backend_pid();
ALTER DATABASE $OLD_DB RENAME TO $NEW_DB;
SQL
fi

if psql_as "$SUPER" "$NEW_DB" <<<"SELECT 1 FROM pg_namespace WHERE nspname = 'custocrm'" | grep -q 1; then
  log "схема custocrm → chatballs, функция RLS на новый GUC"
  psql_as "$SUPER" "$NEW_DB" <<'SQL'
ALTER SCHEMA custocrm RENAME TO chatballs;
CREATE OR REPLACE FUNCTION chatballs.current_organization_id() RETURNS bigint
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN current_setting('chatballs.organization_id', true) ~ '^[1-9][0-9]*$'
        THEN current_setting('chatballs.organization_id', true)::bigint
        ELSE NULL
    END
$$;
SQL
fi

# --- 8. Проверка -----------------------------------------------------------------
psql_as "$SUPER" "$NEW_DB" <<'SQL' | sed 's/^/[chatballs migrate]   /' >&2
SELECT 'roles: ' || string_agg(rolname, ', ' ORDER BY rolname) FROM pg_roles WHERE rolname LIKE 'chatballs%';
SELECT 'schema chatballs: ' || count(*) || ' objects' FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'chatballs';
SELECT 'leftovers custocrm: ' || count(*) FROM pg_roles WHERE rolname LIKE 'custocrm%';
SQL

log "готово. Дальше: docker compose up (dev) или chatballs deploy (prod)."
log "Пользователям потребуется войти заново — имена cookie сессии изменились."
