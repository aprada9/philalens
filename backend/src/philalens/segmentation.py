"""Automatic stamp-region detection for album page photos."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from math import cos, radians, sin
from os import environ
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .models import REVIEW_NEEDS_CROP_REVIEW, REVIEW_UNREVIEWED, StampCrop
from .storage import new_id

_yolo_model_cache: dict[str, Any] = {}


@dataclass(frozen=True)
class DetectionBox:
    bbox_xywh: tuple[int, int, int, int]
    confidence: float | None = None
    source: str = "opencv"


@dataclass(frozen=True)
class SegmentationResult:
    crops: list[StampCrop]
    warnings: list[str]
    detector: str = "opencv"


# Detections with no geometry warnings are review-flagged only below this
# confidence. YOLO scores correct stamp detections at 0.4-0.65 routinely, so
# a higher bar (the original 0.7) flooded the review queue with fine crops:
# on the user's full 241-page collection it flagged 1,383 warning-free crops,
# ~87% of which were kept unchanged during calibration curation.
REVIEW_CONFIDENCE_BAR = 0.45


def detect_stamp_crops(
    page_id: str,
    normalized_image_path: Path,
    crop_dir: Path,
    detector: str = "auto",
    yolo_model_path: Path | None = None,
    yolo_confidence: float = 0.1,
    margin_percent: float = 0.02,
) -> SegmentationResult:
    image = cv2.imread(str(normalized_image_path))
    if image is None:
        return SegmentationResult(crops=[], warnings=["normalized_image_unreadable"])

    height, width = image.shape[:2]
    detections, detector_used, detector_warnings = _detect_boxes(
        image=image,
        normalized_image_path=normalized_image_path,
        image_width=width,
        image_height=height,
        detector=detector,
        yolo_model_path=yolo_model_path,
        yolo_confidence=yolo_confidence,
        margin_percent=margin_percent,
    )
    detections = _dedupe_boxes(detections)

    crops: list[StampCrop] = []
    crop_dir.mkdir(parents=True, exist_ok=True)

    for index, detection in enumerate(_sort_boxes(detections), start=1):
        box = detection.bbox_xywh
        # The padded box is both written to disk and stored as bbox_xywh, so the
        # stored box always describes the saved crop image's exact pixels.
        padded = _pad_box(box, width, height)
        crop_path = crop_dir / f"{page_id}_stamp_{index:03d}.jpg"
        _write_crop(image, padded, crop_path)

        # Warnings/confidence describe the raw detection box, not the padding.
        warnings = _box_warnings(box, width, height)
        if detection.confidence is not None and detection.confidence < 0.35:
            warnings.append("low_detector_confidence")
        confidence = _box_confidence(
            box,
            warnings,
            width,
            height,
            detector_confidence=detection.confidence,
        )
        review_state = (
            REVIEW_NEEDS_CROP_REVIEW
            if warnings or confidence < REVIEW_CONFIDENCE_BAR
            else REVIEW_UNREVIEWED
        )

        crops.append(
            StampCrop(
                crop_id=new_id("crop"),
                page_id=page_id,
                crop_index=index,
                bbox_xywh=padded,
                crop_path=str(crop_path),
                segmentation_confidence=confidence,
                review_state=review_state,
                warnings=warnings,
            )
        )

    page_warnings: list[str] = []
    page_warnings.extend(detector_warnings)
    if not crops:
        page_warnings.append("no_stamp_regions_detected")
    if len(crops) > 120:
        page_warnings.append("unusually_many_stamp_regions_detected")

    return SegmentationResult(crops=crops, warnings=page_warnings, detector=detector_used)


def recrop_stamp(
    page_id: str,
    crop_id: str,
    crop_index: int,
    normalized_image_path: Path,
    crop_dir: Path,
    bbox_xywh: tuple[int, int, int, int],
    rotation_degrees: float = 0.0,
) -> StampCrop:
    image = cv2.imread(str(normalized_image_path))
    if image is None:
        raise ValueError("normalized_image_unreadable")

    height, width = image.shape[:2]
    box = _clamp_box(bbox_xywh, width, height)
    rotation_degrees = _normalize_rotation(rotation_degrees)
    crop_dir.mkdir(parents=True, exist_ok=True)
    crop_path = crop_dir / f"{page_id}_stamp_{crop_index:03d}_manual.jpg"
    # User-drawn boxes are authoritative: write exactly the clamped box so the
    # stored bbox always matches the saved crop image.
    _write_crop(image, box, crop_path, rotation_degrees)

    warnings = _box_warnings(box, width, height)
    confidence = max(0.75, _box_confidence(box, warnings, width, height))
    return StampCrop(
        crop_id=crop_id,
        page_id=page_id,
        crop_index=crop_index,
        bbox_xywh=box,
        crop_path=str(crop_path),
        segmentation_confidence=confidence,
        rotation_degrees=rotation_degrees,
        review_state=REVIEW_UNREVIEWED if not warnings else REVIEW_NEEDS_CROP_REVIEW,
        warnings=warnings,
    )


def _scaled_for_processing(image: np.ndarray, max_side: int = 2200) -> tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    longest_side = max(width, height)
    if longest_side <= max_side:
        return image, 1.0

    scale = max_side / longest_side
    resized = cv2.resize(image, (round(width * scale), round(height * scale)))
    return resized, scale


def _detect_boxes(
    image: np.ndarray,
    normalized_image_path: Path,
    image_width: int,
    image_height: int,
    detector: str,
    yolo_model_path: Path | None,
    yolo_confidence: float,
    margin_percent: float,
) -> tuple[list[DetectionBox], str, list[str]]:
    detector = detector.lower()
    warnings: list[str] = []

    if detector not in {"auto", "opencv", "yolo"}:
        warnings.append(f"unknown_detector_{detector}")
        detector = "auto"

    if detector in {"auto", "yolo"} and yolo_model_path is not None:
        if yolo_model_path.exists():
            try:
                detections = _find_yolo_boxes(
                    normalized_image_path=normalized_image_path,
                    yolo_model_path=yolo_model_path,
                    confidence=yolo_confidence,
                    margin_percent=margin_percent,
                    image_width=image_width,
                    image_height=image_height,
                )
                if detections:
                    return detections, "yolo", warnings
                warnings.append("yolo_detector_returned_no_boxes")
            except RuntimeError as exc:
                warnings.append(str(exc))
        elif detector == "yolo":
            warnings.append("yolo_detector_model_missing")

    processing_image, scale = _scaled_for_processing(image)
    return _find_opencv_candidate_boxes(processing_image, scale, image_width, image_height), "opencv", warnings


def _find_yolo_boxes(
    normalized_image_path: Path,
    yolo_model_path: Path,
    confidence: float,
    margin_percent: float,
    image_width: int,
    image_height: int,
) -> list[DetectionBox]:
    cache_dir = yolo_model_path.parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    environ.setdefault("YOLO_CONFIG_DIR", str(cache_dir / "ultralytics"))
    environ.setdefault("MPLCONFIGDIR", str(cache_dir / "matplotlib"))

    try:
        ultralytics = import_module("ultralytics")
    except ModuleNotFoundError as exc:
        raise RuntimeError("yolo_detector_dependency_missing") from exc

    cache_key = str(yolo_model_path.resolve())
    model = _yolo_model_cache.get(cache_key)
    if model is None:
        model = ultralytics.YOLO(str(yolo_model_path))
        _yolo_model_cache[cache_key] = model
    result = model(str(normalized_image_path), conf=confidence, verbose=False)[0]
    if result.boxes is None:
        return []

    detections: list[DetectionBox] = []
    for box in result.boxes:
        xyxy = _tensor_to_list(box.xyxy[0])
        model_confidence = float(_tensor_to_list(box.conf)[0]) if box.conf is not None else None
        bbox = _xyxy_to_xywh_with_margin(
            xyxy=xyxy,
            image_width=image_width,
            image_height=image_height,
            margin_percent=margin_percent,
        )
        detections.append(
            DetectionBox(
                bbox_xywh=bbox,
                confidence=model_confidence,
                source="yolo",
            )
        )

    return detections


def _find_opencv_candidate_boxes(
    image: np.ndarray,
    scale: float,
    original_width: int,
    original_height: int,
) -> list[DetectionBox]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    bright_ratio = float(np.count_nonzero(mask)) / float(mask.size)
    if bright_ratio > 0.65:
        mask = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            51,
            7,
        )

    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[DetectionBox] = []
    original_area = original_width * original_height
    min_area = max(900, original_area * 0.0007)
    max_area = original_area * 0.16

    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if scale != 1.0:
            x = round(x / scale)
            y = round(y / scale)
            width = round(width / scale)
            height = round(height / scale)

        box = _clamp_box((x, y, width, height), original_width, original_height)
        _, _, box_width, box_height = box
        area = box_width * box_height
        aspect_ratio = box_width / max(1, box_height)

        if area < min_area or area > max_area:
            continue
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            continue

        boxes.append(DetectionBox(bbox_xywh=box, source="opencv"))

    return boxes


def _dedupe_boxes(boxes: list[DetectionBox]) -> list[DetectionBox]:
    kept: list[DetectionBox] = []
    for box in sorted(boxes, key=lambda item: item.bbox_xywh[2] * item.bbox_xywh[3], reverse=True):
        if all(
            _intersection_over_union(box.bbox_xywh, kept_box.bbox_xywh) < 0.55
            for kept_box in kept
        ):
            kept.append(box)
    return kept


def _sort_boxes(boxes: list[DetectionBox]) -> list[DetectionBox]:
    return sorted(boxes, key=lambda box: (box.bbox_xywh[1] // 80, box.bbox_xywh[0]))


def _box_warnings(box: tuple[int, int, int, int], image_width: int, image_height: int) -> list[str]:
    x, y, width, height = box
    warnings: list[str] = []
    area_ratio = (width * height) / max(1, image_width * image_height)
    aspect_ratio = width / max(1, height)

    if x <= 2 or y <= 2 or x + width >= image_width - 2 or y + height >= image_height - 2:
        warnings.append("touches_image_edge")
    if area_ratio > 0.075:
        warnings.append("large_region_may_include_multiple_stamps")
    if area_ratio < 0.0012:
        warnings.append("small_region_may_be_noise_or_partial_stamp")
    if aspect_ratio < 0.45 or aspect_ratio > 2.2:
        warnings.append("unusual_stamp_aspect_ratio")

    return warnings


def _box_confidence(
    box: tuple[int, int, int, int],
    warnings: list[str],
    image_width: int,
    image_height: int,
    detector_confidence: float | None = None,
) -> float:
    if detector_confidence is not None:
        confidence = detector_confidence
        confidence -= len(warnings) * 0.1
        return round(min(0.98, max(0.2, confidence)), 2)

    _, _, width, height = box
    area_ratio = (width * height) / max(1, image_width * image_height)
    aspect_ratio = width / max(1, height)
    confidence = 0.86

    if 0.002 <= area_ratio <= 0.04:
        confidence += 0.06
    else:
        confidence -= 0.08

    if 0.6 <= aspect_ratio <= 1.7:
        confidence += 0.04
    else:
        confidence -= 0.08

    confidence -= len(warnings) * 0.13
    return round(min(0.96, max(0.2, confidence)), 2)


def _pad_box(
    box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
    padding: int = 12,
) -> tuple[int, int, int, int]:
    x, y, width, height = box
    padded_x = max(0, x - padding)
    padded_y = max(0, y - padding)
    right = min(image_width, x + width + padding)
    bottom = min(image_height, y + height + padding)
    return padded_x, padded_y, right - padded_x, bottom - padded_y


def _clamp_box(
    box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    x, y, width, height = box
    x = min(max(0, int(x)), image_width - 1)
    y = min(max(0, int(y)), image_height - 1)
    width = min(max(1, int(width)), image_width - x)
    height = min(max(1, int(height)), image_height - y)
    return x, y, width, height


def _xyxy_to_xywh_with_margin(
    xyxy: list[float],
    image_width: int,
    image_height: int,
    margin_percent: float,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = xyxy
    width = x2 - x1
    height = y2 - y1
    margin_x = width * margin_percent
    margin_y = height * margin_percent
    return _clamp_box(
        (
            round(x1 - margin_x),
            round(y1 - margin_y),
            round(width + 2 * margin_x),
            round(height + 2 * margin_y),
        ),
        image_width,
        image_height,
    )


def _tensor_to_list(value: Any) -> list[float]:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    if hasattr(value, "tolist"):
        result = value.tolist()
    else:
        result = value
    if isinstance(result, list):
        return [float(item) for item in result]
    return [float(result)]


def _write_crop(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    crop_path: Path,
    rotation_degrees: float = 0.0,
) -> None:
    x, y, width, height = box
    rotation_degrees = _normalize_rotation(rotation_degrees)
    if abs(rotation_degrees) < 0.01:
        crop = image[y : y + height, x : x + width]
    else:
        crop = _rotated_crop(image, box, rotation_degrees)
    cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])


def _rotated_crop(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    rotation_degrees: float,
) -> np.ndarray:
    x, y, width, height = box
    center_x = x + width / 2
    center_y = y + height / 2
    theta = radians(rotation_degrees)
    x_axis = np.array([cos(theta), sin(theta)], dtype=np.float32)
    y_axis = np.array([-sin(theta), cos(theta)], dtype=np.float32)
    center = np.array([center_x, center_y], dtype=np.float32)
    half_width = width / 2
    half_height = height / 2
    source = np.array(
        [
            center - x_axis * half_width - y_axis * half_height,
            center + x_axis * half_width - y_axis * half_height,
            center + x_axis * half_width + y_axis * half_height,
            center - x_axis * half_width + y_axis * half_height,
        ],
        dtype=np.float32,
    )
    destination = np.array(
        [
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1],
        ],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(
        image,
        transform,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _normalize_rotation(rotation_degrees: float) -> float:
    rotation = ((float(rotation_degrees) + 180) % 360) - 180
    return round(rotation, 2)


def _intersection_over_union(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second

    left = max(first_x, second_x)
    top = max(first_y, second_y)
    right = min(first_x + first_width, second_x + second_width)
    bottom = min(first_y + first_height, second_y + second_height)
    intersection_width = max(0, right - left)
    intersection_height = max(0, bottom - top)
    intersection = intersection_width * intersection_height

    first_area = first_width * first_height
    second_area = second_width * second_height
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0
