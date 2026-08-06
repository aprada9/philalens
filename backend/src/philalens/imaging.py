"""Image intake and normalization helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_IMAGE_EXTENSIONS = {
    ".heic",
    ".heif",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


@dataclass(frozen=True)
class NormalizedImage:
    original_path: Path
    normalized_path: Path
    image_format: str
    width: int
    height: int
    warnings: list[str] = field(default_factory=list)


def safe_filename(filename: str | None, fallback: str) -> str:
    stem = filename or fallback
    stem = stem.strip().replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem).strip(" .")
    return cleaned or fallback


def supported_image_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def register_heic_support() -> bool:
    try:
        from pillow_heif import register_heif_opener  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        return False

    register_heif_opener()
    return True


def normalize_image(original_path: Path, normalized_path: Path) -> NormalizedImage:
    warnings: list[str] = []
    original_path = original_path.resolve()
    normalized_path = normalized_path.resolve()
    suffix = original_path.suffix.lower()

    heic_enabled = register_heic_support()
    if suffix in {".heic", ".heif"} and not heic_enabled:
        raise RuntimeError(
            "HEIC support requires the pillow-heif package. Install backend dependencies "
            'with `pip install -e ".[dev]"` before importing HEIC photos.'
        )

    try:
        with Image.open(original_path) as image:
            image_format = image.format or suffix.lstrip(".").upper()
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            width, height = normalized.size
            normalized_path.parent.mkdir(parents=True, exist_ok=True)
            normalized.save(normalized_path, format="JPEG", quality=94, optimize=True)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or unreadable image: {original_path.name}") from exc

    if min(width, height) < 1000:
        warnings.append("low_resolution_image")
    if max(width, height) / max(1, min(width, height)) > 2.2:
        warnings.append("unusual_page_aspect_ratio")

    return NormalizedImage(
        original_path=original_path,
        normalized_path=normalized_path,
        image_format=image_format,
        width=width,
        height=height,
        warnings=warnings,
    )
