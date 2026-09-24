"""The container preflight must fail fast and never print secret input values."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def run_preflight(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.preflight"],
        cwd=BACKEND,
        env={"ENV_FILE": "", "SYSTEMROOT": "C:\Windows", "PATH": ""} | env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_preflight_refuses_bad_production_settings_without_leaking_values() -> None:
    leaked_password = "SuperSecretDbPassword123"
    result = run_preflight(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "short-sample-key",
            "DATABASE_URL": f"mysql://user:{leaked_password}@db/app",
        }
    )
    assert result.returncode == 1
    assert "startup refused" in result.stderr
    assert leaked_password not in result.stderr + result.stdout
    assert "short-sample-key" not in result.stderr + result.stdout


def test_preflight_accepts_valid_settings() -> None:
    result = run_preflight(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 64,
            "DATABASE_URL": "postgresql+asyncpg://user:pass@db:5432/app",
            "CORS_ORIGINS": "https://app.example.com",
            "COOKIE_SECURE": "true",
            "CLIENT_IP_SOURCE": "peer",
        }
    )
    assert result.returncode == 0, result.stderr
