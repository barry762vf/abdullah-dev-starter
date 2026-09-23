#!/usr/bin/env bash
set -euo pipefail

script_path="${BASH_SOURCE[0]}"
script_dir="${script_path%/*}"
if [[ "$script_dir" == "$script_path" ]]; then
  script_dir=.
fi
project_root="$(cd "$script_dir/.." && pwd)"
if [[ ! -f "$project_root/.env" ]]; then
  echo 'Missing .env. Copy .env.example to .env and review the development credentials first.' >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker is not installed or not on PATH. Install and start Docker, then rerun this script.' >&2
  exit 1
fi
if ! docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
  echo 'Docker daemon is unavailable. Start Docker, then rerun this script.' >&2
  exit 1
fi

cd "$project_root"
docker compose up -d --wait db
echo 'PostgreSQL is healthy on localhost:5432.'
if [[ -f backend/app/main.py && -f frontend/package.json ]]; then
  echo 'Start the backend from backend/: uvicorn app.main:app --reload'
  echo 'Start the frontend from frontend/: npm run dev'
else
  echo 'Backend and frontend will be scaffolded in later roadmap phases.'
fi
