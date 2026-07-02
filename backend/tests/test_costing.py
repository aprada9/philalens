from types import SimpleNamespace

from philalens.costing import (
    estimate_openai_vision_run_cost,
    openai_cost_for_usage,
    token_usage_from_response,
)


def test_openai_cost_for_usage_handles_cached_tokens_and_model_snapshots() -> None:
    cost = openai_cost_for_usage(
        "gpt-4.1-mini-2025-04-14",
        {
            "input_tokens": 1000,
            "output_tokens": 500,
            "input_tokens_details": {"cached_tokens": 200},
        },
    )

    assert cost["pricing_model"] == "gpt-4.1-mini"
    assert cost["input_tokens"] == 1000
    assert cost["output_tokens"] == 500
    assert cost["cached_input_tokens"] == 200
    assert cost["total_cost_usd"] == 0.00114


def test_token_usage_from_response_supports_openai_sdk_objects() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=1200,
            output_tokens=350,
            total_tokens=1550,
            input_tokens_details=SimpleNamespace(cached_tokens=100),
        )
    )

    usage = token_usage_from_response(response)

    assert usage == {
        "input_tokens": 1200,
        "output_tokens": 350,
        "cached_input_tokens": 100,
        "total_tokens": 1550,
    }


def test_estimate_openai_vision_run_cost_counts_billable_crops_only() -> None:
    estimate = estimate_openai_vision_run_cost(
        model="gpt-4.1-mini",
        image_detail="high",
        crop_count=10,
        billable_api_call_count=8,
        skipped_crop_review_count=2,
    )

    assert estimate["crop_count"] == 10
    assert estimate["billable_api_call_count"] == 8
    assert estimate["skipped_crop_review_count"] == 2
    assert estimate["estimated_total_cost_usd"] is not None
