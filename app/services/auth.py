import hashlib
import secrets
import sqlite3
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

from app.schemas import Credentials
from app.services.errors import ServiceError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
# A missing account still incurs a password verification, reducing timing differences.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def throttle(db: sqlite3.Connection, ip: str) -> None:
    now = int(time.time())
    key = token_hash(ip)
    with db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM auth_attempts WHERE attempted_at < ?", (now - 600,))
        count = db.execute(
            "SELECT COUNT(*) FROM auth_attempts WHERE ip_hash = ?", (key,)
        ).fetchone()[0]
        if count >= 20:
            raise ServiceError(429, "Слишком много попыток. Повторите через 10 минут.")
        db.execute("INSERT INTO auth_attempts VALUES (?, ?)", (key, now))


def register(db: sqlite3.Connection, data: Credentials) -> dict:
    password_hash = hasher.hash(data.password)
    try:
        with db:
            cursor = db.execute(
                "INSERT INTO users(username, password_hash) VALUES (?, ?)",
                (data.username.lower(), password_hash),
            )
    except sqlite3.IntegrityError as exc:
        raise ServiceError(409, "Это имя пользователя уже занято.") from exc
    return {"id": cursor.lastrowid, "username": data.username.lower()}


def login(db: sqlite3.Connection, data: Credentials) -> dict:
    user = db.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (data.username,)
    ).fetchone()
    try:
        hasher.verify(user["password_hash"] if user else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError) as exc:
        raise ServiceError(401, "Неверное имя пользователя или пароль.") from exc
    if user is None:
        raise ServiceError(401, "Неверное имя пользователя или пароль.")
    return {"id": user["id"], "username": user["username"]}


def create_session(db: sqlite3.Connection, user_id: int, hours: int, previous: str | None):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        if previous:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(previous),))
        db.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?)",
            (token_hash(token), user_id, csrf, int(time.time()) + hours * 3600),
        )
    return token, csrf