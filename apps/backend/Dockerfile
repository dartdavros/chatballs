FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/backend/requirements.txt /app/apps/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/backend/requirements.txt

COPY apps/backend /app/apps/backend
# Тот же генератор секретов, что и в production-образе: сервис secrets
# крутится на backend-образе и в dev, и в коробке.
COPY deploy/secrets/generate-instance-secrets.sh /usr/local/bin/chatballs-generate-secrets.sh
RUN chmod 0755 /usr/local/bin/chatballs-generate-secrets.sh

WORKDIR /app/apps/backend

EXPOSE 8000
