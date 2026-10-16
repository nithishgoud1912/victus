"""A bearer bootstrap becomes a bounded HttpOnly browser session in production."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from victus.api.auth import COOKIE


class SessionStatus(BaseModel):
    authenticated: bool
    expires_at: float | None


def create_session_router(authorized, require_bearer, sessions):
    router = APIRouter(prefix="/api/session", tags=["session"])

    @router.post("", response_model=SessionStatus, dependencies=[Depends(require_bearer)])
    def create_session(response: Response):
        token, expiry = sessions.create()
        response.set_cookie(
            COOKIE,
            token,
            max_age=sessions.ttl_seconds,
            path="/api",
            httponly=True,
            samesite="strict",
            secure=False,
        )
        return SessionStatus(authenticated=True, expires_at=expiry)

    @router.get("", response_model=SessionStatus, dependencies=[Depends(authorized)])
    def session_status(request: Request):
        return SessionStatus(
            authenticated=True, expires_at=sessions.expiry(request.cookies.get(COOKIE))
        )

    @router.delete("", status_code=204, dependencies=[Depends(authorized)])
    def delete_session(request: Request):
        sessions.revoke(request.cookies.get(COOKIE))
        response = Response(status_code=204)
        response.delete_cookie(COOKIE, path="/api", httponly=True, samesite="strict")
        return response

    return router
