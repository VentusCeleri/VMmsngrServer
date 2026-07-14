from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request, status

from app.core.config import settings
from app.core.errors import APIError


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        if not settings.rate_limit_enabled:
            return

        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            raise APIError(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "rate_limit_exceeded",
                "Too many requests. Please try again later.",
            )

        bucket.append(now)

    def clear(self) -> None:
        self._hits.clear()


rate_limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(namespace: str, limit_getter: Callable[[], int]) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        key = f"{namespace}:{client_ip(request)}"
        rate_limiter.check(
            key,
            limit=limit_getter(),
            window_seconds=settings.rate_limit_window_seconds,
        )

    return dependency
