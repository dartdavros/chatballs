#!/bin/sh
set -eu

: "${POSTGRES_APP_USER:?POSTGRES_APP_USER is required}"
: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD is required}"
: "${POSTGRES_PLATFORM_USER:?POSTGRES_PLATFORM_USER is required}"
: "${POSTGRES_PLATFORM_PASSWORD:?POSTGRES_PLATFORM_PASSWORD is required}"
: "${POSTGRES_MIGRATION_USER:?POSTGRES_MIGRATION_USER is required}"
: "${POSTGRES_MIGRATION_PASSWORD:?POSTGRES_MIGRATION_PASSWORD is required}"

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_user="$POSTGRES_APP_USER" \
  --set=app_password="$POSTGRES_APP_PASSWORD" \
  --set=platform_user="$POSTGRES_PLATFORM_USER" \
  --set=platform_password="$POSTGRES_PLATFORM_PASSWORD" \
  --set=migration_user="$POSTGRES_MIGRATION_USER" \
  --set=migration_password="$POSTGRES_MIGRATION_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

SELECT 'CREATE ROLE custocrm_runtime_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'custocrm_runtime_app')
\gexec
SELECT 'CREATE ROLE custocrm_runtime_platform NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'custocrm_runtime_platform')
\gexec
SELECT 'CREATE ROLE custocrm_schema NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'custocrm_schema')
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

SELECT format('GRANT custocrm_runtime_app TO %I', :'app_user') \gexec
SELECT format('GRANT custocrm_runtime_platform TO %I', :'platform_user') \gexec
SELECT format('GRANT custocrm_schema TO %I', :'migration_user') \gexec
-- C04 RLS: runtime_app/platform must also be members of custocrm_schema so the
-- permissive custocrm_schema_access policy (USING/WITH CHECK true, created by
-- tenancy.0003 on every tenant table) applies to them. Without this membership
-- the schema_access policy does not cover the login roles, leaving only the
-- tenant_isolation / audit-insert policies, which do not OR to true for
-- cross-tenant writes (e.g. login-failed audit with organization_id IS NULL)
-- and block the write with "violates row-level security policy".
SELECT format('GRANT custocrm_schema TO custocrm_runtime_app') \gexec
SELECT format('GRANT custocrm_schema TO custocrm_runtime_platform') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'platform_user') \gexec
SELECT format('GRANT CONNECT, CREATE, TEMPORARY ON DATABASE %I TO %I', current_database(), :'migration_user') \gexec
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'migration_user') \gexec
GRANT USAGE, CREATE ON SCHEMA public TO custocrm_schema;
SQL
