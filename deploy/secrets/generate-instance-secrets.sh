#!/bin/sh
# Секреты инстанса генерируются один раз при первом старте и живут в томах
# chatballs-secrets*. В .env, в репозитории и в руках человека их нет: установка
# — одна команда, всё остальное настраивается в UI.
#
# Томов три, и каждый процесс монтирует только свои:
#   $DIR            — общие: ключ подписи, ключ шифрования, пароль роли app,
#                     секрет TURN (том chatballs-secrets);
#   $DIR/platform   — пароль роли platform (chatballs-secrets-platform):
#                     платформенная поверхность и воркер;
#   $DIR/schema     — пароль роли миграций и владельца кластера
#                     (chatballs-secrets-schema): postgres, init, admin.
# Публичный backend-app видит только общий том — пароли, дающие обход RLS,
# ему недоступны даже при компрометации процесса.
#
# Скрипт идемпотентен: существующие файлы не трогает, поэтому перезапуск и
# обновление стека не меняют пароли уже работающей базы. Установки, где
# пароли лежали плоско в общем томе, переносятся сюда же: файл копируется в
# свой том, сверяется и только потом удаляется из общего.
set -eu

DIR="${CHATBALLS_SECRETS_DIR:-/run/chatballs/secrets}"
PLATFORM_DIR="$DIR/platform"
SCHEMA_DIR="$DIR/schema"
mkdir -p "$DIR" "$PLATFORM_DIR" "$SCHEMA_DIR"
# Тома видны только контейнерам стека, но читают их разные
# пользователи (postgres, backend), поэтому права как у docker
# secrets: каталог 0755, файлы 0444. Права выставляются на каждом
# запуске — старые установки чинятся сами.
chmod 755 "$DIR" "$PLATFORM_DIR" "$SCHEMA_DIR"

# 32 байта энтропии в hex. openssl есть в alpine/postgres-образах; /dev/urandom —
# запасной путь, если нет.
random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

# Перенос плоского файла из общего тома в свой: только если в своём его ещё
# нет. Копия сверяется побайтно, и лишь после этого оригинал удаляется —
# обрыв на любом шаге оставляет как минимум один целый экземпляр.
relocate_secret() {
  name="$1"
  target_dir="$2"
  source="$DIR/$name"
  target="$target_dir/$name"
  if [ -s "$target" ] || [ ! -s "$source" ]; then
    return 0
  fi
  cp "$source" "$target"
  if ! cmp -s "$source" "$target"; then
    rm -f "$target"
    echo "failed to relocate $name: copy mismatch" >&2
    exit 1
  fi
  chmod 444 "$target"
  chmod 644 "$source" 2>/dev/null || true
  rm -f "$source"
  echo "relocated $name to $(basename "$target_dir")/"
}

ensure_secret() {
  name="$1"
  target_dir="${2:-$DIR}"
  file="$target_dir/$name"
  if [ -s "$file" ]; then
    return 0
  fi
  random_secret > "$file"
  chmod 444 "$file"
  echo "generated $name"
}

fix_permissions() {
  # Только файлы: каталоги platform/ и schema/ — точки монтирования своих
  # томов, и без бита исполнения на них postgres и backend не войдут внутрь.
  chmod 755 "$DIR" "$PLATFORM_DIR" "$SCHEMA_DIR"
  for d in "$DIR" "$PLATFORM_DIR" "$SCHEMA_DIR"; do
    for f in "$d"/*; do
      [ -f "$f" ] && chmod 444 "$f"
    done
  done
  return 0
}

relocate_secret postgres_platform_password "$PLATFORM_DIR"
relocate_secret postgres_migration_password "$SCHEMA_DIR"
relocate_secret postgres_password "$SCHEMA_DIR"

ensure_secret secret_key
ensure_secret postgres_password "$SCHEMA_DIR"
ensure_secret postgres_app_password
ensure_secret postgres_platform_password "$PLATFORM_DIR"
ensure_secret postgres_migration_password "$SCHEMA_DIR"
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
