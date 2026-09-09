# Локальный запуск Chatballs из исходников (Windows).
#
# Это путь разработчика: стек собирается из репозитория. Установка продукта
# выглядит иначе и этого скрипта не требует — там один compose.yaml со
# страницы релиза и `docker compose up -d --wait` (см. README).
#
# Ни одной переменной задавать не нужно и негде: .env у продукта нет. Секреты
# инстанса генерирует первый старт (сервис secrets), всё остальное —
# организацию, владельца, домены, почту, интеграции — человек настраивает в UI.
param(
    [ValidateSet("Cloud", "SelfHosted")]
    [string] $Mode = "Cloud"
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$delivery = if ($Mode -eq "SelfHosted") { "SELF_HOSTED" } else { "CLOUD" }
Write-Output "Сборка из исходников, режим поставки: $delivery."

$env:CHATBALLS_DELIVERY_MODE = $delivery
docker compose -f compose.yaml -f compose.dev.yaml up --build
