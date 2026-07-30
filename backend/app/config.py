"""應用程式設定：支援 SQLite（本地）與 PostgreSQL（Docker）雙軌資料庫。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CASMS API"
    database_url: str = "sqlite:///./casms.db"
    secret_key: str = "casms-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    seed_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
