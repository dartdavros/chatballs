$ErrorActionPreference = "Stop"

# Одноразовый импорт демо-данных организации «Северная Верфь» (выдуманные данные,
# РФ-наполнение). Профиль demo-seed определён только в compose.dev.yaml и не
# запускается обычным `docker compose up`. Сама команда `seed_demo` идемпотентна.
# Запускайте только после того, как локальный dev-стек поднят.
docker compose -f compose.yaml -f compose.dev.yaml --profile demo-seed --env-file .env.example --env-file .env `
    run --rm demo-seed
