from pathlib import Path

import cv2
import numpy as np

from philalens.segmentation import detect_stamp_crops, recrop_stamp


def test_detect_stamp_crops_finds_synthetic_regions(tmp_path: Path) -> None:
    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (70, 80), (210, 290), (235, 235, 235), -1)
    cv2.rectangle(image, (280, 85), (430, 285), (220, 220, 220), -1)
    cv2.rectangle(image, (520, 100), (680, 315), (245, 245, 245), -1)

    page_path = tmp_path / "page.jpg"
    assert cv2.imwrite(str(page_path), image)

    result = detect_stamp_crops("page_1", page_path, tmp_path / "crops")

    assert len(result.crops) == 3
    assert result.warnings == []
    assert all(Path(crop.crop_path).exists() for crop in result.crops)
    assert all(crop.segmentation_confidence >= 0.7 for crop in result.crops)


def test_detect_stamp_crops_falls_back_when_yolo_model_missing(tmp_path: Path) -> None:
    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (70, 80), (210, 290), (235, 235, 235), -1)

    page_path = tmp_path / "page.jpg"
    assert cv2.imwrite(str(page_path), image)

    result = detect_stamp_crops(
        "page_1",
        page_path,
        tmp_path / "crops",
        detector="yolo",
        yolo_model_path=tmp_path / "missing-model.pt",
    )

    assert result.detector == "opencv"
    assert "yolo_detector_model_missing" in result.warnings
    assert len(result.crops) == 1


def test_recrop_stamp_persists_rotation_and_writes_crop(tmp_path: Path) -> None:
    image = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.rectangle(image, (140, 90), (260, 210), (235, 235, 235), -1)

    page_path = tmp_path / "page.jpg"
    assert cv2.imwrite(str(page_path), image)

    crop = recrop_stamp(
        page_id="page_1",
        crop_id="crop_1",
        crop_index=1,
        normalized_image_path=page_path,
        crop_dir=tmp_path / "crops",
        bbox_xywh=(130, 80, 140, 150),
        rotation_degrees=22.25,
    )

    assert crop.rotation_degrees == 22.25
    assert Path(crop.crop_path).exists()
    written = cv2.imread(crop.crop_path)
    assert written is not None
    assert written.shape[0] > 0
    assert written.shape[1] > 0
