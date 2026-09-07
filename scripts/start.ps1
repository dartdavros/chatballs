# Локальный запуск Chatballs (Windows).
#
# Ни одной переменной задавать не нужно и негде: .env у продукта нет. Секреты
# инстанса генерирует первый старт (сервис secrets), всё остальное — организацию,
# владельца, домены, почту, интеграции — человек настраивает в UI.
#
# Если рядом лежит release.env (скачан со страницы релиза), образы берутся из
# реестра по digest — запуск занимает минуты вместо сборки. Без него стек
# собирается из исходников: так работают те, кто правит код.
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (Test-Path "release.env") {
    Write-Output "release.env найден: образы берутся из реестра, сборки не будет."
    docker compose --env-file release.env -f compose.yaml up
}
else {
    Write-Output "release.env нет: собираем из исходников (для готовых образов скачайте release.env со страницы релиза)."
    docker compose -f compose.yaml -f compose.dev.yaml up --build
}
