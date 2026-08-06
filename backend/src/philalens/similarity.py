"""Local perceptual-hash near-duplicate grouping for stamp crops.

Album collections often contain several copies of the same stamp. Grouping
near-duplicates lets an evaluation run make one vision call per group and fan
the result out, cutting API cost. Grouping is deliberately conservative:
stamps from the same series share a design and differ only in numerals and
color, so a structure-only hash match is confirmed with a mean-color check.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat

from .models import StampCrop

# Hamming distance (out of 64 bits) at or below which two crops are considered
# structural near-duplicates, before the color check.
DEFAULT_MAX_HASH_DISTANCE = 6

# Maximum per-channel mean RGB difference for near-duplicates. Guards against
# same-design different-color stamps from one definitive series.
DEFAULT_MAX_COLOR_DISTANCE = 24.0


@dataclass(frozen=True)
class CropFingerprint:
    crop: StampCrop
    dhash_bits: int
    mean_rgb: tuple[float, float, float]


def crop_fingerprint(crop: StampCrop) -> CropFingerprint | None:
    """Return a fingerprint for the crop image, or None if unreadable."""

    path = Path(crop.crop_path)
    if not path.is_file():
        return None
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            gray = rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(gray.tobytes())
            mean = ImageStat.Stat(rgb).mean
    except OSError:
        return None

    bits = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)

    mean_rgb = (float(mean[0]), float(mean[1]), float(mean[2]))
    return CropFingerprint(crop=crop, dhash_bits=bits, mean_rgb=mean_rgb)


def hamming_distance(first: int, second: int) -> int:
    return (first ^ second).bit_count()


def color_distance(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    return max(abs(a - b) for a, b in zip(first, second, strict=True))


def group_duplicate_crops(
    crops: list[StampCrop],
    *,
    max_hash_distance: int = DEFAULT_MAX_HASH_DISTANCE,
    max_color_distance: float = DEFAULT_MAX_COLOR_DISTANCE,
) -> list[list[StampCrop]]:
    """Group crops into near-duplicate clusters, preserving input order.

    Each returned group lists the representative (earliest) crop first.
    Unreadable crop images become single-member groups. Greedy assignment:
    a crop joins the first group whose representative it matches.
    """

    groups: list[list[StampCrop]] = []
    representatives: list[CropFingerprint | None] = []

    for crop in crops:
        fingerprint = crop_fingerprint(crop)
        matched = False
        if fingerprint is not None:
            for index, representative in enumerate(representatives):
                if representative is None:
                    continue
                if (
                    hamming_distance(fingerprint.dhash_bits, representative.dhash_bits)
                    <= max_hash_distance
                    and color_distance(fingerprint.mean_rgb, representative.mean_rgb)
                    <= max_color_distance
                ):
                    groups[index].append(crop)
                    matched = True
                    break
        if not matched:
            groups.append([crop])
            representatives.append(fingerprint)

    return groups
