"""The destructive-test database guard must refuse anything but a dedicated *_test database."""

import pytest
from db_guard import unsafe_test_database_reason

DEV = "postgresql+asyncpg://postgres:postgres@localhost:5432/abdullah_core_dev"


@pytest.mark.parametrize(
    ("raw", "normal"),
    [
        (None, DEV),
        ("", DEV),
        ("postgresql://postgres:postgres@localhost:5432/app_test", DEV),
        ("postgresql+asyncpg://postgres:postgres@localhost:5432/abdullah_core_dev", DEV),
        ("postgresql+asyncpg://postgres:postgres@localhost:5432/", DEV),
        ("postgresql+asyncpg://postgres:postgres@localhost:5432/test_app", DEV),
        # Same database spelled differently must still be refused.
        (
            "postgresql+asyncpg://other:secret@127.0.0.1/shared_test",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/shared_test",
        ),
    ],
)
def test_guard_refuses_unsafe_targets(raw, normal) -> None:
    assert unsafe_test_database_reason(raw, normal) is not None


def test_guard_accepts_dedicated_test_database() -> None:
    raw = "postgresql+asyncpg://postgres:postgres@localhost:5432/abdullah_core_test"
    assert unsafe_test_database_reason(raw, DEV) is None
    assert unsafe_test_database_reason(raw, None) is None
