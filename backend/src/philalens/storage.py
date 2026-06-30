"""SQLite-backed local project storage."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .models import (
    REVIEW_NEEDS_CROP_REVIEW,
    CollectionRecord,
    PageImageRecord,
    StampCrop,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _load_list(value: str | None) -> list[str]:
    if not value:
        return []
    loaded = json.loads(value)
    return loaded if isinstance(loaded, list) else []


class PhilalensStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    collection_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    title TEXT
                );

                CREATE TABLE IF NOT EXISTS pages (
                    page_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL REFERENCES collections(collection_id)
                        ON DELETE CASCADE,
                    page_order INTEGER NOT NULL,
                    original_filename TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    normalized_path TEXT NOT NULL,
                    image_format TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    quality_warnings_json TEXT NOT NULL,
                    notes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS crops (
                    crop_id TEXT PRIMARY KEY,
                    page_id TEXT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
                    crop_index INTEGER NOT NULL,
                    bbox_x INTEGER NOT NULL,
                    bbox_y INTEGER NOT NULL,
                    bbox_w INTEGER NOT NULL,
                    bbox_h INTEGER NOT NULL,
                    rotation_degrees REAL NOT NULL DEFAULT 0,
                    crop_path TEXT NOT NULL,
                    segmentation_confidence REAL NOT NULL,
                    review_state TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_pages_collection_order
                    ON pages(collection_id, page_order);

                CREATE INDEX IF NOT EXISTS idx_crops_page_order
                    ON crops(page_id, crop_index);
                """
            )
            self._ensure_crop_rotation_column(connection)

    def create_collection(self, title: str | None = None) -> CollectionRecord:
        collection = CollectionRecord(
            collection_id=new_id("col"),
            created_at=utc_now(),
            title=title,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO collections (collection_id, created_at, title)
                VALUES (?, ?, ?)
                """,
                (collection.collection_id, collection.created_at, collection.title),
            )
        return collection

    def list_collections(self) -> list[CollectionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.collection_id,
                    c.created_at,
                    c.title,
                    COUNT(DISTINCT p.page_id) AS page_count,
                    COUNT(cr.crop_id) AS stamp_count,
                    COALESCE(SUM(CASE WHEN cr.review_state = ? THEN 1 ELSE 0 END), 0)
                        AS needs_crop_review_count
                FROM collections c
                LEFT JOIN pages p ON p.collection_id = c.collection_id
                LEFT JOIN crops cr ON cr.page_id = p.page_id
                GROUP BY c.collection_id
                ORDER BY c.created_at DESC
                """,
                (REVIEW_NEEDS_CROP_REVIEW,),
            ).fetchall()
        return [self._collection_from_row(row) for row in rows]

    def get_collection(self, collection_id: str) -> CollectionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    c.collection_id,
                    c.created_at,
                    c.title,
                    COUNT(DISTINCT p.page_id) AS page_count,
                    COUNT(cr.crop_id) AS stamp_count,
                    COALESCE(SUM(CASE WHEN cr.review_state = ? THEN 1 ELSE 0 END), 0)
                        AS needs_crop_review_count
                FROM collections c
                LEFT JOIN pages p ON p.collection_id = c.collection_id
                LEFT JOIN crops cr ON cr.page_id = p.page_id
                WHERE c.collection_id = ?
                GROUP BY c.collection_id
                """,
                (REVIEW_NEEDS_CROP_REVIEW, collection_id),
            ).fetchone()
        return self._collection_from_row(row) if row else None

    def add_page(self, page: PageImageRecord) -> PageImageRecord:
        page = replace(page, created_at=page.created_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pages (
                    page_id,
                    collection_id,
                    page_order,
                    original_filename,
                    original_path,
                    normalized_path,
                    image_format,
                    width,
                    height,
                    quality_warnings_json,
                    notes_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page.page_id,
                    page.collection_id,
                    page.page_order,
                    page.original_filename,
                    page.original_path,
                    page.normalized_path,
                    page.image_format,
                    page.width,
                    page.height,
                    _dump_json(page.quality_warnings),
                    _dump_json(page.notes),
                    page.created_at,
                ),
            )
        return page

    def replace_page_crops(self, page_id: str, crops: Iterable[StampCrop]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM crops WHERE page_id = ?", (page_id,))
            connection.executemany(
                """
                INSERT INTO crops (
                    crop_id,
                    page_id,
                    crop_index,
                    bbox_x,
                    bbox_y,
                    bbox_w,
                    bbox_h,
                    rotation_degrees,
                    crop_path,
                    segmentation_confidence,
                    review_state,
                    warnings_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        crop.crop_id,
                        crop.page_id,
                        crop.crop_index,
                        crop.bbox_xywh[0],
                        crop.bbox_xywh[1],
                        crop.bbox_xywh[2],
                        crop.bbox_xywh[3],
                        crop.rotation_degrees,
                        crop.crop_path,
                        crop.segmentation_confidence,
                        crop.review_state,
                        _dump_json(crop.warnings),
                        crop.created_at or utc_now(),
                    )
                    for crop in crops
                ],
            )

    def add_crop(self, crop: StampCrop) -> StampCrop:
        crop = replace(crop, created_at=crop.created_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO crops (
                    crop_id,
                    page_id,
                    crop_index,
                    bbox_x,
                    bbox_y,
                    bbox_w,
                    bbox_h,
                    rotation_degrees,
                    crop_path,
                    segmentation_confidence,
                    review_state,
                    warnings_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crop.crop_id,
                    crop.page_id,
                    crop.crop_index,
                    crop.bbox_xywh[0],
                    crop.bbox_xywh[1],
                    crop.bbox_xywh[2],
                    crop.bbox_xywh[3],
                    crop.rotation_degrees,
                    crop.crop_path,
                    crop.segmentation_confidence,
                    crop.review_state,
                    _dump_json(crop.warnings),
                    crop.created_at,
                ),
            )
        return crop

    def update_crop(self, crop: StampCrop) -> StampCrop:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE crops
                SET
                    bbox_x = ?,
                    bbox_y = ?,
                    bbox_w = ?,
                    bbox_h = ?,
                    rotation_degrees = ?,
                    crop_path = ?,
                    segmentation_confidence = ?,
                    review_state = ?,
                    warnings_json = ?
                WHERE crop_id = ?
                """,
                (
                    crop.bbox_xywh[0],
                    crop.bbox_xywh[1],
                    crop.bbox_xywh[2],
                    crop.bbox_xywh[3],
                    crop.rotation_degrees,
                    crop.crop_path,
                    crop.segmentation_confidence,
                    crop.review_state,
                    _dump_json(crop.warnings),
                    crop.crop_id,
                ),
            )
        return crop

    def delete_crop(self, crop_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM crops WHERE crop_id = ?", (crop_id,))
        return cursor.rowcount > 0

    def delete_page(self, page_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM pages WHERE page_id = ?", (page_id,))
        return cursor.rowcount > 0

    def next_crop_index(self, page_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(crop_index), 0) + 1 AS next_index FROM crops WHERE page_id = ?",
                (page_id,),
            ).fetchone()
        return int(row["next_index"])

    def get_page(self, page_id: str) -> PageImageRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM pages WHERE page_id = ?",
                (page_id,),
            ).fetchone()
        return self._page_from_row(row) if row else None

    def list_pages(self, collection_id: str) -> list[PageImageRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM pages
                WHERE collection_id = ?
                ORDER BY page_order ASC
                """,
                (collection_id,),
            ).fetchall()
        return [self._page_from_row(row) for row in rows]

    def get_crop(self, crop_id: str) -> StampCrop | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM crops WHERE crop_id = ?",
                (crop_id,),
            ).fetchone()
        return self._crop_from_row(row) if row else None

    def list_crops_for_page(self, page_id: str) -> list[StampCrop]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM crops
                WHERE page_id = ?
                ORDER BY crop_index ASC
                """,
                (page_id,),
            ).fetchall()
        return [self._crop_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _ensure_crop_rotation_column(connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(crops)").fetchall()
        }
        if "rotation_degrees" not in columns:
            connection.execute(
                "ALTER TABLE crops ADD COLUMN rotation_degrees REAL NOT NULL DEFAULT 0"
            )

    @staticmethod
    def _collection_from_row(row: sqlite3.Row) -> CollectionRecord:
        return CollectionRecord(
            collection_id=row["collection_id"],
            created_at=row["created_at"],
            title=row["title"],
            page_count=int(row["page_count"]),
            stamp_count=int(row["stamp_count"]),
            needs_crop_review_count=int(row["needs_crop_review_count"]),
        )

    @staticmethod
    def _page_from_row(row: sqlite3.Row) -> PageImageRecord:
        return PageImageRecord(
            page_id=row["page_id"],
            collection_id=row["collection_id"],
            page_order=int(row["page_order"]),
            original_filename=row["original_filename"],
            original_path=row["original_path"],
            normalized_path=row["normalized_path"],
            image_format=row["image_format"],
            width=int(row["width"]),
            height=int(row["height"]),
            quality_warnings=_load_list(row["quality_warnings_json"]),
            notes=_load_list(row["notes_json"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _crop_from_row(row: sqlite3.Row) -> StampCrop:
        return StampCrop(
            crop_id=row["crop_id"],
            page_id=row["page_id"],
            crop_index=int(row["crop_index"]),
            bbox_xywh=(
                int(row["bbox_x"]),
                int(row["bbox_y"]),
                int(row["bbox_w"]),
                int(row["bbox_h"]),
            ),
            crop_path=row["crop_path"],
            segmentation_confidence=float(row["segmentation_confidence"]),
            rotation_degrees=float(row["rotation_degrees"]),
            review_state=row["review_state"],
            warnings=_load_list(row["warnings_json"]),
            created_at=row["created_at"],
        )
