# Disposable copy of the main dev environment for a task: database, media and
# instance secrets, all in Docker volumes of the task's Compose project.
# Nothing unique lives in the copy; it is removed together with the task.
#
# Run it from the task checkout with the task's Compose environment
# (COMPOSE_FILE with compose.task.yaml, ports, image tags): the script starts
# the task's own postgres through Compose before it restores the data.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')]
    [string] $Name,
    # Compose project of the main working copy that owns the source database.
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')]
    [string] $Source = 'chatballs'
)

$ErrorActionPreference = 'Stop'
if ($Name -eq $Source) { throw 'The copy must not share the Compose project of its source.' }
$env:COMPOSE_PROJECT_NAME = $Name

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "docker $($args[0]) failed; see the output above." }
}

function Get-SourceContainer([string] $Service, [switch] $Running) {
    $filter = @('--filter', "label=com.docker.compose.project=$Source",
        '--filter', "label=com.docker.compose.service=$Service")
    $ids = if ($Running) { @(& docker ps -q @filter) } else { @(& docker ps -aq @filter) }
    if ($LASTEXITCODE -ne 0) { throw 'Docker is not available; nothing was copied.' }
    return $ids | Select-Object -First 1
}

$postgres = Get-SourceContainer postgres -Running
if (-not $postgres) { throw "The database of '$Source' is not running. Start the main environment first." }
$image = & docker inspect --format '{{.Config.Image}}' $postgres
$superuser = & docker exec $postgres printenv POSTGRES_USER
$database = & docker exec $postgres printenv POSTGRES_DB
if (-not $image -or -not $superuser -or -not $database) { throw 'Cannot read the source database settings.' }

$secrets = @('chatballs-secrets', 'chatballs-secrets-platform', 'chatballs-secrets-schema')
foreach ($suffix in $secrets) {
    & docker volume inspect "${Source}_$suffix" --format '{{.Name}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Source secret volume is missing: ${Source}_$suffix" }
}
foreach ($suffix in $secrets + @('chatballs-postgres', 'chatballs-media')) {
    & docker volume inspect "${Name}_$suffix" --format '{{.Name}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { throw "Volume ${Name}_$suffix already exists. Remove the old copy first." }
}

# The media of the source: a host folder in dev, a named volume in a boxed install.
$media = $null
$backend = Get-SourceContainer backend-app
if ($backend) {
    $media = & docker inspect $backend --format `
        '{{range .Mounts}}{{if eq .Destination "/app/apps/backend/media"}}{{.Type}}|{{if eq .Type "volume"}}{{.Name}}{{else}}{{.Source}}{{end}}{{end}}{{end}}'
}

function New-CopyVolume([string] $Suffix) {
    # Compose adopts a volume that carries its project and volume labels.
    Invoke-Docker volume create --label "com.docker.compose.project=$Name" `
        --label "com.docker.compose.volume=$Suffix" "${Name}_$Suffix" | Out-Null
}
function Copy-Volume([string] $From, [string] $To) {
    Invoke-Docker run --rm --entrypoint sh -v "${From}:/from:ro" -v "${To}:/to" $image -c 'cp -a /from/. /to/'
}

try {
    # The copy keeps the instance secrets, so the restored roles and signing key stay valid.
    foreach ($suffix in $secrets) {
        New-CopyVolume $suffix
        Copy-Volume "${Source}_$suffix" "${Name}_$suffix"
    }
    New-CopyVolume 'chatballs-media'
    $kind, $path = "$media".Split('|', 2)
    if ($kind -eq 'volume') {
        Copy-Volume $path "${Name}_chatballs-media"
    } elseif ($kind -eq 'bind') {
        # Docker Desktop reports a Windows folder in Linux notation; the host reads it far faster.
        $path = $path -replace '^/(?:run/desktop/mnt/host|host_mnt)/([a-z])/', '$1:/'
        $holder = (Invoke-Docker create -v "${Name}_chatballs-media:/to" $image)
        try { Invoke-Docker cp "$path/." "${holder}:/to" } finally { & docker rm $holder | Out-Null }
    }
    # The task's own stack initializes its cluster and roles from the copied secrets;
    # a logical copy of one database follows, the source keeps running.
    Invoke-Docker compose up -d --wait postgres
    $target = & docker compose ps -q postgres
    Invoke-Docker volume create --label "com.docker.compose.project=$Name" "${Name}_clone-scratch" | Out-Null
    try {
        Invoke-Docker run --rm --network "container:$postgres" --entrypoint pg_dump `
            -v "${Name}_clone-scratch:/dump" $image `
            -h 127.0.0.1 -U $superuser -Fc -f /dump/db.dump $database
        Invoke-Docker run --rm --network "container:$target" --entrypoint pg_restore `
            -v "${Name}_clone-scratch:/dump" $image `
            -h 127.0.0.1 -U $superuser -d $database --exit-on-error --single-transaction /dump/db.dump
    } finally {
        & docker volume rm "${Name}_clone-scratch" | Out-Null
    }
} catch {
    # The copy is disposable and nothing else exists in its project yet; the source is never touched.
    & docker compose down --volumes --remove-orphans 2>$null | Out-Null
    foreach ($suffix in $secrets + @('chatballs-media')) { & docker volume rm "${Name}_$suffix" 2>$null | Out-Null }
    throw
}
Write-Output "Copy of '$Source' is ready in the volumes of '$Name'."
