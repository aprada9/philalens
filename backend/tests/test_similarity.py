from pathlib import Path

from PIL import Image, ImageDraw

from philalens.models import StampCrop
from philalens.similarity import (
    crop_fingerprint,
    group_duplicate_crops,
    hamming_distance,
)


def _crop(crop_id: str, path: Path) -> StampCrop:
    return StampCrop(
        crop_id=crop_id,
        page_id="page_1",
        crop_index=1,
        bbox_xywh=(0, 0, 80, 100),
        crop_path=str(path),
        segmentation_confidence=0.9,
    )


def _stamp_image(path: Path, base: tuple[int, int, int], layout_seed: int = 0) -> None:
    image = Image.new("RGB", (80, 100), base)
    draw = ImageDraw.Draw(image)
    draw.rectangle([10 + layout_seed, 12, 60, 48], fill=(250, 250, 240))
    draw.ellipse([25, 55 + layout_seed, 55, 85], fill=(20, 20, 40))
    image.save(path, "JPEG", quality=92)


def test_identical_images_group_and_different_images_do_not(tmp_path: Path) -> None:
    _stamp_image(tmp_path / "a.jpg", (180, 40, 40))
    _stamp_image(tmp_path / "a2.jpg", (180, 40, 40))
    _stamp_image(tmp_path / "b.jpg", (40, 60, 200), layout_seed=10)

    crops = [
        _crop("a", tmp_path / "a.jpg"),
        _crop("b", tmp_path / "b.jpg"),
        _crop("a2", tmp_path / "a2.jpg"),
    ]
    groups = group_duplicate_crops(crops)
    grouped_ids = [[crop.crop_id for crop in group] for group in groups]
    assert grouped_ids == [["a", "a2"], ["b"]]


def test_same_design_different_color_stays_separate(tmp_path: Path) -> None:
    # Same structure, clearly different base color (one definitive series,
    # two denominations) must NOT be merged.
    _stamp_image(tmp_path / "red.jpg", (190, 50, 50))
    _stamp_image(tmp_path / "green.jpg", (50, 160, 60))

    groups = group_duplicate_crops(
        [_crop("red", tmp_path / "red.jpg"), _crop("green", tmp_path / "green.jpg")]
    )
    assert len(groups) == 2


def test_unreadable_images_become_singletons(tmp_path: Path) -> None:
    missing = _crop("missing", tmp_path / "nope.jpg")
    broken_path = tmp_path / "broken.jpg"
    broken_path.write_bytes(b"not a jpeg")
    broken = _crop("broken", broken_path)

    assert crop_fingerprint(missing) is None
    assert crop_fingerprint(broken) is None
    groups = group_duplicate_crops([missing, broken])
    assert [[crop.crop_id for crop in group] for group in groups] == [["missing"], ["broken"]]


def test_hamming_distance() -> None:
    assert hamming_distance(0b1010, 0b1010) == 0
    assert hamming_distance(0b1010, 0b0101) == 4
