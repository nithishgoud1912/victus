"""Loopback browser sessions. Tokens/cookies are never persisted in local storage."""

import hashlib
import secrets
import threading
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

COOKIE = "victus_session"
PRODUCTION_ORIGIN = "http://127.0.0.1:8765"
PRODUCTION_ORIGINS = frozenset({PRODUCTION_ORIGIN, "http://localhost:8765"})
bearer = HTTPBearer(auto_error=False)
browser_cookie = APIKeyCookie(name=COOKIE, auto_error=False)


class BrowserSessions:
    def __init__(self, *, clock=time.time, ttl_seconds=900, capacity=64):
        self.clock, self.ttl_seconds, self.capacity = clock, ttl_seconds, capacity
        self._sessions = {}
        self._lock = threading.RLock()

    def _purge(self):
        now = self.clock()
        self._sessions = {key: expiry for key, expiry in self._sessions.items() if expiry > now}

    def create(self):
        with self._lock:
            self._purge()
            if len(self._sessions) >= self.capacity:
                raise HTTPException(429, "Browser session capacity reached")
            token = secrets.token_urlsafe(32)
            expiry = self.clock() + self.ttl_seconds
            self._sessions[hashlib.sha256(token.encode()).hexdigest()] = expiry
            return token, expiry

    def expiry(self, token):
        if not isinstance(token, str) or len(token) != 43:
            return None
        with self._lock:
            self._purge()
            return self._sessions.get(hashlib.sha256(token.encode()).hexdigest())

    def revoke(self, token):
        if not isinstance(token, str):
            return
        with self._lock:
            self._sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)


def create_auth(settings, sessions):
    def check_origin(request):
        origin = request.headers.get("origin")
        allowed = set(PRODUCTION_ORIGINS)
        if settings.dashboard_dev_origin is not None:
            allowed.add(settings.dashboard_dev_origin)
        if origin is not None and origin not in allowed:
            raise HTTPException(403, "Browser origin not enabled")

    def valid_bearer(credentials):
        return credentials is not None and secrets.compare_digest(
            credentials.credentials.encode("utf-8"), settings.api_token.encode("utf-8")
        )

    def require_bearer(
        request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
    ):
        check_origin(request)
        if not valid_bearer(credentials):
            raise HTTPException(401, "Unauthorized")

    def authorized(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        cookie: str | None = Depends(browser_cookie),
    ):
        check_origin(request)
        if request.headers.get("authorization") is not None:
            if valid_bearer(credentials):
                return
            raise HTTPException(401, "Unauthorized")
        if sessions.expiry(cookie) is None:
            raise HTTPException(401, "Unauthorized")
        if (
            request.method not in {"GET", "HEAD"}
            and request.headers.get("origin") not in PRODUCTION_ORIGINS
        ):
            raise HTTPException(403, "Browser session mutations require the backend origin")

    return authorized, require_bearer
