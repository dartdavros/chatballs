#!/bin/sh
# Секреты инстанса генерируются один раз при первом старте и живут в томе
# chatballs-secrets. В .env, в репозитории и в руках человека их нет: установка
# — одна команда, всё остальное настраивается в UI.
#
# Скрипт идемпотентен: существующие файлы не трогает, поэтому перезапуск и
# обновление стека не меняют пароли уже работающей базы.
set -eu

DIR="${CHATBALLS_SECRETS_DIR:-/run/chatballs/secrets}"
mkdir -p "$DIR"
# Том виден только контейнерам стека, но читают его разные
# пользователи (postgres, backend), поэтому права как у docker
# secrets: каталог 0755, файлы 0444. Права выставляются на каждом
# запуске — старые установки чинятся сами.
chmod 755 "$DIR"

# 32 байта энтропии в hex. openssl есть в alpine/postgres-образах; /dev/urandom —
# запасной путь, если нет.
random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

ensure_secret() {
  name="$1"
  file="$DIR/$name"
  if [ -s "$file" ]; then
    return 0
  fi
  random_secret > "$file"
  chmod 444 "$file"
  echo "generated $name"
}

fix_permissions() {
  chmod 444 "$DIR"/* 2>/dev/null || true
}

ensure_secret secret_key
ensure_secret postgres_password
ensure_secret postgres_app_password
ensure_secret postgres_platform_password
ensure_secret postgres_migration_password
# Общий секрет TURN: его знают приложение и coturn. Человек его не вводит —
# иначе пришлось бы вписывать одно и то же значение в двух местах.
ensure_secret turn_secret

# Ключ шифрования секретов в БД (Fernet): им зашифрованы секреты TOTP
# сотрудников, токены интеграций, пароль SMTP и ключи S3.
#
# Значение выводится из ключа подписи ровно тем же способом, каким его выводил
# сам продукт, пока отдельного файла не было. Поэтому работающая установка
# ничего не теряет: ключ тот же, просто теперь он живёт своим файлом и больше
# не следует за secret_key. До этого смена ключа подписи молча делала всё
# зашифрованное нечитаемым — Fernet без ключа не расшифровать.
ensure_field_encryption_key() {
  file="$DIR/field_encryption_key"
  if [ -s "$file" ]; then
    return 0
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    # Вывести ключ нечем. Файла не будет, продукт выведет его сам — значение то
    # же самое, просто связка с secret_key сохранится до появления openssl.
    echo "openssl not found — field_encryption_key left derived from secret_key"
    return 0
  fi
  # base64url(sha256(secret_key)) — совпадает с chatballs.identity.crypto.
  printf %s "$(cat "$DIR/secret_key")" \
    | openssl dgst -sha256 -binary \
    | openssl base64 -A \
    | tr '+/' '-_' > "$file"
  chmod 444 "$file"
  echo "generated field_encryption_key"
}

ensure_field_encryption_key

# Coturn читает секрет не из аргумента, а из конфига: значение не светится
# в списке процессов и не дублируется в compose.
if [ ! -s "$DIR/turnserver-secret.conf" ]; then
  echo "static-auth-secret=$(cat "$DIR/turn_secret")" > "$DIR/turnserver-secret.conf"
fi

fix_permissions

echo "instance secrets ready in $DIR"
