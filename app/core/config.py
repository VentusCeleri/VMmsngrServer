from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionConfigurationError(ValueError):
    pass


class Settings(BaseSettings):
    app_name: str = "VMmsngrServer"
    environment: str = "local"
    debug: bool = True
    log_level: str = "INFO"
    allowed_hosts: str = "*"

    database_url: str = "postgresql+psycopg2://vmmsngr:vmmsngr@localhost:5432/vmmsngr"
    postgres_db: str = "vmmsngr"
    postgres_user: str = "vmmsngr"
    postgres_password: str = "vmmsngr"

    jwt_secret_key: str = Field(default="change-me-in-local-env")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_auth_max_requests: int = 8
    rate_limit_pair_join_max_requests: int = 12
    rate_limit_messages_max_requests: int = 30

    apns_enabled: bool = False
    apns_environment: str = "sandbox"
    apns_team_id: str = ""
    apns_key_id: str = ""
    apns_bundle_id: str = "com.maxvika.VMmsngr"
    apns_private_key_path: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production":
            weak_secrets = {"", "change-me-in-local-env", "change-me", "secret", "dev-secret", "test", "vmmsngr"}
            weak_passwords = {"", "vmmsngr", "postgres", "password", "change-me", "secret", "test"}
            if self.debug:
                raise ProductionConfigurationError("DEBUG must be false when ENVIRONMENT=production")
            if self.jwt_secret_key in weak_secrets or len(self.jwt_secret_key) < 32:
                raise ProductionConfigurationError("JWT_SECRET_KEY must be at least 32 characters and non-default in production")
            if self.postgres_password in weak_passwords or len(self.postgres_password) < 24:
                raise ProductionConfigurationError("POSTGRES_PASSWORD must be strong and non-default in production")

            parsed_database_url = urlparse(self.database_url)
            if parsed_database_url.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ProductionConfigurationError("DATABASE_URL must not use localhost inside production Docker")
            if not self.database_url:
                raise ProductionConfigurationError("DATABASE_URL is required in production")
            if self.allowed_host_list == ["*"]:
                raise ProductionConfigurationError("ALLOWED_HOSTS must be explicit in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
