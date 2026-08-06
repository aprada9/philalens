"""Strict schema for AI-visible stamp observations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import StampObservationRecord
from .storage import new_id

OBSERVATION_SCHEMA_VERSION: Literal["stamp-observation-v1"] = "stamp-observation-v1"

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


def parse_stamp_observation_payload(payload: str | Mapping[str, Any]) -> StrictStampObservation:
    """Parse JSON or mapping output from a vision adapter."""

    if isinstance(payload, str):
        loaded = json.loads(payload)
    else:
        loaded = dict(payload)
    if not isinstance(loaded, dict):
        raise TypeError("Stamp observation payload must be a JSON object.")
    return StrictStampObservation.model_validate(loaded)


def stamp_observation_json_schema() -> dict[str, Any]:
    """Return the JSON schema to pass to a structured-output vision adapter."""

    return StrictStampObservation.model_json_schema()


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


def validation_error_messages(error: ValidationError) -> list[str]:
    """Return compact validation messages for API/UI surfaces."""

    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"])
        messages.append(f"{location}: {item['msg']}")
    return messages
