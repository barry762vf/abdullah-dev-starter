"""Small per-process IP limit for local/single-worker deployments."""

from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from app.core.exceptions import AppException


class AuthRateLimiter:
    def __init__(self) -> None:
        self._events: OrderedDict[tuple[str, str], deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(self, action: str, client_ip: str) -> None:
        limit, window = (5, 60) if action == "login" else (3, 3600)
        now = monotonic()
        with self._lock:
            key = (action, client_ip)
            events = self._events.setdefault(key, deque())
            self._events.move_to_end(key)
            if len(self._events) > 4096:
                self._events.popitem(last=False)
            while events and events[0] <= now - window:
                events.popleft()
            if len(events) >= limit:
                raise AppException(429, "Too Many Requests", "Authentication rate limit exceeded.")
            events.append(now)
