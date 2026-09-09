# Шлюз Chatballs: Caddy со своим Caddyfile внутри образа.
#
# Конфигурация шлюза — часть релиза, а не файл, который человек кладёт рядом:
# установка сводится к одному compose.yaml и не требует ничего распаковывать.
ARG CHATBALLS_GATEWAY_BASE_IMAGE=caddy:2.8.4
FROM ${CHATBALLS_GATEWAY_BASE_IMAGE}

COPY Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
