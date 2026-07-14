from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
            db.execute(text("select version_num from alembic_version limit 1"))
    except SQLAlchemyError:
        return HealthResponse(status="not_ready", service=settings.app_name)
    return HealthResponse(status="ready", service=settings.app_name)
