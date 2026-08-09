"""Runtime configuration for Philalens.

Every ``Settings()`` instantiation reads the current process environment, so
settings changes made at runtime (e.g. via the settings endpoint writing
``os.environ``) take effect without a server restart. The repository ``.env``
file is loaded once at import time without overriding variables that are
already set in the environment.
"""

from dataclasses import dataclass, field
from os import environ, getenv
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


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into the environment without overriding set vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in environ:
            environ[key] = value


load_env_file(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: _getenv("PHILALENS_APP_NAME", "Philalens"))
    data_dir: Path = field(
        default_factory=lambda: Path(
            _getenv("PHILALENS_DATA_DIR", str(PROJECT_ROOT / "data" / "local"))
        )
    )
    max_upload_files: int = field(
        default_factory=lambda: int(_getenv("PHILALENS_MAX_UPLOAD_FILES", "120"))
    )
    stamp_detector: str = field(
        default_factory=lambda: _getenv("PHILALENS_STAMP_DETECTOR", "auto").lower()
    )
    stamp_yolo_confidence: float = field(
        default_factory=lambda: float(_getenv("PHILALENS_STAMP_YOLO_CONFIDENCE", "0.1"))
    )
    stamp_crop_margin_percent: float = field(
        default_factory=lambda: float(_getenv("PHILALENS_STAMP_CROP_MARGIN_PERCENT", "0.02"))
    )
    catalog_db_url: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_CATALOG_DB_URL")
    )
    market_data_provider: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_MARKET_DATA_PROVIDER")
    )
    market_data_api_key: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_MARKET_DATA_API_KEY")
    )
    vision_provider: str = field(
        default_factory=lambda: _getenv("PHILALENS_VISION_PROVIDER", "none").lower()
    )
    openai_api_key: str | None = field(default_factory=lambda: _getenv_optional("OPENAI_API_KEY"))
    openai_vision_model: str = field(
        default_factory=lambda: _getenv("PHILALENS_OPENAI_VISION_MODEL", "gpt-4.1-mini")
    )
    openai_vision_detail: str = field(
        default_factory=lambda: _getenv("PHILALENS_OPENAI_VISION_DETAIL", "high")
    )
    vision_concurrency: int = field(
        default_factory=lambda: max(1, int(_getenv("PHILALENS_VISION_CONCURRENCY", "4")))
    )
    ebay_app_id: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_EBAY_APP_ID")
    )
    ebay_cert_id: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_EBAY_CERT_ID")
    )
    ebay_marketplace: str = field(
        default_factory=lambda: _getenv("PHILALENS_EBAY_MARKETPLACE", "EBAY_US")
    )
    ebay_environment: str = field(
        default_factory=lambda: _getenv("PHILALENS_EBAY_ENVIRONMENT", "production").lower()
    )
    hipstamp_api_key: str | None = field(
        default_factory=lambda: _getenv_optional("PHILALENS_HIPSTAMP_API_KEY")
    )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "philalens.sqlite"

    @property
    def collections_dir(self) -> Path:
        return self.data_dir / "collections"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def stamp_yolo_model_path(self) -> Path:
        return Path(
            _getenv(
                "PHILALENS_STAMP_YOLO_MODEL_PATH",
                str(self.data_dir / "models" / "code2k13-philately-tool-model.pt"),
            )
        )


def get_settings() -> Settings:
    """Return settings reflecting the current process environment."""
    return Settings()
