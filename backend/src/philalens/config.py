"""Runtime configuration for Philalens."""

from dataclasses import dataclass, field
from os import getenv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _getenv(name: str, default: str) -> str:
    value = getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _getenv_optional(name: str) -> str | None:
    value = getenv(name)
    if value is None or value.strip() == "":
        return None
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = _getenv("PHILALENS_APP_NAME", "Philalens")
    data_dir: Path = field(
        default_factory=lambda: Path(
            _getenv("PHILALENS_DATA_DIR", str(PROJECT_ROOT / "data" / "local"))
        )
    )
    max_upload_files: int = int(_getenv("PHILALENS_MAX_UPLOAD_FILES", "120"))
    stamp_detector: str = _getenv("PHILALENS_STAMP_DETECTOR", "auto").lower()
    stamp_yolo_confidence: float = float(_getenv("PHILALENS_STAMP_YOLO_CONFIDENCE", "0.1"))
    stamp_crop_margin_percent: float = float(_getenv("PHILALENS_STAMP_CROP_MARGIN_PERCENT", "0.02"))
    catalog_db_url: str | None = _getenv_optional("PHILALENS_CATALOG_DB_URL")
    market_data_provider: str | None = _getenv_optional("PHILALENS_MARKET_DATA_PROVIDER")
    market_data_api_key: str | None = _getenv_optional("PHILALENS_MARKET_DATA_API_KEY")
    vision_provider: str = _getenv("PHILALENS_VISION_PROVIDER", "none").lower()
    openai_api_key: str | None = _getenv_optional("OPENAI_API_KEY")
    openai_vision_model: str = _getenv("PHILALENS_OPENAI_VISION_MODEL", "gpt-4.1-mini")
    openai_vision_detail: str = _getenv("PHILALENS_OPENAI_VISION_DETAIL", "high")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "philalens.sqlite"

    @property
    def collections_dir(self) -> Path:
        return self.data_dir / "collections"

    @property
    def stamp_yolo_model_path(self) -> Path:
        return Path(
            _getenv(
                "PHILALENS_STAMP_YOLO_MODEL_PATH",
                str(self.data_dir / "models" / "code2k13-philately-tool-model.pt"),
            )
        )


settings = Settings()
