"""OpenAI API cost estimation and run-level cost summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import EvaluationRunRecord, StampObservationRecord


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


def build_cost_dashboard(runs: list[EvaluationRunRecord]) -> dict[str, object]:
    sorted_runs = sorted(runs, key=lambda run: (run.started_at, run.run_id), reverse=True)
    total_actual_cost = 0.0
    total_estimated_cost = 0.0
    actual_cost_available = True
    estimated_cost_available = True
    api_call_count = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    unknown_cost_call_count = 0
    estimated_api_call_count = 0

    for run in sorted_runs:
        settings = run.settings
        actual = settings.get("cost_actual")
        estimate = settings.get("cost_estimate")
        if isinstance(actual, dict):
            api_call_count += _dict_int(actual, "api_call_count")
            input_tokens += _dict_int(actual, "input_tokens")
            output_tokens += _dict_int(actual, "output_tokens")
            total_tokens += _dict_int(actual, "total_tokens")
            unknown_cost_call_count += _dict_int(actual, "unknown_cost_call_count")
            actual_cost_value = actual.get("total_cost_usd")
            known_cost_value = actual.get("known_total_cost_usd")
            if isinstance(actual_cost_value, int | float):
                total_actual_cost += float(actual_cost_value)
            elif isinstance(known_cost_value, int | float):
                total_actual_cost += float(known_cost_value)
                actual_cost_available = False
            elif _dict_int(actual, "api_call_count") > 0:
                actual_cost_available = False

        if isinstance(estimate, dict):
            estimated_api_call_count += _dict_int(estimate, "billable_api_call_count")
            estimate_cost_value = estimate.get("estimated_total_cost_usd")
            if isinstance(estimate_cost_value, int | float):
                total_estimated_cost += float(estimate_cost_value)
            elif _dict_int(estimate, "billable_api_call_count") > 0:
                estimated_cost_available = False

    latest_run = sorted_runs[0] if sorted_runs else None
    return {
        "currency": "USD",
        "evaluation_run_count": len(sorted_runs),
        "api_call_count": api_call_count,
        "estimated_api_call_count": estimated_api_call_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "unknown_cost_call_count": unknown_cost_call_count,
        "actual_cost_available": actual_cost_available,
        "estimated_cost_available": estimated_cost_available,
        "total_actual_cost_usd": _round_usd(total_actual_cost),
        "total_estimated_cost_usd": _round_usd(total_estimated_cost)
        if estimated_cost_available
        else None,
        "latest_run": _dashboard_latest_run(latest_run),
        "pricing_note": PRICING_NOTE,
    }


def pricing_key_for_model(model: str | None) -> str | None:
    if not model:
        return None
    normalized = model.strip().lower()
    for key in sorted(OPENAI_MODEL_RATES_USD_PER_MILLION, key=len, reverse=True):
        if normalized == key or normalized.startswith(f"{key}-"):
            return key
    return None


def _dashboard_latest_run(run: EvaluationRunRecord | None) -> dict[str, object] | None:
    if run is None:
        return None
    actual = run.settings.get("cost_actual")
    estimate = run.settings.get("cost_estimate")
    actual_cost = actual.get("total_cost_usd") if isinstance(actual, dict) else None
    estimated_cost = (
        estimate.get("estimated_total_cost_usd") if isinstance(estimate, dict) else None
    )
    api_call_count = _dict_int(actual, "api_call_count") if isinstance(actual, dict) else 0
    return {
        "run_id": run.run_id,
        "collection_id": run.collection_id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "model": run.vision_model,
        "actual_cost_usd": actual_cost if isinstance(actual_cost, int | float) else None,
        "estimated_cost_usd": estimated_cost if isinstance(estimated_cost, int | float) else None,
        "api_call_count": api_call_count,
    }


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


def _dict_int(source: dict[str, Any], key: str) -> int:
    value = source.get(key)
    return max(0, int(value)) if isinstance(value, int | float) else 0


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
