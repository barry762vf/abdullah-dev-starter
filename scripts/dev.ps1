$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error 'Missing .env. Copy .env.example to .env and review the development credentials first.'
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBin = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin'
    if (Test-Path -LiteralPath (Join-Path $dockerBin 'docker.exe')) {
        # Docker Desktop's per-user installer may not update the current shell PATH.
        # The credential helper in this directory is also needed for image pulls.
        $env:PATH = "$dockerBin;$env:PATH"
    } else {
        Write-Error 'Docker is not installed or not on PATH. Install and start Docker Desktop, then rerun this script.'
        exit 1
    }
}

docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Docker daemon is unavailable. Start Docker Desktop, then rerun this script.'
    exit 1
}

Push-Location $projectRoot
try {
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) {
        throw 'PostgreSQL did not become healthy. Run docker compose ps db and docker compose logs db.'
    }
    Write-Host 'PostgreSQL is healthy on localhost:5432.'
    if ((Test-Path -LiteralPath 'backend/app/main.py') -and (Test-Path -LiteralPath 'frontend/package.json')) {
        Write-Host 'Start the backend from backend/: uvicorn app.main:app --reload'
        Write-Host 'Start the frontend from frontend/: npm run dev'
    } else {
        Write-Host 'Backend and frontend will be scaffolded in later roadmap phases.'
    }
} finally {
    Pop-Location
}
