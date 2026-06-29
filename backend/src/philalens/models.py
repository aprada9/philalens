"""Core data models for stamp analysis results."""

from dataclasses import dataclass, field


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
    visible_text: list[str] = field(default_factory=list)
    country_hint: str | None = None
    denomination_hint: str | None = None
    color_hints: list[str] = field(default_factory=list)
    condition_notes: list[str] = field(default_factory=list)


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
    stamps: list[StampAssessment] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CollectionSummary:
    page_count: int
    stamp_count: int
    estimated_value_low: float | None
    estimated_value_high: float | None
    currency: str = "USD"

