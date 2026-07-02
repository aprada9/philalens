from pathlib import Path
from typing import Any, cast

from philalens.exports import (
    build_collection_csv,
    build_collection_export,
    build_evaluation_run_export,
)
from philalens.models import (
    REVIEW_NEEDS_CROP_REVIEW,
    CatalogCandidateRecord,
    EmbeddingRecord,
    PageImageRecord,
    SourceEvidenceRecord,
    StampCrop,
    StampObservationRecord,
    StampValuationRecord,
)
from philalens.storage import PhilalensStore


def test_storage_and_exports_round_trip_collection(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="test batch")

    page = PageImageRecord(
        page_id="page_1",
        collection_id=collection.collection_id,
        page_order=1,
        original_filename="album.heic",
        original_path=str(tmp_path / "album.heic"),
        normalized_path=str(tmp_path / "normalized.jpg"),
        image_format="HEIF",
        width=1200,
        height=900,
        quality_warnings=[],
        notes=["Automatic crop detection completed."],
    )
    store.add_page(page)
    store.replace_page_crops(
        page.page_id,
        [
            StampCrop(
                crop_id="crop_1",
                page_id=page.page_id,
                crop_index=1,
                bbox_xywh=(10, 20, 100, 120),
                crop_path=str(tmp_path / "crop.jpg"),
                segmentation_confidence=0.62,
                rotation_degrees=12.5,
                review_state=REVIEW_NEEDS_CROP_REVIEW,
                warnings=["large_region_may_include_multiple_stamps"],
            )
        ],
    )

    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    collection_export = cast(dict[str, Any], export["collection"])
    pages_export = cast(list[dict[str, Any]], export["pages"])
    stamp_export = cast(dict[str, Any], pages_export[0]["stamps"][0])
    assert collection_export["page_count"] == 1
    assert collection_export["stamp_count"] == 1
    assert collection_export["needs_crop_review_count"] == 1
    assert stamp_export["review_state"] == REVIEW_NEEDS_CROP_REVIEW
    assert stamp_export["rotation_degrees"] == 12.5

    run = store.create_evaluation_run(
        collection_id=collection.collection_id,
        pipeline_version="test-pipeline-v1",
        vision_model="test-vision",
        embedding_model="test-embedding",
        enabled_sources=["user-csv"],
        settings={"confidence_floor": 0.2},
    )
    observation = store.add_stamp_observation(
        StampObservationRecord(
            observation_id="obs_1",
            run_id=run.run_id,
            crop_id="crop_1",
            visible_text=["FRANCE", "25"],
            issuer_hint="France",
            denomination_hint="25c",
            date_hint="early 20th century",
            design_subject="Sower definitive",
            color_hints=["blue"],
            cancellation_state="used",
            condition_notes=["heavy cancellation"],
            unobservable_factors=["watermark", "gum", "paper"],
            confidence=0.71,
            model_metadata={"adapter": "fixture"},
        )
    )
    candidate = store.add_catalog_candidate(
        CatalogCandidateRecord(
            candidate_id="cand_1",
            run_id=run.run_id,
            crop_id="crop_1",
            source_name="user-csv",
            source_record_id="row-12",
            issuer="France",
            title="France Sower 25c",
            year=1907,
            denomination="25c",
            variant_notes=["watermark unverified"],
            match_score=0.82,
            rank=1,
            contradiction_warnings=["perforation_not_measured"],
        )
    )
    evidence = store.add_source_evidence(
        SourceEvidenceRecord(
            evidence_id="ev_1",
            run_id=run.run_id,
            crop_id="crop_1",
            candidate_id=candidate.candidate_id,
            source_name="user-csv",
            source_type="user_imported_reference",
            local_reference_id="row-12",
            matched_fields={"issuer": "exact", "denomination": "exact"},
            price_low=0.25,
            price_high=1.5,
            currency="USD",
            evidence_tier="catalog_reference",
            confidence=0.67,
            license_notes="user supplied",
        )
    )
    valuation = store.add_stamp_valuation(
        StampValuationRecord(
            valuation_id="val_1",
            run_id=run.run_id,
            crop_id="crop_1",
            candidate_id=candidate.candidate_id,
            estimated_value_low=0.25,
            estimated_value_high=1.5,
            currency="USD",
            identity_confidence=0.72,
            condition_confidence=0.45,
            market_evidence_confidence=0.2,
            valuation_confidence=0.38,
            value_bucket="identified_low_value",
            assumptions=["front image only"],
            uncertainty_warnings=["watermark not checked"],
            recommended_next_action="no further review needed",
            evidence_ids=[evidence.evidence_id],
        )
    )
    embedding = store.add_embedding(
        EmbeddingRecord(
            embedding_id="emb_1",
            owner_type="crop",
            owner_id="crop_1",
            model_name="test-embedding",
            embedding_dimension=3,
            embedding_vector=[0.1, 0.2, 0.3],
        )
    )

    assert store.list_evaluation_runs(collection.collection_id)[0].run_id == run.run_id
    assert store.get_latest_evaluation_run(collection.collection_id) == run
    assert store.get_stamp_observation_for_crop(run.run_id, "crop_1") == observation
    assert store.list_catalog_candidates_for_crop(run.run_id, "crop_1") == [candidate]
    assert store.list_source_evidence_for_crop(run.run_id, "crop_1") == [evidence]
    assert store.get_stamp_valuation_for_crop(run.run_id, "crop_1") == valuation
    assert store.list_embeddings_for_owner("crop", "crop_1") == [embedding]

    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    assert export["latest_evaluation_run_id"] == run.run_id
    pages_export = cast(list[dict[str, Any]], export["pages"])
    stamp_export = cast(dict[str, Any], pages_export[0]["stamps"][0])
    observation_export = cast(dict[str, Any], stamp_export["observation"])
    identification_export = cast(dict[str, Any], stamp_export["identification"])
    candidates_export = cast(list[dict[str, Any]], identification_export["candidates"])
    evidence_export = cast(list[dict[str, Any]], stamp_export["evidence"])
    valuation_export = cast(dict[str, Any], stamp_export["valuation"])
    assert stamp_export["evaluation_run_id"] == run.run_id
    assert stamp_export["description"] == "Sower definitive"
    assert observation_export["issuer_hint"] == "France"
    assert candidates_export[0]["title"] == "France Sower 25c"
    assert evidence_export[0]["evidence_id"] == evidence.evidence_id
    assert valuation_export["value_bucket"] == "identified_low_value"
    assert valuation_export["recommended_next_action"] == "no further review needed"

    run_export = build_evaluation_run_export(store, run.run_id)
    assert run_export is not None
    run_export_run = cast(dict[str, Any], run_export["run"])
    observations_export = cast(list[dict[str, Any]], run_export["observations"])
    candidates_export = cast(list[dict[str, Any]], run_export["candidates"])
    evidence_export = cast(list[dict[str, Any]], run_export["evidence"])
    valuations_export = cast(list[dict[str, Any]], run_export["valuations"])
    assert run_export_run["pipeline_version"] == "test-pipeline-v1"
    assert observations_export[0]["observation_id"] == observation.observation_id
    assert candidates_export[0]["candidate_id"] == candidate.candidate_id
    assert evidence_export[0]["evidence_id"] == evidence.evidence_id
    assert valuations_export[0]["valuation_id"] == valuation.valuation_id

    csv_payload = build_collection_csv(store, collection.collection_id)
    assert csv_payload is not None
    assert "crop_1" in csv_payload
    assert "rotation_degrees" in csv_payload
    assert "12.5" in csv_payload
    assert "large_region_may_include_multiple_stamps" in csv_payload
    assert "Sower definitive" in csv_payload
    assert "identified_low_value" in csv_payload
    assert "no further review needed" in csv_payload

    assert store.delete_crop("crop_1") is True
    assert store.delete_crop("crop_missing") is False
    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    collection_export = cast(dict[str, Any], export["collection"])
    pages_export = cast(list[dict[str, Any]], export["pages"])
    assert collection_export["page_count"] == 1
    assert collection_export["stamp_count"] == 0
    assert pages_export[0]["stamps"] == []

    assert store.delete_page(page.page_id) is True
    assert store.delete_page("page_missing") is False
    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    collection_export = cast(dict[str, Any], export["collection"])
    assert collection_export["page_count"] == 0
    assert export["pages"] == []
