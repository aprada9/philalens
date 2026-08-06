"""Strict schemas for AI-visible stamp observations and identity priors."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import CatalogCandidateRecord, StampObservationRecord
from .storage import new_id

OBSERVATION_SCHEMA_VERSION: Literal["stamp-observation-v1"] = "stamp-observation-v1"
OBSERVATION_SCHEMA_V2_VERSION: Literal["stamp-observation-v2"] = "stamp-observation-v2"

AI_PRIOR_SOURCE_NAME = "ai_vision_prior"

PriorValueBucket = Literal["likely_common", "possibly_interesting", "investigate"]

CancellationState = Literal[
    "unknown",
    "unused_or_mint",
    "used_light_cancel",
    "used_heavy_cancel",
    "cancelled_unclear",
]
CenteringAssessment = Literal[
    "unknown",
    "well_centered",
    "slightly_off_center",
    "noticeably_off_center",
    "cut_into_design",
]

DEFAULT_UNOBSERVABLE_FACTORS = [
    "watermark",
    "paper",
    "gum",
    "reverse_condition",
    "hidden_thins",
    "hidden_repairs",
    "regumming",
    "perforation_gauge",
    "authenticity",
]


class StrictStampObservation(BaseModel):
    """Model-facing observation contract for one stamp crop.

    This is intentionally about visible observations, not final catalog identity
    or value. Candidate matching and valuation should consume this schema later.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

    schema_version: Literal["stamp-observation-v1"] = OBSERVATION_SCHEMA_VERSION
    visible_text: list[str] = Field(default_factory=list)
    issuer_hint: str | None = None
    denomination_hint: str | None = None
    currency_hint: str | None = None
    date_hint: str | None = None
    design_subject: str | None = None
    color_hints: list[str] = Field(default_factory=list)
    cancellation_state: CancellationState = "unknown"
    centering: CenteringAssessment = "unknown"
    margin_notes: list[str] = Field(default_factory=list)
    perforation_observations: list[str] = Field(default_factory=list)
    visible_faults: list[str] = Field(default_factory=list)
    condition_notes: list[str] = Field(default_factory=list)
    image_quality_warnings: list[str] = Field(default_factory=list)
    unobservable_factors: list[str] = Field(
        default_factory=lambda: DEFAULT_UNOBSERVABLE_FACTORS.copy()
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    observation_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "issuer_hint",
        "denomination_hint",
        "currency_hint",
        "date_hint",
        "design_subject",
        mode="before",
    )
    @classmethod
    def _blank_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "visible_text",
        "color_hints",
        "margin_notes",
        "perforation_observations",
        "visible_faults",
        "condition_notes",
        "image_quality_warnings",
        "unobservable_factors",
        "observation_notes",
    )
    @classmethod
    def _clean_string_list(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized = item.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key not in seen:
                cleaned.append(normalized)
                seen.add(key)
        return cleaned

    @field_validator("unobservable_factors")
    @classmethod
    def _ensure_default_unobservables(cls, value: list[str]) -> list[str]:
        factors = list(value)
        existing = {item.casefold() for item in factors}
        for factor in DEFAULT_UNOBSERVABLE_FACTORS:
            if factor.casefold() not in existing:
                factors.append(factor)
                existing.add(factor.casefold())
        return factors


class IdentityCandidate(BaseModel):
    """One candidate identity for the stamp, proposed from model knowledge.

    This is a prior, not source-backed evidence. Catalog hints are free-text
    approximations (e.g. "Michel NL ~500-535 range") and must never be
    presented as verified catalog numbers.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

    country: str
    series_or_issue: str | None = None
    year_range: str | None = None
    denomination: str | None = None
    catalog_hint: str | None = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    rationale: str | None = None

    @field_validator(
        "series_or_issue",
        "year_range",
        "denomination",
        "catalog_hint",
        "rationale",
        mode="before",
    )
    @classmethod
    def _blank_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class StrictStampObservationV2(StrictStampObservation):
    """V2 adds identity priors and a value-triage bucket to the observation.

    Identification and triage are model priors from a front photo. They rank
    attention; they are not source-backed identifications or appraisals.
    """

    schema_version: Literal["stamp-observation-v2"] = OBSERVATION_SCHEMA_V2_VERSION  # type: ignore[assignment]
    identity_candidates: list[IdentityCandidate] = Field(default_factory=list)
    prior_value_bucket: PriorValueBucket = "likely_common"
    prior_value_rationale: str | None = None

    @field_validator("identity_candidates")
    @classmethod
    def _cap_candidates(cls, value: list[IdentityCandidate]) -> list[IdentityCandidate]:
        ranked = sorted(value, key=lambda candidate: candidate.confidence, reverse=True)
        return ranked[:3]

    @field_validator("prior_value_rationale", mode="before")
    @classmethod
    def _blank_rationale_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@dataclass(frozen=True)
class VisionAnalysisResult:
    """Composite result of one vision call over one crop."""

    observation: StampObservationRecord
    candidates: list[CatalogCandidateRecord] = field(default_factory=list)
    prior_value_bucket: str | None = None
    prior_value_rationale: str | None = None


def parse_stamp_observation_payload(payload: str | Mapping[str, Any]) -> StrictStampObservation:
    """Parse JSON or mapping output from a vision adapter."""

    if isinstance(payload, str):
        loaded = json.loads(payload)
    else:
        loaded = dict(payload)
    if not isinstance(loaded, dict):
        raise TypeError("Stamp observation payload must be a JSON object.")
    if loaded.get("schema_version") == OBSERVATION_SCHEMA_V2_VERSION:
        return StrictStampObservationV2.model_validate(loaded)
    return StrictStampObservation.model_validate(loaded)


def stamp_observation_json_schema() -> dict[str, Any]:
    """Return the JSON schema to pass to a structured-output vision adapter."""

    return StrictStampObservationV2.model_json_schema()


def observation_to_record(
    observation: StrictStampObservation,
    run_id: str,
    crop_id: str,
    *,
    observation_id: str | None = None,
    adapter_name: str = "strict_observation_schema",
    model_name: str | None = None,
) -> StampObservationRecord:
    """Convert a validated observation into the durable storage record."""

    structured_condition = {
        "centering": observation.centering,
        "margin_notes": observation.margin_notes,
        "perforation_observations": observation.perforation_observations,
        "visible_faults": observation.visible_faults,
    }
    condition_notes = list(observation.condition_notes)
    condition_notes.extend(f"visible_fault: {fault}" for fault in observation.visible_faults)
    condition_notes.extend(
        f"perforation_observation: {note}" for note in observation.perforation_observations
    )
    condition_notes.extend(f"margin_note: {note}" for note in observation.margin_notes)

    return StampObservationRecord(
        observation_id=observation_id or new_id("obs"),
        run_id=run_id,
        crop_id=crop_id,
        visible_text=observation.visible_text,
        issuer_hint=observation.issuer_hint,
        denomination_hint=observation.denomination_hint,
        date_hint=observation.date_hint,
        design_subject=observation.design_subject,
        color_hints=observation.color_hints,
        cancellation_state=observation.cancellation_state,
        condition_notes=condition_notes,
        image_quality_warnings=observation.image_quality_warnings,
        unobservable_factors=observation.unobservable_factors,
        confidence=observation.confidence,
        model_metadata={
            "adapter": adapter_name,
            "schema_version": observation.schema_version,
            "model_name": model_name,
            "currency_hint": observation.currency_hint,
            "observation_notes": observation.observation_notes,
            "structured_condition": structured_condition,
        },
    )


def analysis_from_observation(
    observation: StrictStampObservation,
    run_id: str,
    crop_id: str,
    *,
    adapter_name: str = "strict_observation_schema",
    model_name: str | None = None,
) -> VisionAnalysisResult:
    """Convert a validated observation (v1 or v2) into durable analysis records."""

    record = observation_to_record(
        observation,
        run_id=run_id,
        crop_id=crop_id,
        adapter_name=adapter_name,
        model_name=model_name,
    )
    if not isinstance(observation, StrictStampObservationV2):
        return VisionAnalysisResult(observation=record)

    candidates = [
        _candidate_to_record(candidate, rank, run_id, crop_id)
        for rank, candidate in enumerate(observation.identity_candidates, start=1)
    ]
    return VisionAnalysisResult(
        observation=record,
        candidates=candidates,
        prior_value_bucket=observation.prior_value_bucket,
        prior_value_rationale=observation.prior_value_rationale,
    )


def _candidate_to_record(
    candidate: IdentityCandidate,
    rank: int,
    run_id: str,
    crop_id: str,
) -> CatalogCandidateRecord:
    variant_notes: list[str] = []
    if candidate.year_range:
        variant_notes.append(f"year_range: {candidate.year_range}")
    if candidate.catalog_hint:
        variant_notes.append(f"catalog_hint (unverified): {candidate.catalog_hint}")
    if candidate.rationale:
        variant_notes.append(f"rationale: {candidate.rationale}")

    return CatalogCandidateRecord(
        candidate_id=new_id("cand"),
        run_id=run_id,
        crop_id=crop_id,
        source_name=AI_PRIOR_SOURCE_NAME,
        catalog_id=None,
        issuer=candidate.country,
        title=candidate.series_or_issue or candidate.country,
        year=_first_year(candidate.year_range),
        denomination=candidate.denomination,
        variant_notes=variant_notes,
        match_score=candidate.confidence,
        rank=rank,
        contradiction_warnings=["ai_prior_without_source_evidence"],
    )


def _first_year(year_range: str | None) -> int | None:
    if not year_range:
        return None
    match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", year_range)
    return int(match.group(1)) if match else None


def validation_error_messages(error: ValidationError) -> list[str]:
    """Return compact validation messages for API/UI surfaces."""

    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"])
        messages.append(f"{location}: {item['msg']}")
    return messages
