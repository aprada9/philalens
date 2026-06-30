"""Runtime configuration for Philalens."""

from dataclasses import dataclass, field
from os import getenv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("PHILALENS_APP_NAME", "Philalens")
    data_dir: Path = field(
        default_factory=lambda: Path(getenv("PHILALENS_DATA_DIR", PROJECT_ROOT / "data" / "local"))
    )
    max_upload_files: int = int(getenv("PHILALENS_MAX_UPLOAD_FILES", "120"))
    stamp_detector: str = getenv("PHILALENS_STAMP_DETECTOR", "auto").lower()
    stamp_yolo_confidence: float = float(getenv("PHILALENS_STAMP_YOLO_CONFIDENCE", "0.1"))
    stamp_crop_margin_percent: float = float(getenv("PHILALENS_STAMP_CROP_MARGIN_PERCENT", "0.02"))
    catalog_db_url: str | None = getenv("PHILALENS_CATALOG_DB_URL")
    market_data_provider: str | None = getenv("PHILALENS_MARKET_DATA_PROVIDER")
    market_data_api_key: str | None = getenv("PHILALENS_MARKET_DATA_API_KEY")
    openai_api_key: str | None = getenv("OPENAI_API_KEY")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "philalens.sqlite"

    @property
    def collections_dir(self) -> Path:
        return self.data_dir / "collections"

    @property
    def stamp_yolo_model_path(self) -> Path:
        return Path(
            getenv(
                "PHILALENS_STAMP_YOLO_MODEL_PATH",
                self.data_dir / "models" / "code2k13-philately-tool-model.pt",
            )
        )


settings = Settings()
