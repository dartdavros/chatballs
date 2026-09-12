# Сервис updater: обновление установки по кнопке из интерфейса (ADR-CHATBALLS-0049).
# Официальный образ docker CLI с плагином compose плюс два сценария; больше в
# нём ничего нет. Базовый образ закрепляется по digest при сборке релиза.
ARG CHATBALLS_UPDATER_BASE_IMAGE=docker:27-cli
FROM ${CHATBALLS_UPDATER_BASE_IMAGE}

COPY deploy/updater/chatballs-updater.sh /usr/local/bin/chatballs-updater.sh
COPY deploy/updater/chatballs-updater-apply.sh /usr/local/bin/chatballs-updater-apply.sh
RUN chmod 0755 /usr/local/bin/chatballs-updater.sh /usr/local/bin/chatballs-updater-apply.sh

ENTRYPOINT ["/bin/sh", "/usr/local/bin/chatballs-updater.sh"]
