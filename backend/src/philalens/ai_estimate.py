"""AI value estimation for flagged stamps (Tier 2.5).

One model call per flagged stamp combines the crop image, the Tier 1
identification, and the gathered market evidence (asking-price context,
reference matches) into a conservative value range with confidence, a
rationale, and rarity notes (which varieties of the issue are valuable and
what to check on the physical stamp).

These are PRIORS, informed by the model's approximate catalog knowledge —
never evidence-backed facts. Every estimate is stored with an explicit
"AI-estimated range (unverified)" marker and stays visually and numerically
separate from owner-reviewed and realized-sale ranges in the UI, report,
and CSV.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from .market_evidence import ATTENTION_BUCKETS, MarketEvidenceError, _latest_valuations_per_crop
from .models import (
    CatalogCandidateRecord,
    SourceEvidenceRecord,
    StampCrop,
    StampObservationRecord,
    StampValuationRecord,
)
from .sources import TIER_ACTIVE_LISTING_WEAK
from .storage import PhilalensStore, new_id

AI_ESTIMATE_PREFIX = "AI-estimated range (unverified)"

_ESTIMATE_PROMPT = """You are an experienced philatelic dealer estimating what a stamp
would realistically fetch today, for a collection-triage tool. You are given a photo of
the stamp, an AI identification (unverified), visible-condition observations, and market
evidence gathered online.

Rules:
- Be conservative. Common used material trades in bulk at 5-20% of catalog value.
- Asking prices skew high: realized prices typically land at 20-50% of the median ask.
- If the identification is uncertain, widen the range and lower your confidence.
- The photo shows only the front: watermark, paper, gum, hidden faults, and authenticity
  are unknown. If the issue has valuable varieties that depend on them, say exactly what
  to check in rarity_notes (e.g. which watermark or perforation gauge separates the rare
  printing) and reflect the uncertainty in the range.
- rationale: 1-2 sentences on how you arrived at the range.
- rarity_notes: the valuable varieties of this issue (if any) and what distinguishes
  them; or state plainly that no valuable variety exists for this issue.
- recommended_action: keep_common if this is bulk material; check_sold_listings if the
  range matters enough to verify against realized sales; expert_review only when a
  plausible valuable variety needs physical examination.
Respond in the structured format only."""

_ESTIMATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "value_low",
        "value_high",
        "currency",
        "confidence",
        "rationale",
        "rarity_notes",
        "recommended_action",
    ],
    "properties": {
        "value_low": {"type": "number", "minimum": 0},
        "value_high": {"type": "number", "minimum": 0},
        "currency": {"type": "string", "enum": ["EUR", "USD"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string"},
        "rarity_notes": {"type": "string"},
        "recommended_action": {
            "type": "string",
            "enum": ["keep_common", "check_sold_listings", "expert_review"],
        },
    },
}

_ACTION_TEXT = {
    "keep_common": "AI estimate: bulk material; no individual follow-up needed",
    "check_sold_listings": "verify the AI estimate against eBay sold listings, then set the range",
    "expert_review": "physical check / expert review recommended (see rarity notes)",
}


class ValueEstimationError(RuntimeError):
    """Raised when the estimation model call fails."""


class ValueEstimator(Protocol):
    @property
    def model_name(self) -> str | None: ...

    def estimate(self, context: str, crop_image_path: Path) -> dict[str, Any]: ...


class OpenAIValueEstimator:
    """Structured estimation call against the OpenAI Responses API."""

    def __init__(self, client: Any, model_name: str) -> None:
        self.client = client
        self.model_name = model_name

    def estimate(self, context: str, crop_image_path: Path) -> dict[str, Any]:
        try:
            image_bytes = crop_image_path.read_bytes()
            image_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": f"{_ESTIMATE_PROMPT}\n\n{context}"},
                            {"type": "input_image", "image_url": image_url, "detail": "low"},
                        ],
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "stamp_value_estimate",
                        "description": "Conservative triage value estimate for one stamp.",
                        "schema": _ESTIMATE_SCHEMA,
                        "strict": True,
                    }
                },
                temperature=0,
                store=False,
            )
        except Exception as exc:
            raise ValueEstimationError(f"OpenAI API call failed: {exc}") from exc

        output_text = getattr(response, "output_text", None) or ""
        try:
            payload = json.loads(output_text)
        except ValueError as exc:
            raise ValueEstimationError("Estimation response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueEstimationError("Estimation response had an unexpected shape.")
        return payload


def build_value_estimator_from_settings(settings: Any) -> ValueEstimator | None:
    if (settings.vision_provider or "").strip().lower() != "openai" or not settings.openai_api_key:
        return None
    from openai import OpenAI

    return OpenAIValueEstimator(
        client=OpenAI(api_key=settings.openai_api_key),
        model_name=settings.openai_vision_model,
    )


def estimate_flagged_values(
    store: PhilalensStore,
    collection_id: str,
    estimator: ValueEstimator,
    crop_ids: list[str] | None = None,
    progress_callback: Callable[[int, int, StampCrop], None] | None = None,
) -> dict[str, object] | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    run = store.get_latest_evaluation_run(collection_id)
    if run is None or run.status != "completed":
        raise MarketEvidenceError(
            "Run a Tier 1 evaluation first: AI estimates attach to the latest completed run."
        )

    crops = {
        crop.crop_id: crop
        for page in store.list_pages(collection_id)
        for crop in store.list_crops_for_page(page.page_id)
    }
    if crop_ids is not None:
        missing = [crop_id for crop_id in crop_ids if crop_id not in crops]
        if missing:
            raise MarketEvidenceError(f"Crop not found in collection: {missing[0]}")
        targets = [crops[crop_id] for crop_id in crop_ids]
    else:
        targets = [
            crops[valuation.crop_id]
            for valuation in _latest_valuations_per_crop(store, run.run_id)
            if valuation.value_bucket in ATTENTION_BUCKETS and valuation.crop_id in crops
        ]

    estimated = 0
    errors: list[str] = []
    for index, crop in enumerate(targets, start=1):
        if progress_callback is not None:
            progress_callback(index, len(targets), crop)
        previous = store.get_stamp_valuation_for_crop(run.run_id, crop.crop_id)
        candidates = store.list_catalog_candidates_for_crop(run.run_id, crop.crop_id)
        observation = store.get_stamp_observation_for_crop(run.run_id, crop.crop_id)
        evidence = store.list_source_evidence_for_crop(run.run_id, crop.crop_id)
        context = _estimation_context(candidates, observation, evidence)

        try:
            payload = estimator.estimate(context, Path(crop.crop_path))
        except ValueEstimationError as exc:
            errors.append(f"{crop.crop_id}: {exc}")
            continue

        store.add_stamp_valuation(
            _estimated_valuation(run.run_id, crop, previous, payload)
        )
        estimated += 1

    return {"estimated_count": estimated, "target_count": len(targets), "errors": errors}


def _estimation_context(
    candidates: list[CatalogCandidateRecord],
    observation: StampObservationRecord | None,
    evidence: list[SourceEvidenceRecord],
) -> str:
    lines: list[str] = ["IDENTIFICATION (unverified AI prior):"]
    top = sorted(candidates, key=lambda candidate: candidate.rank)[:2]
    if not top:
        lines.append("- none available")
    for candidate in top:
        hint = next(
            (
                note.removeprefix("catalog_hint (unverified):").strip()
                for note in candidate.variant_notes
                if note.startswith("catalog_hint (unverified):")
            ),
            None,
        )
        lines.append(
            f"- {candidate.issuer or '?'} · {candidate.title or '?'} · "
            f"{candidate.year or '?'} · {candidate.denomination or '?'}"
            f" (confidence {candidate.match_score:.2f}"
            + (f"; catalog hint: {hint}" if hint else "")
            + ")"
        )

    if observation is not None:
        lines.append("CONDITION (visible only):")
        if observation.cancellation_state:
            lines.append(f"- cancellation: {observation.cancellation_state}")
        if observation.condition_notes:
            lines.append(f"- notes: {'; '.join(observation.condition_notes[:6])}")

    asking = [
        record.price
        for record in evidence
        if record.evidence_tier == TIER_ACTIVE_LISTING_WEAK and record.price is not None
    ]
    lines.append("MARKET EVIDENCE GATHERED:")
    if asking:
        lines.append(
            f"- {len(asking)} active eBay listings for similar keyword matches, asking "
            f"{min(asking):g}-{max(asking):g} "
            f"{next((r.currency for r in evidence if r.currency), 'USD')} "
            "(keyword-matched, may include different stamps; asking prices skew high)"
        )
    else:
        lines.append("- no marketplace listings found")
    return "\n".join(lines)


def _estimated_valuation(
    run_id: str,
    crop: StampCrop,
    previous: StampValuationRecord | None,
    payload: dict[str, Any],
) -> StampValuationRecord:
    value_low = max(0.0, float(payload.get("value_low", 0)))
    value_high = max(value_low, float(payload.get("value_high", 0)))
    confidence = min(1.0, max(0.0, float(payload.get("confidence", 0))))
    action = str(payload.get("recommended_action", "check_sold_listings"))

    assumptions = [
        f"{AI_ESTIMATE_PREFIX}: model prior informed by catalog knowledge and the "
        "gathered market context; not evidence-backed and not owner-reviewed.",
        f"AI rationale: {str(payload.get('rationale', '')).strip()}",
        f"Rarity check: {str(payload.get('rarity_notes', '')).strip()}",
    ]
    if previous is not None:
        assumptions.extend(
            item for item in previous.assumptions if item.startswith("Asking-price context:")
        )

    uncertainty_warnings = ["ai_estimated_range_unverified"]
    if previous is not None:
        uncertainty_warnings.extend(
            warning
            for warning in previous.uncertainty_warnings
            if warning not in {"no_evidence_backed_value_range", "market_evidence_not_checked"}
        )

    return StampValuationRecord(
        valuation_id=new_id("val"),
        run_id=run_id,
        crop_id=crop.crop_id,
        candidate_id=previous.candidate_id if previous else None,
        estimated_value_low=value_low,
        estimated_value_high=value_high,
        currency=str(payload.get("currency", "EUR")),
        identity_confidence=previous.identity_confidence if previous else 0.0,
        condition_confidence=previous.condition_confidence if previous else 0.0,
        # An AI prior is weak market evidence by definition.
        market_evidence_confidence=round(min(confidence, 0.4), 2),
        valuation_confidence=round(
            min(confidence, previous.identity_confidence if previous else confidence), 2
        ),
        value_bucket=previous.value_bucket if previous else "possibly_interesting",
        assumptions=assumptions,
        uncertainty_warnings=uncertainty_warnings,
        recommended_next_action=_ACTION_TEXT.get(action, _ACTION_TEXT["check_sold_listings"]),
        evidence_ids=previous.evidence_ids if previous else [],
    )
