"""Core data models for stamp analysis results."""

from dataclasses import dataclass, field


REVIEW_UNREVIEWED = "unreviewed"
REVIEW_NEEDS_CROP_REVIEW = "needs_crop_review"
REVIEW_NEEDS_BETTER_IMAGE = "needs_better_image"
REVIEW_CANDIDATE_CONFIRMED = "candidate_confirmed"
REVIEW_CANDIDATE_REJECTED = "candidate_rejected"
REVIEW_EXPERT_REVIEW_RECOMMENDED = "expert_review_recommended"
REVIEW_VALUATION_READY = "valuation_ready"


@dataclass(frozen=True)
class Evidence:
    source: str
    summary: str
    url: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class StampObservation:
    crop_id: str
    page_id: str
    bbox_xywh: tuple[int, int, int, int] | None = None
    crop_image_path: str | None = None
    segmentation_confidence: float | None = None
    review_state: str = REVIEW_UNREVIEWED
    segmentation_warnings: list[str] = field(default_factory=list)
    visible_text: list[str] = field(default_factory=list)
    country_hint: str | None = None
    denomination_hint: str | None = None
    color_hints: list[str] = field(default_factory=list)
    condition_notes: list[str] = field(default_factory=list)
    description: str | None = None


@dataclass(frozen=True)
class CatalogCandidate:
    title: str
    catalog_id: str | None = None
    issuer: str | None = None
    year: int | None = None
    confidence: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class StampAssessment:
    observation: StampObservation
    candidates: list[CatalogCandidate] = field(default_factory=list)
    estimated_value_low: float | None = None
    estimated_value_high: float | None = None
    currency: str = "USD"
    valuation_confidence: float = 0.0
    valuation_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PageAnalysis:
    page_id: str
    image_filename: str
    normalized_image_path: str | None = None
    width: int | None = None
    height: int | None = None
    stamps: list[StampAssessment] = field(default_factory=list)
    quality_warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CollectionSummary:
    page_count: int
    stamp_count: int
    estimated_value_low: float | None
    estimated_value_high: float | None
    currency: str = "USD"
    needs_crop_review_count: int = 0


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
