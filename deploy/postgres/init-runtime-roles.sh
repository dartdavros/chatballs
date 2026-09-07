#!/bin/sh
set -eu

# Пароли ролей приходят файлами из тома секретов (их генерирует первый старт
# стека), либо переменными — для установок, которые ведут конфигурацию сами.
read_secret() {
  var="$1"; file_var="${1}_FILE"
  eval "value=\${$var:-}"
  if [ -n "$value" ]; then printf %s "$value"; return 0; fi
  eval "file=\${$file_var:-}"
  if [ -n "$file" ] && [ -s "$file" ]; then cat "$file"; return 0; fi
  echo "$var or $file_var is required" >&2
  exit 1
}

: "${POSTGRES_APP_USER:?POSTGRES_APP_USER is required}"
: "${POSTGRES_PLATFORM_USER:?POSTGRES_PLATFORM_USER is required}"
: "${POSTGRES_MIGRATION_USER:?POSTGRES_MIGRATION_USER is required}"
POSTGRES_APP_PASSWORD="$(read_secret POSTGRES_APP_PASSWORD)"
POSTGRES_PLATFORM_PASSWORD="$(read_secret POSTGRES_PLATFORM_PASSWORD)"
POSTGRES_MIGRATION_PASSWORD="$(read_secret POSTGRES_MIGRATION_PASSWORD)"

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_user="$POSTGRES_APP_USER" \
  --set=app_password="$POSTGRES_APP_PASSWORD" \
  --set=platform_user="$POSTGRES_PLATFORM_USER" \
  --set=platform_password="$POSTGRES_PLATFORM_PASSWORD" \
  --set=migration_user="$POSTGRES_MIGRATION_USER" \
  --set=migration_password="$POSTGRES_MIGRATION_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

SELECT 'CREATE ROLE chatballs_runtime_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_runtime_app')
\gexec
SELECT 'CREATE ROLE chatballs_runtime_platform NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_runtime_platform')
\gexec
SELECT 'CREATE ROLE chatballs_schema NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatballs_schema')
\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS', :'platform_user', :'platform_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'platform_user')
\gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS', :'migration_user', :'migration_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migration_user')
\gexec

SELECT format('GRANT chatballs_runtime_app TO %I', :'app_user') \gexec
SELECT format('GRANT chatballs_runtime_platform TO %I', :'platform_user') \gexec
SELECT format('GRANT chatballs_schema TO %I', :'migration_user') \gexec
-- Runtime roles must not inherit the permissive chatballs_schema_access policy:
-- membership in the schema-owner role would bypass tenant RLS entirely.
REVOKE chatballs_schema FROM chatballs_runtime_app, chatballs_runtime_platform;
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'platform_user') \gexec
SELECT format('GRANT CONNECT, CREATE, TEMPORARY ON DATABASE %I TO %I', current_database(), :'migration_user') \gexec
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'migration_user') \gexec
GRANT USAGE, CREATE ON SCHEMA public TO chatballs_schema;
SQL
