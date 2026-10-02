"""Per-IP rate limiting so a public deployment can't drain the Gemini quota.

In-memory sliding window: fine for a single server instance. With several instances
you'd move this to Redis so they share counts.
"""
import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings

WINDOW_SECONDS = 3600.0


class SlidingWindow:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()  # sync routes run in a thread pool

    def hit(self, key: str, limit: int, window: float = WINDOW_SECONDS) -> float | None:
        """Record a request. Returns seconds to wait if over the limit, else None."""
        now = self.clock()
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return q[0] + window - now
            q.append(now)
            return None

    def reset(self) -> None:
        with self.lock:
            self.hits.clear()


_windows = {"upload": SlidingWindow(), "ask": SlidingWindow()}


def reset_limits() -> None:
    for w in _windows.values():
        w.reset()


def client_ip(request: Request) -> str:
    # uvicorn --proxy-headers (see Dockerfile) already resolves the real client IP
    # from the hosting provider's X-Forwarded-For header.
    return request.client.host if request.client else "unknown"


def rate_limit(name: str):
    def dependency(request: Request, settings: Settings = Depends(get_settings)) -> None:
        limit = settings.upload_limit_per_hour if name == "upload" else settings.ask_limit_per_hour
        if limit <= 0:  # 0 disables the limit
            return
        wait = _windows[name].hit(client_ip(request), limit)
        if wait is not None:
            minutes = max(1, math.ceil(wait / 60))
            raise HTTPException(
                429,
                f"Too many {name} requests. Please try again in {minutes} minute{'s' if minutes > 1 else ''}.",
                headers={"Retry-After": str(math.ceil(wait))},
            )

    return dependency
