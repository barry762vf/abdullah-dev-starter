# Build the production images and validate the production compose file.
# Usage: .\scripts\build.ps1 [-EnvFile deploy\production.env] [-Up]
param(
    [string]$EnvFile = 'deploy/production.env',
    [switch]$Up
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw "Missing $EnvFile. Copy deploy/production.env.example and fill every value (never commit it)."
    }
    docker build -t abdullah-core-api:local backend
    if ($LASTEXITCODE -ne 0) { throw 'Backend image build failed.' }
    docker build -t abdullah-core-web:local frontend
    if ($LASTEXITCODE -ne 0) { throw 'Frontend image build failed.' }
    docker compose --env-file $EnvFile -f docker-compose.prod.yml config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'docker-compose.prod.yml is invalid for this environment file.' }
    if ($Up) {
        docker compose --env-file $EnvFile -f docker-compose.prod.yml up -d --wait
        if ($LASTEXITCODE -ne 0) { throw 'Production stack did not become healthy.' }
        Write-Host 'Production stack is healthy. Run scripts/smoke-prod.sh to verify it.'
    } else {
        Write-Host 'Images built and compose configuration is valid.'
    }
} finally {
    Pop-Location
}
