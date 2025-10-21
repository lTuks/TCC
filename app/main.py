
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.middleware.ratelimit import RateLimitMiddleware, make_key_func
from app.middleware.auth import auth_middleware
from app.config import settings
from app.db.session import init_db
from app.auth.routes import router as auth_router
from app.documents.routes import router as documents_router
from app.uploads.routes import router as upload_router
from app.web.routes_ui import router as ui_router
from app.tutor.routes import router as tutor_router

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        RateLimitMiddleware,
        window_seconds=settings.rate_limit_window_seconds,
        max_calls=settings.rate_limit_max_calls,
        key_func=make_key_func(settings.secret_key),
        include_path_prefixes=("/tools", "/upload"),
    )
    app.middleware("http")(auth_middleware)

    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(upload_router)
    app.include_router(ui_router)
    app.include_router(tutor_router)

    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

    @app.on_event("startup")
    def on_startup():
        init_db()

    @app.get("/", tags=["root"])
    def root():
        return {"name": settings.app_name, "env": settings.app_env}

    return app

app = create_app()