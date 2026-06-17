FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/backend/requirements.txt /app/apps/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/backend/requirements.txt

COPY apps/backend /app/apps/backend

WORKDIR /app/apps/backend

EXPOSE 8000
