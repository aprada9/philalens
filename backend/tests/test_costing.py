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


def test_vision_model_options_include_estimates_and_recommendation() -> None:
    from philalens.costing import vision_model_options

    options = vision_model_options("high")
    ids = [option["id"] for option in options]
    assert "gpt-4.1-mini" in ids
    assert "gpt-5.4-mini" in ids
    default = next(option for option in options if option["id"] == "gpt-4.1-mini")
    assert default["recommended"] is True
    assert isinstance(default["estimated_usd_per_100_stamps"], float)
    assert 0 < default["estimated_usd_per_100_stamps"] < 1
    # Every curated option must have a price in the rates table.
    assert all(option["estimated_usd_per_100_stamps"] is not None for option in options)


def test_ai_estimate_cost_heuristic() -> None:
    from philalens.costing import estimate_ai_value_run_cost

    estimate = estimate_ai_value_run_cost(model="gpt-4.1-mini", call_count=50)
    assert estimate["billable_api_call_count"] == 50
    assert estimate["estimate_available"] is True
    cost = estimate["estimated_total_cost_usd"]
    assert isinstance(cost, float)
    assert 0 < cost < 0.5  # ~50 low-detail estimation calls stay in cents territory
