"""Conservative value-triage rules for observed stamp crops."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import StampObservationRecord


@dataclass(frozen=True)
class ValueTriage:
    value_bucket: str
    recommended_next_action: str
    uncertainty_warnings: list[str]
    assumptions: list[str]
    valuation_confidence: float


_INTERESTING_TERMS = {
    "air mail",
    "airmail",
    "avion",
    "due",
    "express",
    "official",
    "overprint",
    "postage due",
    "surcharge",
    "taxe",
    "war",
}
_EXPERT_TERMS = {
    "essay",
    "error",
    "inverted",
    "misprint",
    "overprint",
    "proof",
    "surcharge",
    "variety",
}
_SEVERE_FAULT_TERMS = {
    "clipped",
    "crease",
    "fold",
    "heavy cancel",
    "stain",
    "tear",
    "thin",
    "toning",
}


def triage_observation(observation: StampObservationRecord) -> ValueTriage:
    """Assign a non-price triage bucket from visible observations only."""

    text = _observation_text(observation)
    has_identity_clues = bool(
        observation.issuer_hint or observation.denomination_hint or observation.design_subject
    )
    has_expert_signal = _contains_any(text, _EXPERT_TERMS)
    has_interest_signal = has_expert_signal or _contains_any(text, _INTERESTING_TERMS)
    has_early_signal = _has_early_date_signal(text)
    has_severe_fault = _contains_any(text, _SEVERE_FAULT_TERMS)
    confidence = observation.confidence

    base_warnings = [
        "catalog_identity_not_verified",
        "market_evidence_not_checked",
        "front_image_triage_only",
    ]

    if not has_identity_clues or confidence < 0.35:
        return ValueTriage(
            value_bucket="needs_source_matching",
            recommended_next_action="run source matching",
            uncertainty_warnings=[
                *base_warnings,
                "observation_confidence_low_or_identity_clues_missing",
            ],
            assumptions=[
                "Visible observation does not provide enough identity clues for value triage.",
                "No catalog, perforation, watermark, or market evidence has been checked.",
            ],
            valuation_confidence=0.05,
        )

    if has_expert_signal or (has_early_signal and not has_severe_fault):
        return ValueTriage(
            value_bucket="needs_expert_check",
            recommended_next_action="verify catalog variant and expert-only factors",
            uncertainty_warnings=[
                *base_warnings,
                "possible_variant_or_classic_stamp_signal",
                "watermark_perforation_or_paper_may_control_value",
            ],
            assumptions=[
                "Visible clues suggest this crop may depend on expert-only catalog factors.",
                "No price range should be trusted until catalog identity and condition are verified.",
            ],
            valuation_confidence=0.12,
        )

    if has_interest_signal or has_early_signal:
        return ValueTriage(
            value_bucket="possibly_interesting",
            recommended_next_action="prioritize source matching",
            uncertainty_warnings=[
                *base_warnings,
                "visible_clues_may_indicate_special_issue_or_age",
            ],
            assumptions=[
                "Visible clues make this crop worth prioritizing for catalog/source matching.",
                "No market evidence has been checked.",
            ],
            valuation_confidence=0.1,
        )

    return ValueTriage(
        value_bucket="likely_common",
        recommended_next_action="spot-check with source matching",
        uncertainty_warnings=[
            *base_warnings,
            "triage_cannot_rule_out_valuable_variants",
        ],
        assumptions=[
            "Visible clues do not show an obvious high-priority value signal.",
            "Watermark, perforation, paper, shade, and market evidence have not been checked.",
        ],
        valuation_confidence=0.08,
    )


def _observation_text(observation: StampObservationRecord) -> str:
    parts: list[str] = []
    parts.extend(observation.visible_text)
    parts.extend(observation.color_hints)
    parts.extend(observation.condition_notes)
    parts.extend(observation.image_quality_warnings)
    for value in (
        observation.issuer_hint,
        observation.denomination_hint,
        observation.date_hint,
        observation.design_subject,
        observation.cancellation_state,
    ):
        if value:
            parts.append(value)
    return " ".join(parts).casefold()


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _has_early_date_signal(text: str) -> bool:
    if any(term in text for term in ("19th century", "classic", "victorian")):
        return True
    for match in re.finditer(r"\b(18\d{2}|19\d{2})\b", text):
        year = int(match.group(1))
        if year < 1930:
            return True
    return False
