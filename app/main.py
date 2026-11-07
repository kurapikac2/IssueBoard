from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database import initialize
from app.dependencies import json_only
from app.routers import auth, projects
from app.services.errors import ServiceError

STATIC = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize(settings.database)
        yield

    application = FastAPI(title="IssueBoard", version="1.0.0", lifespan=lifespan,
                          docs_url=None, redoc_url=None, dependencies=[Depends(json_only)])
    application.state.settings = settings
    application.include_router(auth.router)
    application.include_router(projects.router)

    @application.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        headers = {"Retry-After": "600"} if exc.status_code == 429 else None
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code, headers=headers)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Never echo rejected input: it can contain a password.
        errors = [{"field": ".".join(map(str, e["loc"][1:])), "message": e["msg"]}
                  for e in exc.errors()]
        return JSONResponse({"detail": "Проверьте поля формы.", "errors": errors}, status_code=422)

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    application.mount("/static", StaticFiles(directory=STATIC, check_dir=False), name="static")
    return application


app = create_app()