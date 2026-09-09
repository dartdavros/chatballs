# PostgreSQL Chatballs: тот же pgvector, но со своими init-скриптами внутри.
#
# Раньше compose монтировал эти файлы с хоста. Из-за этого установка требовала
# рядом распакованный репозиторий, а забытый в релизе файл превращался в
# молча созданный Docker'ом пустой каталог — и стек падал на первом старте.
# Теперь всё, что нужно базе, лежит в образе.
ARG CHATBALLS_POSTGRES_BASE_IMAGE=pgvector/pgvector:pg16
FROM ${CHATBALLS_POSTGRES_BASE_IMAGE}

# Роли app/platform/migration и расширение vector — при инициализации кластера.
COPY deploy/postgres/init-runtime-roles.sh /docker-entrypoint-initdb.d/20-chatballs-runtime-roles.sh
# Нормализация владельца public-схемы: вызывается вручную из `chatballs deploy`.
COPY deploy/postgres/reassign-schema-ownership.sql /chatballs-reassign-ownership.sql

# Бит исполнения не переживает checkout на Windows, а без него entrypoint
# источает скрипт вместо запуска — и `exit 1` внутри убивает инициализацию.
RUN chmod 0755 /docker-entrypoint-initdb.d/20-chatballs-runtime-roles.sh \
 && chmod 0644 /chatballs-reassign-ownership.sql
