import time
import asyncio
from collections import deque
from typing import Callable, Iterable
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

class RateLimitMiddleware:
    def __init__(
        self,
        app,
        *,
        window_seconds: int,
        max_calls: int,
        key_func: Callable[[Request], str],
        include_path_prefixes: Iterable[str] = ("/tools", "/upload"),
    ):
        self.app = app
        self.window = window_seconds
        self.max_calls = max_calls
        self.key_func = key_func
        self.include_paths = tuple(include_path_prefixes)

        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    def _should_guard(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.include_paths)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        if not self._should_guard(path):
            return await self.app(scope, receive, send)

        request = Request(scope, receive=receive)
        key = self.key_func(request)

        now = time.time()
        async with self._lock:
            q = self._buckets.get(key)
            if q is None:
                q = deque()
                self._buckets[key] = q

            cutoff = now - self.window
            while q and q[0] < cutoff:
                q.popleft()

            if len(q) >= self.max_calls:
                retry_after = max(1, int(q[0] + self.window - now))
                resp = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too Many Requests",
                        "key": key,
                        "window_seconds": self.window,
                        "max_calls": self.max_calls,
                        "try_again_in": retry_after,
                    },
                )
                resp.headers["Retry-After"] = str(retry_after)
                return await resp(scope, receive, send)

            q.append(now)

        return await self.app(scope, receive, send)


def make_key_func(secret_key: str) -> Callable[[Request], str]:
    def _key(req: Request) -> str:
        ip = req.client.host if req.client else "unknown"

        auth = req.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
            except JWTError:
                pass

        return f"ip:{ip}"
    return _key
