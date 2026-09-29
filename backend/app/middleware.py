"""Pure-ASGI middlewares: request id + access log + security headers, body-size limit, rate limiting."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id_var

logger = logging.getLogger("app.access")
EXPENSIVE = ("/api/v1/assessments", "/api/v1/assessments/stream")


def _client_ip(scope: Scope, trust_proxy: bool) -> str:
    if trust_proxy:
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                return value.decode().split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


async def _json_response(
    send: Send, status: int, code: str, message: str, extra_headers: list[tuple[bytes, bytes]] | None = None
) -> None:
    body = json.dumps(
        {"error": {"code": code, "message": message, "field_errors": [], "request_id": request_id_var.get()}}
    ).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())] + (extra_headers or [])
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"cache-control", b"no-store"),
                ]
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info("%s %s -> %s in %dms", scope["method"], scope["path"], status, (time.perf_counter() - start) * 1000)
            request_id_var.reset(token)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name == b"content-length" and value.isdigit() and int(value) > self.max_bytes:
                await _json_response(send, 413, "payload_too_large", "Request body is too large.")
                return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _TooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _TooLarge:
            await _json_response(send, 413, "payload_too_large", "Request body is too large.")


class _TooLarge(Exception):
    pass


class RateLimitMiddleware:
    """Sliding-window limiter, per client IP. In-memory: use a shared limiter in front of multiple replicas."""

    def __init__(self, app: ASGIApp, per_minute: int, expensive_per_minute: int, trust_proxy: bool = False) -> None:
        self.app = app
        self.limits = {"general": per_minute, "expensive": expensive_per_minute}
        self.trust_proxy = trust_proxy
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _allow(self, key: tuple[str, str], limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        window = self.hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return False, max(1, int(60 - (now - window[0])))
        window.append(now)
        return True, 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].endswith("/health"):
            await self.app(scope, receive, send)
            return
        ip = _client_ip(scope, self.trust_proxy)
        path: str = scope["path"].rstrip("/")
        expensive = scope["method"] == "POST" and (path in EXPENSIVE or path.endswith("/replan"))
        checks: list[tuple[str, int]] = [("general", self.limits["general"])]
        if expensive:
            checks.append(("expensive", self.limits["expensive"]))
        for bucket, limit in checks:
            ok, retry_after = self._allow((ip, bucket), limit)
            if not ok:
                await _json_response(
                    send,
                    429,
                    "rate_limited",
                    "Too many requests. Please slow down.",
                    [(b"retry-after", str(retry_after).encode())],
                )
                return
        if len(self.hits) > 10_000:  # bound memory
            self.hits.clear()
        await self.app(scope, receive, send)
