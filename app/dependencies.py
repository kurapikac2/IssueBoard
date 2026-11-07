import secrets
import sqlite3
import time
from typing import Annotated

from fastapi import Depends, Request

from app.database import get_db
from app.services.auth import token_hash
from app.services.errors import ServiceError


def database(request: Request):
    yield from get_db(request)


Db = Annotated[sqlite3.Connection, Depends(database)]


def current_session(request: Request, db: Db) -> dict:
    token = request.cookies.get("issueboard_session", "")
    row = db.execute(
        """SELECT s.token_hash, s.csrf_token, u.id, u.username
           FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token_hash = ? AND s.expires_at > ?""",
        (token_hash(token), int(time.time())),
    ).fetchone()
    if row is None:
        raise ServiceError(401, "Войдите в аккаунт.")
    session = dict(row)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not supplied.isascii() or not secrets.compare_digest(supplied, session["csrf_token"]):
            raise ServiceError(403, "Сессия формы устарела. Обновите страницу.")
    return session


Session = Annotated[dict, Depends(current_session)]


def json_only(request: Request) -> None:
    # Also blocks login CSRF: cross-origin HTML forms cannot send application/json.
    if request.method in {"POST", "PUT", "PATCH"} and request.url.path != "/api/auth/logout":
        media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type != "application/json":
            raise ServiceError(415, "Ожидается JSON.")
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        if origin != str(request.base_url).rstrip("/"):
            raise ServiceError(403, "Запрос с другого сайта запрещён.")