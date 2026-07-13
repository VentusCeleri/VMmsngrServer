from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, messages, pairs, tasks
from app.core.config import settings
from app.core.errors import install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="VMmsngrServer",
        description="Local MVP backend for VMmsngr family messenger/organizer.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(pairs.router)
    app.include_router(tasks.router)
    app.include_router(messages.router)
    return app


app = create_app()
