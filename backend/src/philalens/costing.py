"""OpenAI API cost estimation and run-level cost summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import StampObservationRecord

USD_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class OpenAIModelRate:
    input_usd_per_million: float
    output_usd_per_million: float
    cached_input_usd_per_million: float | None = None


OPENAI_MODEL_RATES_USD_PER_MILLION: dict[str, OpenAIModelRate] = {
    "gpt-5.4": OpenAIModelRate(1.25, 10.00, 0.125),
    "gpt-5.4-mini": OpenAIModelRate(0.25, 2.00, 0.025),
    "gpt-5.4-nano": OpenAIModelRate(0.05, 0.40, 0.005),
    "gpt-5.4-pro": OpenAIModelRate(15.00, 120.00),
    "gpt-5.5": OpenAIModelRate(1.75, 14.00, 0.175),
    "gpt-4.1": OpenAIModelRate(2.00, 8.00, 0.50),
    "gpt-4.1-mini": OpenAIModelRate(0.40, 1.60, 0.10),
    "gpt-4.1-nano": OpenAIModelRate(0.10, 0.40, 0.025),
}

# Curated vision-model choices surfaced in the settings dropdown. Estimates
# are computed from the same rough token heuristic as pre-run estimates
# (high image detail). Reasoning models (gpt-5.4 family) bill hidden
# reasoning tokens as output, so their real cost runs above the estimate.
_VISION_MODEL_CHOICES: list[dict[str, str | bool]] = [
    {
        "id": "gpt-4.1-mini",
        "note": "Proven default — calibration identifications were good at ~$0.07 per 46 stamps.",
        "recommended": True,
    },
    {
        "id": "gpt-5.4-mini",
        "note": "Smarter reasoning model at a similar price — best value upgrade to try.",
        "recommended": True,
    },
    {
        "id": "gpt-4.1",
        "note": "Stronger non-reasoning model; ~5x the price of the default.",
        "recommended": False,
    },
    {
        "id": "gpt-5.4",
        "note": (
            "Top-tier reasoning; for tricky stamps or a flagged-only re-run. "
            "Reasoning tokens make real cost higher than the estimate."
        ),
        "recommended": False,
    },
    {
        "id": "gpt-5.5",
        "note": "Newest flagship; most capable and most expensive sensible option.",
        "recommended": False,
    },
    {
        "id": "gpt-4.1-nano",
        "note": "Cheapest; identification quality drops noticeably — not recommended.",
        "recommended": False,
    },
]


def vision_model_options(image_detail: str = "high") -> list[dict[str, object]]:
    """Dropdown options with a rough cost-per-100-stamps estimate."""
    options: list[dict[str, object]] = []
    for choice in _VISION_MODEL_CHOICES:
        model_id = str(choice["id"])
        estimate = estimate_openai_vision_run_cost(
            model=model_id,
            image_detail=image_detail,
            crop_count=100,
            billable_api_call_count=100,
        )
        options.append(
            {
                "id": model_id,
                "note": choice["note"],
                "recommended": choice["recommended"],
                "estimated_usd_per_100_stamps": estimate["estimated_total_cost_usd"],
            }
        )
    return options


PRICING_NOTE = (
    "Costs use token usage returned by OpenAI and a local USD-per-million-token "
    "pricing table. Confirm current pricing in OpenAI billing for final charges."
)

ROUGH_ESTIMATE_NOTE = (
    "Pre-run cost is a rough token estimate for the configured model/detail. "
    "The post-run cost uses actual API token usage when the provider returns it."
)

_PROMPT_AND_SCHEMA_TOKEN_ESTIMATE = 1600
_OUTPUT_TOKEN_ESTIMATE = 700
_IMAGE_TOKEN_ESTIMATES_BY_DETAIL = {
    "low": 300,
    "auto": 1200,
    "high": 1800,
}


def estimate_openai_vision_run_cost(
    *,
    model: str | None,
    image_detail: str | None,
    crop_count: int,
    billable_api_call_count: int,
    skipped_crop_review_count: int = 0,
) -> dict[str, object]:
    detail = (image_detail or "auto").strip().lower()
    image_tokens = _IMAGE_TOKEN_ESTIMATES_BY_DETAIL.get(
        detail, _IMAGE_TOKEN_ESTIMATES_BY_DETAIL["auto"]
    )
    input_tokens_per_crop = _PROMPT_AND_SCHEMA_TOKEN_ESTIMATE + image_tokens
    output_tokens_per_crop = _OUTPUT_TOKEN_ESTIMATE
    usage = {
        "input_tokens": max(0, billable_api_call_count) * input_tokens_per_crop,
        "output_tokens": max(0, billable_api_call_count) * output_tokens_per_crop,
        "cached_input_tokens": 0,
    }
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    cost = openai_cost_for_usage(model, usage)
    return {
        "provider": "openai",
        "model": model,
        "pricing_model": cost.get("pricing_model"),
        "image_detail": detail,
        "currency": "USD",
        "estimate_available": cost.get("cost_available", False),
        "estimate_method": "rough_token_heuristic_v1",
        "crop_count": max(0, crop_count),
        "billable_api_call_count": max(0, billable_api_call_count),
        "skipped_crop_review_count": max(0, skipped_crop_review_count),
        "estimated_input_tokens": usage["input_tokens"],
        "estimated_output_tokens": usage["output_tokens"],
        "estimated_total_tokens": usage["total_tokens"],
        "estimated_total_cost_usd": cost.get("total_cost_usd"),
        "pricing": cost.get("pricing"),
        "note": ROUGH_ESTIMATE_NOTE,
    }


def non_openai_cost_estimate(
    *,
    provider: str,
    model: str | None = None,
    crop_count: int = 0,
    billable_api_call_count: int = 0,
    skipped_crop_review_count: int = 0,
) -> dict[str, object]:
    return {
        "provider": provider,
        "model": model,
        "pricing_model": None,
        "currency": "USD",
        "estimate_available": billable_api_call_count == 0,
        "crop_count": max(0, crop_count),
        "billable_api_call_count": max(0, billable_api_call_count),
        "skipped_crop_review_count": max(0, skipped_crop_review_count),
        "estimated_input_tokens": 0,
        "estimated_output_tokens": 0,
        "estimated_total_tokens": 0,
        "estimated_total_cost_usd": 0.0 if billable_api_call_count == 0 else None,
        "note": "No OpenAI API cost estimate is available for this provider.",
    }


def token_usage_from_response(response: Any) -> dict[str, int]:
    usage = _value(response, "usage")
    return token_usage_from_openai_usage(usage)


def token_usage_from_openai_usage(usage: Any) -> dict[str, int]:
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens = _int_value(usage, "input_tokens", "prompt_tokens")
    output_tokens = _int_value(usage, "output_tokens", "completion_tokens")
    total_tokens = _int_value(usage, "total_tokens")
    cached_input_tokens = _nested_int_value(
        usage,
        ("input_tokens_details", "cached_tokens"),
        ("prompt_tokens_details", "cached_tokens"),
    )

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": min(cached_input_tokens, input_tokens),
        "total_tokens": total_tokens,
    }


def openai_cost_for_usage(model: str | None, usage: dict[str, Any]) -> dict[str, object]:
    normalized_usage = token_usage_from_openai_usage(usage)
    pricing_model = pricing_key_for_model(model)
    rate = OPENAI_MODEL_RATES_USD_PER_MILLION.get(pricing_model or "")
    payload: dict[str, object] = {
        "provider": "openai",
        "model": model,
        "pricing_model": pricing_model,
        "currency": "USD",
        "input_tokens": normalized_usage["input_tokens"],
        "output_tokens": normalized_usage["output_tokens"],
        "cached_input_tokens": normalized_usage["cached_input_tokens"],
        "total_tokens": normalized_usage["total_tokens"],
        "pricing": _rate_payload(rate),
        "cost_available": rate is not None,
        "note": PRICING_NOTE,
    }
    if rate is None:
        payload.update(
            {
                "input_cost_usd": None,
                "output_cost_usd": None,
                "total_cost_usd": None,
            }
        )
        return payload

    cached_tokens = normalized_usage["cached_input_tokens"]
    uncached_input_tokens = max(0, normalized_usage["input_tokens"] - cached_tokens)
    cached_rate = rate.cached_input_usd_per_million or rate.input_usd_per_million
    input_cost = (
        uncached_input_tokens * rate.input_usd_per_million
        + cached_tokens * cached_rate
    ) / USD_PER_MILLION
    output_cost = (
        normalized_usage["output_tokens"] * rate.output_usd_per_million
    ) / USD_PER_MILLION
    total_cost = input_cost + output_cost
    payload.update(
        {
            "input_cost_usd": _round_usd(input_cost),
            "output_cost_usd": _round_usd(output_cost),
            "total_cost_usd": _round_usd(total_cost),
        }
    )
    return payload


def summarize_observation_costs(
    observations: list[StampObservationRecord],
    *,
    provider: str = "openai",
    model: str | None = None,
) -> dict[str, object]:
    api_call_count = 0
    input_tokens = 0
    output_tokens = 0
    cached_input_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    costed_call_count = 0
    unknown_cost_call_count = 0
    by_model: dict[str, dict[str, object]] = {}

    for observation in observations:
        metadata = observation.model_metadata
        usage = metadata.get("api_usage")
        if not isinstance(usage, dict):
            continue

        api_call_count += 1
        normalized_usage = token_usage_from_openai_usage(usage)
        input_tokens += normalized_usage["input_tokens"]
        output_tokens += normalized_usage["output_tokens"]
        cached_input_tokens += normalized_usage["cached_input_tokens"]
        total_tokens += normalized_usage["total_tokens"]

        call_cost = metadata.get("api_cost")
        call_model = model or str(metadata.get("model_name") or "unknown")
        model_bucket = by_model.setdefault(
            call_model,
            {
                "model": call_model,
                "api_call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "unknown_cost_call_count": 0,
            },
        )
        model_bucket["api_call_count"] = int(model_bucket["api_call_count"]) + 1
        model_bucket["input_tokens"] = int(model_bucket["input_tokens"]) + normalized_usage[
            "input_tokens"
        ]
        model_bucket["output_tokens"] = int(model_bucket["output_tokens"]) + normalized_usage[
            "output_tokens"
        ]
        model_bucket["total_tokens"] = int(model_bucket["total_tokens"]) + normalized_usage[
            "total_tokens"
        ]

        cost_value = (
            call_cost.get("total_cost_usd") if isinstance(call_cost, dict) else None
        )
        if isinstance(cost_value, int | float):
            total_cost += float(cost_value)
            costed_call_count += 1
            model_bucket["total_cost_usd"] = _round_usd(
                float(model_bucket["total_cost_usd"]) + float(cost_value)
            )
        else:
            unknown_cost_call_count += 1
            model_bucket["unknown_cost_call_count"] = int(
                model_bucket["unknown_cost_call_count"]
            ) + 1

    cost_available = api_call_count == 0 or unknown_cost_call_count == 0
    return {
        "provider": provider,
        "model": model,
        "currency": "USD",
        "api_call_count": api_call_count,
        "costed_api_call_count": costed_call_count,
        "unknown_cost_call_count": unknown_cost_call_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "total_tokens": total_tokens,
        "total_cost_usd": _round_usd(total_cost) if cost_available else None,
        "known_total_cost_usd": _round_usd(total_cost),
        "cost_available": cost_available,
        "by_model": list(by_model.values()),
        "note": PRICING_NOTE if api_call_count else "No billable API calls recorded for this run.",
    }


def pricing_key_for_model(model: str | None) -> str | None:
    if not model:
        return None
    normalized = model.strip().lower()
    for key in sorted(OPENAI_MODEL_RATES_USD_PER_MILLION, key=len, reverse=True):
        if normalized == key or normalized.startswith(f"{key}-"):
            return key
    return None


def _value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _int_value(source: Any, *keys: str) -> int:
    for key in keys:
        value = _value(source, key)
        if isinstance(value, int | float):
            return max(0, int(value))
    return 0


def _nested_int_value(source: Any, *paths: tuple[str, str]) -> int:
    for parent_key, child_key in paths:
        parent = _value(source, parent_key)
        value = _value(parent, child_key)
        if isinstance(value, int | float):
            return max(0, int(value))
    return 0


def _rate_payload(rate: OpenAIModelRate | None) -> dict[str, float | None] | None:
    if rate is None:
        return None
    return {
        "input_usd_per_million": rate.input_usd_per_million,
        "cached_input_usd_per_million": rate.cached_input_usd_per_million,
        "output_usd_per_million": rate.output_usd_per_million,
    }


def _round_usd(value: float) -> float:
    return round(value, 8)
