"""Runtime configuration for Philalens."""

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("PHILALENS_APP_NAME", "Philalens")
    catalog_db_url: str | None = getenv("PHILALENS_CATALOG_DB_URL")
    market_data_provider: str | None = getenv("PHILALENS_MARKET_DATA_PROVIDER")
    market_data_api_key: str | None = getenv("PHILALENS_MARKET_DATA_API_KEY")
    openai_api_key: str | None = getenv("OPENAI_API_KEY")


settings = Settings()

