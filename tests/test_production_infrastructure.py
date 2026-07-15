from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


ROOT = Path(__file__).resolve().parents[1]


def production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "debug": False,
        "allowed_hosts": "api.example.com",
        "cors_origins": "https://api.example.com",
        "database_url": "postgresql+psycopg2://vmmsngr:strong-postgres-password-123456@db:5432/vmmsngr",
        "postgres_db": "vmmsngr",
        "postgres_user": "vmmsngr",
        "postgres_password": "strong-postgres-password-123456",
        "jwt_secret_key": "a" * 64,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_accept_safe_values() -> None:
    settings = production_settings()

    assert settings.environment == "production"
    assert settings.debug is False


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"debug": True}, "DEBUG must be false"),
        ({"jwt_secret_key": "change-me-in-local-env"}, "JWT_SECRET_KEY"),
        ({"jwt_secret_key": "short"}, "JWT_SECRET_KEY"),
        ({"database_url": "postgresql+psycopg2://vmmsngr:password@localhost:5432/vmmsngr"}, "DATABASE_URL"),
        ({"postgres_password": "vmmsngr"}, "POSTGRES_PASSWORD"),
        ({"allowed_hosts": "*"}, "ALLOWED_HOSTS"),
    ],
)
def test_production_settings_reject_unsafe_values(override: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**override)


def test_production_compose_does_not_publish_postgres_port() -> None:
    compose = (ROOT / "docker-compose.prod.yml").read_text()

    db_section = compose.split("  api:", 1)[0]
    assert "5432:5432" not in db_section
    assert "ports:" not in db_section


def test_production_compose_binds_api_to_loopback_only() -> None:
    compose = (ROOT / "docker-compose.prod.yml").read_text()

    assert '"127.0.0.1:8000:8000"' in compose
    assert '"8000:8000"' not in compose
    assert "--reload" not in compose
    assert ".:/app" not in compose


def test_alembic_has_single_linear_head() -> None:
    versions = ROOT / "alembic" / "versions"
    revisions: dict[str, str | None] = {}

    for file_path in versions.glob("*.py"):
        namespace: dict = {}
        exec(file_path.read_text(), namespace)
        revisions[namespace["revision"]] = namespace["down_revision"]

    children = {down_revision for down_revision in revisions.values() if down_revision is not None}
    heads = set(revisions) - children

    assert heads == {"0005_push_notifications"}
    assert revisions["0002_task_priority_string"] == "0001_initial_schema"
    assert revisions["0003_profiles_presence"] == "0002_task_priority_string"
    assert revisions["0004_pair_management"] == "0003_profiles_presence"
    assert revisions["0005_push_notifications"] == "0004_pair_management"
