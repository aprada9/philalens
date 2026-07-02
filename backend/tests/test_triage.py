from philalens.models import StampObservationRecord
from philalens.triage import triage_observation


def test_triage_marks_complete_modern_observation_as_likely_common() -> None:
    triage = triage_observation(
        StampObservationRecord(
            observation_id="obs_1",
            run_id="run_1",
            crop_id="crop_1",
            issuer_hint="France",
            denomination_hint="25c",
            design_subject="Sower",
            cancellation_state="used_light_cancel",
            confidence=0.74,
        )
    )

    assert triage.value_bucket == "likely_common"
    assert triage.recommended_next_action == "spot-check with source matching"
    assert "triage_cannot_rule_out_valuable_variants" in triage.uncertainty_warnings


def test_triage_prioritizes_special_issue_clues() -> None:
    triage = triage_observation(
        StampObservationRecord(
            observation_id="obs_1",
            run_id="run_1",
            crop_id="crop_1",
            issuer_hint="United States",
            denomination_hint="10c",
            visible_text=["AIR MAIL"],
            design_subject="airplane",
            confidence=0.82,
        )
    )

    assert triage.value_bucket == "possibly_interesting"
    assert triage.recommended_next_action == "prioritize source matching"


def test_triage_escalates_classic_or_variant_clues_to_expert_check() -> None:
    triage = triage_observation(
        StampObservationRecord(
            observation_id="obs_1",
            run_id="run_1",
            crop_id="crop_1",
            issuer_hint="France",
            denomination_hint="1fr",
            date_hint="1890",
            visible_text=["surcharge"],
            confidence=0.78,
        )
    )

    assert triage.value_bucket == "needs_expert_check"
    assert triage.recommended_next_action == "verify catalog variant and expert-only factors"
    assert "watermark_perforation_or_paper_may_control_value" in triage.uncertainty_warnings


def test_triage_requires_source_matching_for_low_confidence_or_missing_identity() -> None:
    triage = triage_observation(
        StampObservationRecord(
            observation_id="obs_1",
            run_id="run_1",
            crop_id="crop_1",
            visible_text=["25"],
            confidence=0.2,
        )
    )

    assert triage.value_bucket == "needs_source_matching"
    assert triage.recommended_next_action == "run source matching"
