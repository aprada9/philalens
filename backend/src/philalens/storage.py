"""SQLite-backed local project storage."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    EVALUATION_STATUS_PENDING,
    REVIEW_NEEDS_CROP_REVIEW,
    CatalogCandidateRecord,
    CollectionRecord,
    EmbeddingRecord,
    EvaluationRunRecord,
    PageImageRecord,
    SourceEvidenceRecord,
    StampCrop,
    StampObservationRecord,
    StampValuationRecord,
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


def _load_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {}


def _load_float_list(value: str | None) -> list[float]:
    if not value:
        return []
    loaded = json.loads(value)
    return [float(item) for item in loaded] if isinstance(loaded, list) else []


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

                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL REFERENCES collections(collection_id)
                        ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    pipeline_version TEXT NOT NULL,
                    vision_model TEXT,
                    embedding_model TEXT,
                    enabled_sources_json TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stamp_observations (
                    observation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
                    crop_id TEXT NOT NULL REFERENCES crops(crop_id) ON DELETE CASCADE,
                    visible_text_json TEXT NOT NULL,
                    issuer_hint TEXT,
                    denomination_hint TEXT,
                    date_hint TEXT,
                    design_subject TEXT,
                    color_hints_json TEXT NOT NULL,
                    cancellation_state TEXT,
                    condition_notes_json TEXT NOT NULL,
                    image_quality_warnings_json TEXT NOT NULL,
                    unobservable_factors_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    model_metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS catalog_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
                    crop_id TEXT NOT NULL REFERENCES crops(crop_id) ON DELETE CASCADE,
                    source_name TEXT NOT NULL,
                    source_record_id TEXT,
                    catalog_id TEXT,
                    issuer TEXT,
                    title TEXT,
                    year INTEGER,
                    denomination TEXT,
                    variant_notes_json TEXT NOT NULL,
                    match_score REAL NOT NULL,
                    candidate_rank INTEGER NOT NULL,
                    supporting_evidence_ids_json TEXT NOT NULL,
                    contradiction_warnings_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
                    crop_id TEXT NOT NULL REFERENCES crops(crop_id) ON DELETE CASCADE,
                    candidate_id TEXT REFERENCES catalog_candidates(candidate_id)
                        ON DELETE SET NULL,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT,
                    local_reference_id TEXT,
                    retrieved_at TEXT,
                    matched_fields_json TEXT NOT NULL,
                    price_low REAL,
                    price_high REAL,
                    price REAL,
                    currency TEXT,
                    condition_assumptions TEXT,
                    evidence_tier TEXT,
                    confidence REAL NOT NULL,
                    license_notes TEXT,
                    raw_payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stamp_valuations (
                    valuation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
                    crop_id TEXT NOT NULL REFERENCES crops(crop_id) ON DELETE CASCADE,
                    candidate_id TEXT REFERENCES catalog_candidates(candidate_id)
                        ON DELETE SET NULL,
                    estimated_value_low REAL,
                    estimated_value_high REAL,
                    currency TEXT NOT NULL,
                    identity_confidence REAL NOT NULL,
                    condition_confidence REAL NOT NULL,
                    market_evidence_confidence REAL NOT NULL,
                    valuation_confidence REAL NOT NULL,
                    value_bucket TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL,
                    uncertainty_warnings_json TEXT NOT NULL,
                    recommended_next_action TEXT,
                    evidence_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS embedding_index (
                    embedding_id TEXT PRIMARY KEY,
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    embedding_dimension INTEGER NOT NULL,
                    embedding_vector_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_pages_collection_order
                    ON pages(collection_id, page_order);

                CREATE INDEX IF NOT EXISTS idx_crops_page_order
                    ON crops(page_id, crop_index);

                CREATE INDEX IF NOT EXISTS idx_evaluation_runs_collection_started
                    ON evaluation_runs(collection_id, started_at DESC);

                CREATE INDEX IF NOT EXISTS idx_observations_run_crop
                    ON stamp_observations(run_id, crop_id);

                CREATE INDEX IF NOT EXISTS idx_candidates_run_crop_rank
                    ON catalog_candidates(run_id, crop_id, candidate_rank);

                CREATE INDEX IF NOT EXISTS idx_evidence_run_crop
                    ON source_evidence(run_id, crop_id);

                CREATE INDEX IF NOT EXISTS idx_valuations_run_crop
                    ON stamp_valuations(run_id, crop_id);

                CREATE INDEX IF NOT EXISTS idx_embedding_owner
                    ON embedding_index(owner_type, owner_id, model_name);
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

    def create_evaluation_run(
        self,
        collection_id: str,
        pipeline_version: str,
        status: str = EVALUATION_STATUS_PENDING,
        vision_model: str | None = None,
        embedding_model: str | None = None,
        enabled_sources: list[str] | None = None,
        settings: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> EvaluationRunRecord:
        run = EvaluationRunRecord(
            run_id=new_id("run"),
            collection_id=collection_id,
            status=status,
            started_at=utc_now(),
            pipeline_version=pipeline_version,
            vision_model=vision_model,
            embedding_model=embedding_model,
            enabled_sources=enabled_sources or [],
            settings=settings or {},
            warnings=warnings or [],
            errors=errors or [],
        )
        return self.add_evaluation_run(run)

    def add_evaluation_run(self, run: EvaluationRunRecord) -> EvaluationRunRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_runs (
                    run_id,
                    collection_id,
                    status,
                    started_at,
                    finished_at,
                    pipeline_version,
                    vision_model,
                    embedding_model,
                    enabled_sources_json,
                    settings_json,
                    warnings_json,
                    errors_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.collection_id,
                    run.status,
                    run.started_at,
                    run.finished_at,
                    run.pipeline_version,
                    run.vision_model,
                    run.embedding_model,
                    _dump_json(run.enabled_sources),
                    _dump_json(run.settings),
                    _dump_json(run.warnings),
                    _dump_json(run.errors),
                ),
            )
        return run

    def update_evaluation_run(self, run: EvaluationRunRecord) -> EvaluationRunRecord:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE evaluation_runs
                SET
                    status = ?,
                    started_at = ?,
                    finished_at = ?,
                    pipeline_version = ?,
                    vision_model = ?,
                    embedding_model = ?,
                    enabled_sources_json = ?,
                    settings_json = ?,
                    warnings_json = ?,
                    errors_json = ?
                WHERE run_id = ?
                """,
                (
                    run.status,
                    run.started_at,
                    run.finished_at,
                    run.pipeline_version,
                    run.vision_model,
                    run.embedding_model,
                    _dump_json(run.enabled_sources),
                    _dump_json(run.settings),
                    _dump_json(run.warnings),
                    _dump_json(run.errors),
                    run.run_id,
                ),
            )
        return run

    def list_evaluation_runs(self, collection_id: str) -> list[EvaluationRunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM evaluation_runs
                WHERE collection_id = ?
                ORDER BY started_at DESC, run_id DESC
                """,
                (collection_id,),
            ).fetchall()
        return [self._evaluation_run_from_row(row) for row in rows]

    def get_evaluation_run(self, run_id: str) -> EvaluationRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM evaluation_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return self._evaluation_run_from_row(row) if row else None

    def get_latest_evaluation_run(self, collection_id: str) -> EvaluationRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM evaluation_runs
                WHERE collection_id = ?
                ORDER BY started_at DESC, run_id DESC
                LIMIT 1
                """,
                (collection_id,),
            ).fetchone()
        return self._evaluation_run_from_row(row) if row else None

    def add_stamp_observation(self, observation: StampObservationRecord) -> StampObservationRecord:
        observation = replace(observation, created_at=observation.created_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stamp_observations (
                    observation_id,
                    run_id,
                    crop_id,
                    visible_text_json,
                    issuer_hint,
                    denomination_hint,
                    date_hint,
                    design_subject,
                    color_hints_json,
                    cancellation_state,
                    condition_notes_json,
                    image_quality_warnings_json,
                    unobservable_factors_json,
                    confidence,
                    model_metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.observation_id,
                    observation.run_id,
                    observation.crop_id,
                    _dump_json(observation.visible_text),
                    observation.issuer_hint,
                    observation.denomination_hint,
                    observation.date_hint,
                    observation.design_subject,
                    _dump_json(observation.color_hints),
                    observation.cancellation_state,
                    _dump_json(observation.condition_notes),
                    _dump_json(observation.image_quality_warnings),
                    _dump_json(observation.unobservable_factors),
                    observation.confidence,
                    _dump_json(observation.model_metadata),
                    observation.created_at,
                ),
            )
        return observation

    def list_stamp_observations_for_run(self, run_id: str) -> list[StampObservationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM stamp_observations
                WHERE run_id = ?
                ORDER BY created_at ASC, observation_id ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._stamp_observation_from_row(row) for row in rows]

    def get_stamp_observation_for_crop(
        self, run_id: str, crop_id: str
    ) -> StampObservationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM stamp_observations
                WHERE run_id = ? AND crop_id = ?
                ORDER BY created_at DESC, observation_id DESC
                LIMIT 1
                """,
                (run_id, crop_id),
            ).fetchone()
        return self._stamp_observation_from_row(row) if row else None

    def add_catalog_candidate(self, candidate: CatalogCandidateRecord) -> CatalogCandidateRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO catalog_candidates (
                    candidate_id,
                    run_id,
                    crop_id,
                    source_name,
                    source_record_id,
                    catalog_id,
                    issuer,
                    title,
                    year,
                    denomination,
                    variant_notes_json,
                    match_score,
                    candidate_rank,
                    supporting_evidence_ids_json,
                    contradiction_warnings_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.run_id,
                    candidate.crop_id,
                    candidate.source_name,
                    candidate.source_record_id,
                    candidate.catalog_id,
                    candidate.issuer,
                    candidate.title,
                    candidate.year,
                    candidate.denomination,
                    _dump_json(candidate.variant_notes),
                    candidate.match_score,
                    candidate.rank,
                    _dump_json(candidate.supporting_evidence_ids),
                    _dump_json(candidate.contradiction_warnings),
                ),
            )
        return candidate

    def list_catalog_candidates_for_run(self, run_id: str) -> list[CatalogCandidateRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM catalog_candidates
                WHERE run_id = ?
                ORDER BY crop_id ASC, candidate_rank ASC, match_score DESC
                """,
                (run_id,),
            ).fetchall()
        return [self._catalog_candidate_from_row(row) for row in rows]

    def list_catalog_candidates_for_crop(
        self, run_id: str, crop_id: str
    ) -> list[CatalogCandidateRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM catalog_candidates
                WHERE run_id = ? AND crop_id = ?
                ORDER BY candidate_rank ASC, match_score DESC
                """,
                (run_id, crop_id),
            ).fetchall()
        return [self._catalog_candidate_from_row(row) for row in rows]

    def add_source_evidence(self, evidence: SourceEvidenceRecord) -> SourceEvidenceRecord:
        evidence = replace(evidence, retrieved_at=evidence.retrieved_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO source_evidence (
                    evidence_id,
                    run_id,
                    crop_id,
                    candidate_id,
                    source_name,
                    source_type,
                    source_url,
                    local_reference_id,
                    retrieved_at,
                    matched_fields_json,
                    price_low,
                    price_high,
                    price,
                    currency,
                    condition_assumptions,
                    evidence_tier,
                    confidence,
                    license_notes,
                    raw_payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.run_id,
                    evidence.crop_id,
                    evidence.candidate_id,
                    evidence.source_name,
                    evidence.source_type,
                    evidence.source_url,
                    evidence.local_reference_id,
                    evidence.retrieved_at,
                    _dump_json(evidence.matched_fields),
                    evidence.price_low,
                    evidence.price_high,
                    evidence.price,
                    evidence.currency,
                    evidence.condition_assumptions,
                    evidence.evidence_tier,
                    evidence.confidence,
                    evidence.license_notes,
                    _dump_json(evidence.raw_payload),
                ),
            )
        return evidence

    def list_source_evidence_for_run(self, run_id: str) -> list[SourceEvidenceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM source_evidence
                WHERE run_id = ?
                ORDER BY retrieved_at ASC, evidence_id ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._source_evidence_from_row(row) for row in rows]

    def list_source_evidence_for_crop(
        self, run_id: str, crop_id: str
    ) -> list[SourceEvidenceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM source_evidence
                WHERE run_id = ? AND crop_id = ?
                ORDER BY retrieved_at ASC, evidence_id ASC
                """,
                (run_id, crop_id),
            ).fetchall()
        return [self._source_evidence_from_row(row) for row in rows]

    def add_stamp_valuation(self, valuation: StampValuationRecord) -> StampValuationRecord:
        valuation = replace(valuation, created_at=valuation.created_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stamp_valuations (
                    valuation_id,
                    run_id,
                    crop_id,
                    candidate_id,
                    estimated_value_low,
                    estimated_value_high,
                    currency,
                    identity_confidence,
                    condition_confidence,
                    market_evidence_confidence,
                    valuation_confidence,
                    value_bucket,
                    assumptions_json,
                    uncertainty_warnings_json,
                    recommended_next_action,
                    evidence_ids_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    valuation.valuation_id,
                    valuation.run_id,
                    valuation.crop_id,
                    valuation.candidate_id,
                    valuation.estimated_value_low,
                    valuation.estimated_value_high,
                    valuation.currency,
                    valuation.identity_confidence,
                    valuation.condition_confidence,
                    valuation.market_evidence_confidence,
                    valuation.valuation_confidence,
                    valuation.value_bucket,
                    _dump_json(valuation.assumptions),
                    _dump_json(valuation.uncertainty_warnings),
                    valuation.recommended_next_action,
                    _dump_json(valuation.evidence_ids),
                    valuation.created_at,
                ),
            )
        return valuation

    def list_stamp_valuations_for_run(self, run_id: str) -> list[StampValuationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM stamp_valuations
                WHERE run_id = ?
                ORDER BY created_at ASC, valuation_id ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._stamp_valuation_from_row(row) for row in rows]

    def get_stamp_valuation_for_crop(
        self, run_id: str, crop_id: str
    ) -> StampValuationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM stamp_valuations
                WHERE run_id = ? AND crop_id = ?
                ORDER BY created_at DESC, valuation_id DESC
                LIMIT 1
                """,
                (run_id, crop_id),
            ).fetchone()
        return self._stamp_valuation_from_row(row) if row else None

    def add_embedding(self, embedding: EmbeddingRecord) -> EmbeddingRecord:
        embedding = replace(embedding, created_at=embedding.created_at or utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO embedding_index (
                    embedding_id,
                    owner_type,
                    owner_id,
                    model_name,
                    embedding_dimension,
                    embedding_vector_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    embedding.embedding_id,
                    embedding.owner_type,
                    embedding.owner_id,
                    embedding.model_name,
                    embedding.embedding_dimension,
                    _dump_json(embedding.embedding_vector),
                    embedding.created_at,
                ),
            )
        return embedding

    def list_embeddings_for_owner(
        self, owner_type: str, owner_id: str, model_name: str | None = None
    ) -> list[EmbeddingRecord]:
        query = """
            SELECT * FROM embedding_index
            WHERE owner_type = ? AND owner_id = ?
        """
        params: tuple[str, ...] = (owner_type, owner_id)
        if model_name is not None:
            query += " AND model_name = ?"
            params = (owner_type, owner_id, model_name)
        query += " ORDER BY created_at DESC, embedding_id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._embedding_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _ensure_crop_rotation_column(connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(crops)").fetchall()
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

    @staticmethod
    def _evaluation_run_from_row(row: sqlite3.Row) -> EvaluationRunRecord:
        return EvaluationRunRecord(
            run_id=row["run_id"],
            collection_id=row["collection_id"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            pipeline_version=row["pipeline_version"],
            vision_model=row["vision_model"],
            embedding_model=row["embedding_model"],
            enabled_sources=_load_list(row["enabled_sources_json"]),
            settings=_load_dict(row["settings_json"]),
            warnings=_load_list(row["warnings_json"]),
            errors=_load_list(row["errors_json"]),
        )

    @staticmethod
    def _stamp_observation_from_row(row: sqlite3.Row) -> StampObservationRecord:
        return StampObservationRecord(
            observation_id=row["observation_id"],
            run_id=row["run_id"],
            crop_id=row["crop_id"],
            visible_text=_load_list(row["visible_text_json"]),
            issuer_hint=row["issuer_hint"],
            denomination_hint=row["denomination_hint"],
            date_hint=row["date_hint"],
            design_subject=row["design_subject"],
            color_hints=_load_list(row["color_hints_json"]),
            cancellation_state=row["cancellation_state"],
            condition_notes=_load_list(row["condition_notes_json"]),
            image_quality_warnings=_load_list(row["image_quality_warnings_json"]),
            unobservable_factors=_load_list(row["unobservable_factors_json"]),
            confidence=float(row["confidence"]),
            model_metadata=_load_dict(row["model_metadata_json"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _catalog_candidate_from_row(row: sqlite3.Row) -> CatalogCandidateRecord:
        return CatalogCandidateRecord(
            candidate_id=row["candidate_id"],
            run_id=row["run_id"],
            crop_id=row["crop_id"],
            source_name=row["source_name"],
            source_record_id=row["source_record_id"],
            catalog_id=row["catalog_id"],
            issuer=row["issuer"],
            title=row["title"],
            year=int(row["year"]) if row["year"] is not None else None,
            denomination=row["denomination"],
            variant_notes=_load_list(row["variant_notes_json"]),
            match_score=float(row["match_score"]),
            rank=int(row["candidate_rank"]),
            supporting_evidence_ids=_load_list(row["supporting_evidence_ids_json"]),
            contradiction_warnings=_load_list(row["contradiction_warnings_json"]),
        )

    @staticmethod
    def _source_evidence_from_row(row: sqlite3.Row) -> SourceEvidenceRecord:
        return SourceEvidenceRecord(
            evidence_id=row["evidence_id"],
            run_id=row["run_id"],
            crop_id=row["crop_id"],
            candidate_id=row["candidate_id"],
            source_name=row["source_name"],
            source_type=row["source_type"],
            source_url=row["source_url"],
            local_reference_id=row["local_reference_id"],
            retrieved_at=row["retrieved_at"],
            matched_fields=_load_dict(row["matched_fields_json"]),
            price_low=float(row["price_low"]) if row["price_low"] is not None else None,
            price_high=float(row["price_high"]) if row["price_high"] is not None else None,
            price=float(row["price"]) if row["price"] is not None else None,
            currency=row["currency"],
            condition_assumptions=row["condition_assumptions"],
            evidence_tier=row["evidence_tier"],
            confidence=float(row["confidence"]),
            license_notes=row["license_notes"],
            raw_payload=_load_dict(row["raw_payload_json"]),
        )

    @staticmethod
    def _stamp_valuation_from_row(row: sqlite3.Row) -> StampValuationRecord:
        return StampValuationRecord(
            valuation_id=row["valuation_id"],
            run_id=row["run_id"],
            crop_id=row["crop_id"],
            candidate_id=row["candidate_id"],
            estimated_value_low=(
                float(row["estimated_value_low"])
                if row["estimated_value_low"] is not None
                else None
            ),
            estimated_value_high=(
                float(row["estimated_value_high"])
                if row["estimated_value_high"] is not None
                else None
            ),
            currency=row["currency"],
            identity_confidence=float(row["identity_confidence"]),
            condition_confidence=float(row["condition_confidence"]),
            market_evidence_confidence=float(row["market_evidence_confidence"]),
            valuation_confidence=float(row["valuation_confidence"]),
            value_bucket=row["value_bucket"],
            assumptions=_load_list(row["assumptions_json"]),
            uncertainty_warnings=_load_list(row["uncertainty_warnings_json"]),
            recommended_next_action=row["recommended_next_action"],
            evidence_ids=_load_list(row["evidence_ids_json"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _embedding_from_row(row: sqlite3.Row) -> EmbeddingRecord:
        return EmbeddingRecord(
            embedding_id=row["embedding_id"],
            owner_type=row["owner_type"],
            owner_id=row["owner_id"],
            model_name=row["model_name"],
            embedding_dimension=int(row["embedding_dimension"]),
            embedding_vector=_load_float_list(row["embedding_vector_json"]),
            created_at=row["created_at"],
        )
