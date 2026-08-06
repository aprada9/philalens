import json

import pytest
from pydantic import ValidationError

from philalens.observation_schema import (
    DEFAULT_UNOBSERVABLE_FACTORS,
    OBSERVATION_SCHEMA_VERSION,
    observation_to_record,
    parse_stamp_observation_payload,
    stamp_observation_json_schema,
    validation_error_messages,
)


def test_parse_stamp_observation_payload_and_convert_to_record() -> None:
    observation = parse_stamp_observation_payload(
        {
            "schema_version": OBSERVATION_SCHEMA_VERSION,
            "visible_text": ["FRANCE", "25", "france", " "],
            "issuer_hint": " France ",
            "denomination_hint": "25c",
            "currency_hint": "centimes",
            "date_hint": "early 20th century",
            "design_subject": "Sower",
            "color_hints": ["blue", "Blue"],
            "cancellation_state": "used_heavy_cancel",
            "centering": "slightly_off_center",
            "margin_notes": ["narrow right margin"],
            "perforation_observations": ["perforations visible, gauge not measured"],
            "visible_faults": ["heavy cancel"],
            "condition_notes": ["used"],
            "image_quality_warnings": ["crop review suggested"],
            "unobservable_factors": ["watermark"],
            "confidence": 0.68,
            "observation_notes": ["front crop only"],
        }
    )

    assert observation.visible_text == ["FRANCE", "25"]
    assert observation.issuer_hint == "France"
    assert observation.color_hints == ["blue"]
    assert observation.unobservable_factors[:1] == ["watermark"]
    assert set(DEFAULT_UNOBSERVABLE_FACTORS).issubset(set(observation.unobservable_factors))

    record = observation_to_record(
        observation,
        run_id="run_1",
        crop_id="crop_1",
        observation_id="obs_1",
        model_name="test-vision-model",
    )

    assert record.observation_id == "obs_1"
    assert record.run_id == "run_1"
    assert record.crop_id == "crop_1"
    assert record.visible_text == ["FRANCE", "25"]
    assert record.issuer_hint == "France"
    assert record.denomination_hint == "25c"
    assert record.design_subject == "Sower"
    assert record.cancellation_state == "used_heavy_cancel"
    assert "visible_fault: heavy cancel" in record.condition_notes
    assert record.model_metadata["schema_version"] == OBSERVATION_SCHEMA_VERSION
    assert record.model_metadata["model_name"] == "test-vision-model"
    assert record.model_metadata["currency_hint"] == "centimes"
    assert record.model_metadata["structured_condition"]["centering"] == "slightly_off_center"


def test_parse_stamp_observation_payload_accepts_json_string_and_defaults() -> None:
    observation = parse_stamp_observation_payload(
        json.dumps(
            {
                "visible_text": [],
                "issuer_hint": "",
                "cancellation_state": "unknown",
                "centering": "unknown",
                "confidence": 0.0,
            }
        )
    )

    assert observation.schema_version == OBSERVATION_SCHEMA_VERSION
    assert observation.issuer_hint is None
    assert observation.unobservable_factors == DEFAULT_UNOBSERVABLE_FACTORS


def test_stamp_observation_json_schema_forbids_extra_fields() -> None:
    schema = stamp_observation_json_schema()

    assert schema["additionalProperties"] is False
    assert "visible_text" in schema["properties"]
    assert schema["properties"]["confidence"]["maximum"] == 1.0


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (
            {
                "visible_text": [],
                "cancellation_state": "unknown",
                "centering": "unknown",
                "confidence": 0.5,
                "catalog_id": "not allowed here",
            },
            "catalog_id",
        ),
        (
            {
                "visible_text": [],
                "cancellation_state": "cancelled",
                "centering": "unknown",
                "confidence": 0.5,
            },
            "cancellation_state",
        ),
        (
            {
                "visible_text": [],
                "cancellation_state": "unknown",
                "centering": "unknown",
                "confidence": "0.5",
            },
            "confidence",
        ),
        (
            {
                "visible_text": [],
                "cancellation_state": "unknown",
                "centering": "unknown",
                "confidence": 1.5,
            },
            "confidence",
        ),
    ],
)
def test_parse_stamp_observation_payload_rejects_invalid_payloads(
    payload: dict[str, object], expected_message: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        parse_stamp_observation_payload(payload)

    messages = validation_error_messages(exc_info.value)
    assert any(expected_message in message for message in messages)


def test_parse_stamp_observation_payload_rejects_non_object_json() -> None:
    with pytest.raises(TypeError):
        parse_stamp_observation_payload("[]")


def test_parse_v2_payload_with_identity_and_bucket() -> None:
    from philalens.observation_schema import (
        StrictStampObservationV2,
        analysis_from_observation,
    )

    payload = {
        "schema_version": "stamp-observation-v2",
        "visible_text": ["ESPANA", "80 CTS"],
        "issuer_hint": "Spain",
        "denomination_hint": "80 cts",
        "cancellation_state": "used_light_cancel",
        "confidence": 0.8,
        "identity_candidates": [
            {
                "country": "Spain",
                "series_or_issue": "1959 Velazquez set",
                "year_range": "1959",
                "denomination": "80 cts",
                "catalog_hint": "Edifil ~1238-1247",
                "confidence": 0.75,
                "rationale": "ESPANA text and Velazquez portrait design",
            }
        ],
        "prior_value_bucket": "likely_common",
        "prior_value_rationale": "Mass-produced commemorative, used.",
    }

    observation = parse_stamp_observation_payload(payload)
    assert isinstance(observation, StrictStampObservationV2)
    assert observation.prior_value_bucket == "likely_common"

    analysis = analysis_from_observation(observation, run_id="run_1", crop_id="crop_1")
    assert analysis.prior_value_bucket == "likely_common"
    assert len(analysis.candidates) == 1
    assert analysis.candidates[0].issuer == "Spain"
    assert analysis.candidates[0].year == 1959
    assert analysis.candidates[0].catalog_id is None
    assert "ai_prior_without_source_evidence" in analysis.candidates[0].contradiction_warnings


def test_v2_caps_candidates_at_three_strongest() -> None:
    payload = {
        "schema_version": "stamp-observation-v2",
        "confidence": 0.5,
        "identity_candidates": [
            {"country": f"Country {index}", "confidence": index / 10}
            for index in range(1, 6)
        ],
        "prior_value_bucket": "likely_common",
    }

    observation = parse_stamp_observation_payload(payload)
    from philalens.observation_schema import StrictStampObservationV2

    assert isinstance(observation, StrictStampObservationV2)
    assert len(observation.identity_candidates) == 3
    assert [candidate.confidence for candidate in observation.identity_candidates] == [
        0.5,
        0.4,
        0.3,
    ]


def test_v2_rejects_unknown_bucket() -> None:
    payload = {
        "schema_version": "stamp-observation-v2",
        "confidence": 0.5,
        "prior_value_bucket": "very_valuable",
    }

    with pytest.raises(ValidationError):
        parse_stamp_observation_payload(payload)


def test_v1_analysis_has_no_priors() -> None:
    from philalens.observation_schema import analysis_from_observation

    observation = parse_stamp_observation_payload(
        {"schema_version": "stamp-observation-v1", "confidence": 0.4}
    )
    analysis = analysis_from_observation(observation, run_id="run_1", crop_id="crop_1")
    assert analysis.candidates == []
    assert analysis.prior_value_bucket is None
    assert analysis.prior_value_rationale is None
