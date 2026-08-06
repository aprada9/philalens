import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from philalens.config import Settings
from philalens.models import StampCrop
from philalens.observation_schema import DEFAULT_UNOBSERVABLE_FACTORS, OBSERVATION_SCHEMA_VERSION
from philalens.vision import (
    OpenAIStampVisionAdapter,
    VisionObservationError,
    build_vision_adapter_from_settings,
)

VALID_OBSERVATION = {
    "schema_version": OBSERVATION_SCHEMA_VERSION,
    "visible_text": ["FRANCE", "25"],
    "issuer_hint": "France",
    "denomination_hint": "25c",
    "currency_hint": "centimes",
    "date_hint": None,
    "design_subject": "Sower",
    "color_hints": ["blue"],
    "cancellation_state": "used_light_cancel",
    "centering": "slightly_off_center",
    "margin_notes": ["narrow right margin"],
    "perforation_observations": ["perforations visible, gauge not measured"],
    "visible_faults": ["light corner crease"],
    "condition_notes": ["used"],
    "image_quality_warnings": [],
    "unobservable_factors": DEFAULT_UNOBSERVABLE_FACTORS,
    "confidence": 0.72,
    "observation_notes": ["front crop only"],
}


class FakeResponses:
    def __init__(self, output_text: str, usage: Any | None = None) -> None:
        self.output_text = output_text
        self.usage = usage
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text, usage=self.usage)


class FakeClient:
    def __init__(self, output_text: str, usage: Any | None = None) -> None:
        self.responses = FakeResponses(output_text, usage=usage)


def test_openai_adapter_submits_image_and_strict_schema(tmp_path: Path) -> None:
    crop_path = tmp_path / "stamp.jpg"
    crop_path.write_bytes(b"fake jpeg payload")
    client = FakeClient(
        json.dumps(VALID_OBSERVATION),
        usage={
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
            "input_tokens_details": {"cached_tokens": 100},
        },
    )
    adapter = OpenAIStampVisionAdapter(
        api_key="test-key",
        model="test-vision-model",
        image_detail="low",
        client=client,
        prompt="Observe this stamp.",
    )

    analysis = adapter.observe_crop(
        StampCrop(
            crop_id="crop_1",
            page_id="page_1",
            crop_index=1,
            bbox_xywh=(1, 2, 30, 40),
            crop_path=str(crop_path),
            segmentation_confidence=0.9,
        ),
        run_id="run_1",
    )

    record = analysis.observation
    assert record.run_id == "run_1"
    assert record.crop_id == "crop_1"
    assert record.issuer_hint == "France"
    assert record.design_subject == "Sower"
    assert record.confidence == 0.72
    assert record.model_metadata["adapter"] == "openai_responses_vision"
    assert record.model_metadata["model_name"] == "test-vision-model"
    assert record.model_metadata["api_usage"]["total_tokens"] == 1500
    assert record.model_metadata["api_cost"]["cost_available"] is False
    # v1 payloads still parse; they simply carry no identity priors.
    assert analysis.candidates == []
    assert analysis.prior_value_bucket is None

    call = client.responses.calls[0]
    assert call["model"] == "test-vision-model"
    assert call["store"] is False
    assert call["temperature"] == 0
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    schema = call["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "identity_candidates" in schema["properties"]
    assert "prior_value_bucket" in schema["properties"]
    candidate_schema = schema["$defs"]["IdentityCandidate"]
    assert set(candidate_schema["required"]) == set(candidate_schema["properties"])
    assert "default" not in json.dumps(schema)

    content = call["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "Observe this stamp."}
    assert content[1]["type"] == "input_image"
    assert content[1]["detail"] == "low"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


def test_openai_adapter_parses_v2_identity_and_bucket(tmp_path: Path) -> None:
    crop_path = tmp_path / "stamp.jpg"
    crop_path.write_bytes(b"fake jpeg payload")
    payload = {
        **VALID_OBSERVATION,
        "schema_version": "stamp-observation-v2",
        "identity_candidates": [
            {
                "country": "France",
                "series_or_issue": "Sower definitives",
                "year_range": "1907-1920",
                "denomination": "25c",
                "catalog_hint": "Yvert Sower definitive range",
                "confidence": 0.8,
                "rationale": "REPUBLIQUE FRANCAISE text and Sower design visible",
            }
        ],
        "prior_value_bucket": "possibly_interesting",
        "prior_value_rationale": "Early period issue with light cancel.",
    }
    adapter = OpenAIStampVisionAdapter(
        api_key="test-key",
        model="test-vision-model",
        client=FakeClient(json.dumps(payload)),
        prompt="Observe this stamp.",
    )

    analysis = adapter.observe_crop(
        StampCrop(
            crop_id="crop_1",
            page_id="page_1",
            crop_index=1,
            bbox_xywh=(1, 2, 30, 40),
            crop_path=str(crop_path),
            segmentation_confidence=0.9,
        ),
        run_id="run_1",
    )

    assert analysis.prior_value_bucket == "possibly_interesting"
    assert analysis.prior_value_rationale == "Early period issue with light cancel."
    assert len(analysis.candidates) == 1
    candidate = analysis.candidates[0]
    assert candidate.run_id == "run_1"
    assert candidate.crop_id == "crop_1"
    assert candidate.source_name == "ai_vision_prior"
    assert candidate.catalog_id is None
    assert candidate.issuer == "France"
    assert candidate.title == "Sower definitives"
    assert candidate.year == 1907
    assert candidate.match_score == 0.8
    assert candidate.rank == 1
    assert "ai_prior_without_source_evidence" in candidate.contradiction_warnings
    assert any("catalog_hint (unverified)" in note for note in candidate.variant_notes)


def test_openai_adapter_rejects_invalid_model_output(tmp_path: Path) -> None:
    crop_path = tmp_path / "stamp.jpg"
    crop_path.write_bytes(b"fake jpeg payload")
    adapter = OpenAIStampVisionAdapter(
        api_key="test-key",
        model="test-vision-model",
        client=FakeClient(json.dumps({**VALID_OBSERVATION, "confidence": "high"})),
        prompt="Observe this stamp.",
    )

    with pytest.raises(VisionObservationError, match="Vision response did not match schema"):
        adapter.observe_crop(
            StampCrop(
                crop_id="crop_1",
                page_id="page_1",
                crop_index=1,
                bbox_xywh=(1, 2, 30, 40),
                crop_path=str(crop_path),
                segmentation_confidence=0.9,
            ),
            run_id="run_1",
        )


def test_vision_adapter_builder_requires_explicit_provider_and_key() -> None:
    assert build_vision_adapter_from_settings(Settings(vision_provider="none")) is None
    assert build_vision_adapter_from_settings(Settings(vision_provider="disabled")) is None

    with pytest.raises(VisionObservationError, match="OPENAI_API_KEY"):
        build_vision_adapter_from_settings(Settings(vision_provider="openai", openai_api_key=None))

    with pytest.raises(VisionObservationError, match="Unsupported vision provider"):
        build_vision_adapter_from_settings(
            Settings(vision_provider="unsupported", openai_api_key="test-key")
        )
