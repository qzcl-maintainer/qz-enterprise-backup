import os

from fastapi import HTTPException, Request, status


def check_credentials(username: str, password: str) -> bool:
    admin_user = os.environ.get("ADMIN_USER", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "changeme")
    return username == admin_user and password == admin_password


def login(request: Request, username: str) -> None:
    request.session["user"] = username


def logout(request: Request) -> None:
    request.session.clear()


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_auth(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
