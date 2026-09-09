# Полная проверка репозитория Chatballs (Windows).
#
# Запускается из любого каталога: скрипт сам переходит в корень code/chatballs.
#
# Два места, где прежняя редакция скрипта молча врала:
#   1) голый `docker compose` читает только compose.yaml, а сервисы frontend и
#      web-chat (node) существуют лишь в dev-оверлее — в базовом compose
#      frontend это production-образ nginx, где нет npm;
#   2) $ErrorActionPreference не останавливает скрипт на ненулевом коде
#      возврата нативных команд, поэтому падение тестов проходило как успех.
#      Каждый шаг проверяется явно по $LASTEXITCODE.
#
# Требуется один раз: npx playwright install chromium.
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$compose = "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml"
$failed = @()

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][scriptblock] $Body
    )
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) {
        $script:failed += $Name
        Write-Host "!!! $Name — код возврата $LASTEXITCODE" -ForegroundColor Red
    }
}

# Сначала быстрые проверки, затем длинные: backend-сьют идёт около 20 минут.
# Линтер запускается из корня репозитория: конфигурация лежит в pyproject.toml,
# а в контейнер смонтирован только apps/backend — без корня ruff взял бы
# правила по умолчанию вместо проектных и молча пропускал бы половину.
Invoke-Step "backend · ruff" { docker @compose run --rm --no-deps -v "${PWD}:/repo" -w /repo backend-app ruff check apps/backend }
Invoke-Step "internal-ui · typecheck" { docker @compose run --rm --no-deps frontend npm run typecheck }
Invoke-Step "web-chat · typecheck"    { docker @compose run --rm --no-deps web-chat npm run typecheck }
Invoke-Step "internal-ui · vitest"    { docker @compose run --rm --no-deps frontend npm run test }
Invoke-Step "deployment CLI · pytest" { python -m pytest -q tests/cli }
# Playwright сам поднимает нужные dev-серверы (webServer в playwright.config.ts).
Invoke-Step "e2e · playwright"        { npx playwright test }
# backend-app сам поднимает postgres, redis и миграции через сервис init.
Invoke-Step "backend · pytest"        { docker @compose run --rm backend-app pytest -q }

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "Провалено шагов: $($failed.Count)" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "Все проверки пройдены." -ForegroundColor Green
