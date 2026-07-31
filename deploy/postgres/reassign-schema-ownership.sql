-- Нормализация владельца объектов public-схемы под роль миграций.
--
-- Контекст: при раздельных ролях (custocrm_migration / custocrm_app /
-- custocrm_platform) Django-миграции от migration-user требуют, чтобы
-- выполняющий был ВЛАДЕЛЬЦЕМ изменяемой таблицы («must be owner of table …»).
-- Таблицы, созданные/импортированные иначе (суперпользователем postgres,
-- app-role или до ввода разделения ролей), оказываются «осиротевшими», и
-- AddField/AlterField на них падает в deploy.
--
-- Скрипт переписывает владение всей public-схемы на custocrm_schema — роль,
-- в которую входит custocrm_migration (см. init-runtime-roles.sh). После этого
-- любой migration-user может мигрировать любые таблицы.
--
-- Выполнять под суперпользователем postgres (не под app/migration role):
--   docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     < deploy/postgres/reassign-schema-ownership.sql
--
-- Идемпотентен: повторный запуск безопасен. Затрагивает только схему public.

\set ON_ERROR_STOP on

-- 1. Таблицы, последовательности, функции, типы → custocrm_schema.
ALTER SCHEMA public OWNER TO custocrm_schema;

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Таблицы.
    FOR r IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO custocrm_schema', r.tablename);
    END LOOP;

    -- Последовательности (включая owned-последовательности таблиц).
    FOR r IN
        SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO custocrm_schema', r.sequence_name);
    END LOOP;

    -- Функции/процедуры в public.
    FOR r IN
        SELECT p.oid, p.proname, pg_get_function_identity_arguments(p.oid) AS args
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
    LOOP
        EXECUTE format('ALTER FUNCTION %s(%s) OWNER TO custocrm_schema', r.proname, r.args);
    END LOOP;
END $$;

-- 2. Права по умолчанию для будущих объектов, создаваемых migration-user'ом,
--    остаются корректными (владелец = создатель, что для миграций = migration).
--    Явная выдача DDL-прав runtime-ролям не нужна и не делается (RLS-изоляция).

-- 3. Диагностика: кто чем владеет после нормализации.
SELECT tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
