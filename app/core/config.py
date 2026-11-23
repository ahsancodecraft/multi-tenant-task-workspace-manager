import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppConfig(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    DATABASE_URL: str = "sqlite:///./task_manager.db"
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    ANALYTICS_CACHE_TTL_SECONDS: int = 60
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DevelopmentConfig(BaseAppConfig):
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class TestConfig(BaseAppConfig):
    APP_ENV: str = "test"
    DEBUG: bool = True
    LOG_LEVEL: str = "WARNING"


class ProductionConfig(BaseAppConfig):
    APP_ENV: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


def get_settings() -> BaseAppConfig:
    env = os.getenv("APP_ENV", "development").strip().lower()
    if env == "production":
        return ProductionConfig()
    if env == "test":
        return TestConfig()
    return DevelopmentConfig()


settings = get_settings()