"""Core data models for stamp analysis results."""

from dataclasses import dataclass, field
from typing import Any

REVIEW_UNREVIEWED = "unreviewed"
REVIEW_NEEDS_CROP_REVIEW = "needs_crop_review"
REVIEW_NEEDS_BETTER_IMAGE = "needs_better_image"
REVIEW_CANDIDATE_CONFIRMED = "candidate_confirmed"
REVIEW_CANDIDATE_REJECTED = "candidate_rejected"
REVIEW_EXPERT_REVIEW_RECOMMENDED = "expert_review_recommended"
REVIEW_VALUATION_READY = "valuation_ready"

EVALUATION_STATUS_PENDING = "pending"
EVALUATION_STATUS_RUNNING = "running"
EVALUATION_STATUS_COMPLETED = "completed"
EVALUATION_STATUS_FAILED = "failed"
EVALUATION_STATUS_INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class CollectionRecord:
    collection_id: str
    created_at: str
    title: str | None = None
    page_count: int = 0
    stamp_count: int = 0
    needs_crop_review_count: int = 0


@dataclass(frozen=True)
class PageImageRecord:
    page_id: str
    collection_id: str
    page_order: int
    original_filename: str
    original_path: str
    normalized_path: str
    image_format: str
    width: int
    height: int
    quality_warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass(frozen=True)
class StampCrop:
    crop_id: str
    page_id: str
    crop_index: int
    bbox_xywh: tuple[int, int, int, int]
    crop_path: str
    segmentation_confidence: float
    rotation_degrees: float = 0.0
    review_state: str = REVIEW_UNREVIEWED
    warnings: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass(frozen=True)
class EvaluationRunRecord:
    run_id: str
    collection_id: str
    status: str
    started_at: str
    pipeline_version: str
    finished_at: str | None = None
    vision_model: str | None = None
    embedding_model: str | None = None
    enabled_sources: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StampObservationRecord:
    observation_id: str
    run_id: str
    crop_id: str
    visible_text: list[str] = field(default_factory=list)
    issuer_hint: str | None = None
    denomination_hint: str | None = None
    date_hint: str | None = None
    design_subject: str | None = None
    color_hints: list[str] = field(default_factory=list)
    cancellation_state: str | None = None
    condition_notes: list[str] = field(default_factory=list)
    image_quality_warnings: list[str] = field(default_factory=list)
    unobservable_factors: list[str] = field(default_factory=list)
    confidence: float = 0.0
    model_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class CatalogCandidateRecord:
    candidate_id: str
    run_id: str
    crop_id: str
    source_name: str
    source_record_id: str | None = None
    catalog_id: str | None = None
    issuer: str | None = None
    title: str | None = None
    year: int | None = None
    denomination: str | None = None
    variant_notes: list[str] = field(default_factory=list)
    match_score: float = 0.0
    rank: int = 0
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradiction_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceEvidenceRecord:
    evidence_id: str
    run_id: str
    crop_id: str
    source_name: str
    source_type: str
    candidate_id: str | None = None
    source_url: str | None = None
    local_reference_id: str | None = None
    retrieved_at: str | None = None
    matched_fields: dict[str, Any] = field(default_factory=dict)
    price_low: float | None = None
    price_high: float | None = None
    price: float | None = None
    currency: str | None = None
    condition_assumptions: str | None = None
    evidence_tier: str | None = None
    confidence: float = 0.0
    license_notes: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StampValuationRecord:
    valuation_id: str
    run_id: str
    crop_id: str
    candidate_id: str | None = None
    estimated_value_low: float | None = None
    estimated_value_high: float | None = None
    currency: str = "USD"
    identity_confidence: float = 0.0
    condition_confidence: float = 0.0
    market_evidence_confidence: float = 0.0
    valuation_confidence: float = 0.0
    value_bucket: str = "not_enough_evidence"
    assumptions: list[str] = field(default_factory=list)
    uncertainty_warnings: list[str] = field(default_factory=list)
    recommended_next_action: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str | None = None
