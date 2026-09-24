"""Validate configuration once before Uvicorn starts workers.

A multi-worker Uvicorn parent keeps running while its workers crash on bad settings, so a
misconfigured container would look alive. The image runs this first and exits non-zero instead.
Errors print field names and messages only: Pydantic's default text can echo input values such
as a DATABASE_URL containing its password.
"""

import sys

from pydantic import ValidationError


def main() -> int:
    try:
        import app.main  # noqa: F401  (builds Settings and runs create_app startup guards)
    except ValidationError as error:
        for item in error.errors(include_input=False, include_url=False):
            field = ".".join(str(part) for part in item["loc"]) or "settings"
            print(f"startup refused: {field}: {item['msg']}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"startup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
