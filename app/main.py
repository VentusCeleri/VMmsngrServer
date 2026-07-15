import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import auth, devices, health, messages, pairs, tasks, users, ws
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.db.session import engine
from app.realtime.manager import realtime_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger = logging.getLogger("vmmsngr")
    logger.info("Application startup complete", extra={"environment": settings.environment})
    try:
        yield
    finally:
        logger.info("Application shutdown started")
        await realtime_manager.close_all(code=1001)
        engine.dispose()
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    configure_logging()
    logging.getLogger("vmmsngr").info("Starting VMmsngrServer", extra={"environment": settings.environment})
    app = FastAPI(
        title="VMmsngrServer",
        description="Local MVP backend for VMmsngr family messenger/organizer.",
        version="1.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.allowed_host_list and settings.allowed_host_list != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(users.router)
    app.include_router(pairs.router)
    app.include_router(tasks.router)
    app.include_router(messages.router)
    app.include_router(ws.router)
    return app


app = create_app()
