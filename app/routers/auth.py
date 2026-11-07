from fastapi import APIRouter, Request, Response

from app.dependencies import Db, Session
from app.schemas import Credentials, SessionOut, UserOut
from app.services import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: Credentials, request: Request, db: Db):
    auth.throttle(db, request.client.host if request.client else "unknown")
    return auth.register(db, data)


@router.post("/login", response_model=SessionOut)
def login(data: Credentials, request: Request, response: Response, db: Db):
    auth.throttle(db, request.client.host if request.client else "unknown")
    user = auth.login(db, data)
    settings = request.app.state.settings
    token, csrf = auth.create_session(
        db, user["id"], settings.session_hours, request.cookies.get("issueboard_session")
    )
    response.set_cookie(
        "issueboard_session", token, max_age=settings.session_hours * 3600,
        httponly=True, secure=settings.cookie_secure, samesite="strict", path="/",
    )
    return {**user, "csrf_token": csrf}


@router.get("/session", response_model=SessionOut)
def session(user: Session):
    return user


@router.post("/logout", status_code=204)
def logout(user: Session, db: Db, response: Response):
    with db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (user["token_hash"],))
    response.delete_cookie("issueboard_session", path="/")