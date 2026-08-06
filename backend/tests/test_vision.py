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

    record = adapter.observe_crop(
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

    assert record.run_id == "run_1"
    assert record.crop_id == "crop_1"
    assert record.issuer_hint == "France"
    assert record.design_subject == "Sower"
    assert record.confidence == 0.72
    assert record.model_metadata["adapter"] == "openai_responses_vision"
    assert record.model_metadata["model_name"] == "test-vision-model"
    assert record.model_metadata["api_usage"]["total_tokens"] == 1500
    assert record.model_metadata["api_cost"]["cost_available"] is False

    call = client.responses.calls[0]
    assert call["model"] == "test-vision-model"
    assert call["store"] is False
    assert call["temperature"] == 0
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    schema = call["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in json.dumps(schema)

    content = call["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "Observe this stamp."}
    assert content[1]["type"] == "input_image"
    assert content[1]["detail"] == "low"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


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
