"""Starter per-process limiter: window, bound and 429 contract (not a distributed limiter)."""

import pytest

from app.core import rate_limit
from app.core.exceptions import AppException
from app.core.rate_limit import AuthRateLimiter


def test_login_limit_resets_after_the_window(monkeypatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now[0])
    limiter = AuthRateLimiter()
    for _ in range(5):
        limiter.check("login", "198.51.100.1")
    with pytest.raises(AppException) as error:
        limiter.check("login", "198.51.100.1")
    assert error.value.status_code == 429
    limiter.check("login", "198.51.100.2")  # other clients are unaffected
    now[0] += 60
    limiter.check("login", "198.51.100.1")  # the 60 s window expired


def test_registration_limit_is_three_per_hour(monkeypatch) -> None:
    now = [0.0]
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now[0])
    limiter = AuthRateLimiter()
    for _ in range(3):
        limiter.check("register", "198.51.100.1")
    now[0] += 3599
    with pytest.raises(AppException):
        limiter.check("register", "198.51.100.1")
    now[0] += 1
    limiter.check("register", "198.51.100.1")


def test_memory_is_bounded(monkeypatch) -> None:
    """Known limitation (BUG-010): eviction can forget an old client; memory stays bounded."""
    limiter = AuthRateLimiter()
    for index in range(5000):
        limiter.check("login", f"2001:db8::{index:x}")
    assert len(limiter._events) <= 4097
