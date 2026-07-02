"""Optional AI vision observation adapters."""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from .costing import openai_cost_for_usage, token_usage_from_response
from .config import Settings
from .models import StampCrop, StampObservationRecord
from .observation_schema import (
    observation_to_record,
    parse_stamp_observation_payload,
    stamp_observation_json_schema,
    validation_error_messages,
)


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "stamp_analysis.md"


class VisionObservationError(RuntimeError):
    """Raised when an optional vision adapter cannot produce a valid observation."""


class VisionObservationAdapter(Protocol):
    @property
    def adapter_name(self) -> str:
        """Stable adapter identifier stored on evaluation runs and observations."""

    @property
    def model_name(self) -> str | None:
        """Provider model identifier, when the adapter has one."""

    def observe_crop(self, crop: StampCrop, run_id: str) -> StampObservationRecord:
        """Return a validated durable observation for a crop."""


def load_stamp_analysis_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_vision_adapter_from_settings(settings: Settings) -> VisionObservationAdapter | None:
    if settings.vision_provider in {"", "none", "off", "disabled"}:
        return None
    if settings.vision_provider != "openai":
        raise VisionObservationError(f"Unsupported vision provider: {settings.vision_provider}")
    if not settings.openai_api_key:
        raise VisionObservationError(
            "OPENAI_API_KEY is required when PHILALENS_VISION_PROVIDER=openai"
        )

    return OpenAIStampVisionAdapter(
        api_key=settings.openai_api_key,
        model=settings.openai_vision_model,
        image_detail=settings.openai_vision_detail,
    )


class OpenAIStampVisionAdapter:
    adapter_name = "openai_responses_vision"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        image_detail: str = "high",
        client: Any | None = None,
        prompt: str | None = None,
    ) -> None:
        self.model_name = model
        self.image_detail = image_detail
        self.prompt = prompt or load_stamp_analysis_prompt()
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
        self.client: Any = client

    def observe_crop(self, crop: StampCrop, run_id: str) -> StampObservationRecord:
        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": self.prompt},
                        {
                            "type": "input_image",
                            "image_url": _image_data_url(Path(crop.crop_path)),
                            "detail": self.image_detail,
                        },
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "stamp_observation",
                    "description": "Visible, uncertainty-preserving observations for one stamp crop.",
                    "schema": _openai_json_schema(stamp_observation_json_schema()),
                    "strict": True,
                }
            },
            temperature=0,
            store=False,
        )

        output_text = _response_output_text(response)
        try:
            observation = parse_stamp_observation_payload(output_text)
        except ValidationError as exc:
            detail = "; ".join(validation_error_messages(exc))
            raise VisionObservationError(f"Vision response did not match schema: {detail}") from exc
        except (TypeError, ValueError) as exc:
            detail = str(exc)
            raise VisionObservationError(f"Vision response did not match schema: {detail}") from exc

        record = observation_to_record(
            observation,
            run_id=run_id,
            crop_id=crop.crop_id,
            adapter_name=self.adapter_name,
            model_name=self.model_name,
        )
        usage = token_usage_from_response(response)
        if usage["total_tokens"] <= 0:
            return record

        return replace(
            record,
            model_metadata={
                **record.model_metadata,
                "api_usage": usage,
                "api_cost": openai_cost_for_usage(self.model_name, usage),
            },
        )


def _image_data_url(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise VisionObservationError(f"Crop image not found: {path}")

    content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for output_item in getattr(response, "output", []) or []:
        if isinstance(output_item, dict):
            content_items = output_item.get("content", [])
        else:
            content_items = getattr(output_item, "content", [])
        for content_item in content_items or []:
            text = getattr(content_item, "text", None)
            if isinstance(text, str) and text.strip():
                return text
            if isinstance(content_item, dict):
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    return text

    raise VisionObservationError("Vision response did not include output text.")


def _openai_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adjust Pydantic JSON schema for OpenAI strict structured outputs."""

    prepared = dict(schema)
    properties = prepared.get("properties")
    if isinstance(properties, dict):
        prepared["required"] = list(properties.keys())
    _strip_defaults(prepared)
    return prepared


def _strip_defaults(value: Any) -> None:
    if isinstance(value, dict):
        value.pop("default", None)
        for item in value.values():
            _strip_defaults(item)
    elif isinstance(value, list):
        for item in value:
            _strip_defaults(item)
