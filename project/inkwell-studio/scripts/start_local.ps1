param(
    [switch]$SkipInstall,
    [switch]$SkipMigrate,
    [switch]$UsePostgres
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host $Message
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$PythonInVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonInVenv)) {
    Invoke-CheckedCommand "[Bedrock] Creating virtual environment..." { python -m venv .venv }
}

$PythonInVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "[Bedrock] Using Python: $PythonInVenv"

if (-not $SkipInstall) {
    Invoke-CheckedCommand "[Bedrock] Upgrading pip..." { & $PythonInVenv -m pip install --upgrade pip }
    Invoke-CheckedCommand "[Bedrock] Installing base dependencies..." { & $PythonInVenv -m pip install -r requirements.txt }
}

$env:DJANGO_SETTINGS_MODULE = "config.settings.development"

if ($UsePostgres) {
    $env:DEV_USE_SQLITE = "False"
    if (-not $SkipInstall) {
        Invoke-CheckedCommand "[Bedrock] Installing PostgreSQL dependency..." { & $PythonInVenv -m pip install -r requirements-postgres.txt }
    }
    if (-not $env:POSTGRES_HOST) { $env:POSTGRES_HOST = "127.0.0.1" }
    if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5432" }
    if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "bedrock" }
    if (-not $env:POSTGRES_USER) { $env:POSTGRES_USER = "bedrock" }
    if (-not $env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD = "bedrock" }
} else {
    $env:DEV_USE_SQLITE = "True"
}

if (-not $SkipMigrate) {
    Invoke-CheckedCommand "[Bedrock] Running migrations..." { & $PythonInVenv manage.py migrate }
}

Write-Host "[Bedrock] Starting dev server at http://127.0.0.1:8000"
& $PythonInVenv manage.py runserver 0.0.0.0:8000
