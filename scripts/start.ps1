param(
    [ValidateSet("Cloud", "SelfHosted")]
    [string]$Mode = "Cloud"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

# Dev-контур: canonical compose.yaml + dev override (ADR-HUB-0028).
# Режим поставки задаётся процессу Compose и не переписывает локальный .env.
$deliveryMode = if ($Mode -eq "SelfHosted") { "SELF_HOSTED" } else { "CLOUD" }
$previousDeliveryMode = $env:CUS_DELIVERY_MODE
$env:CUS_DELIVERY_MODE = $deliveryMode

try {
    docker compose -f compose.yaml -f compose.dev.yaml --env-file .env.example --env-file .env up --build
}
finally {
    if ($null -eq $previousDeliveryMode) {
        Remove-Item Env:CUS_DELIVERY_MODE -ErrorAction SilentlyContinue
    }
    else {
        $env:CUS_DELIVERY_MODE = $previousDeliveryMode
    }
}
