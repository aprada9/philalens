import importlib
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient


def test_api_uploads_collection_to_temp_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    # Stay hermetic even when the developer's .env configures a provider.
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    import philalens.config

    importlib.reload(philalens.config)

    import philalens.api

    importlib.reload(philalens.api)

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    client = TestClient(philalens.api.app)
    response = client.post(
        "/api/collections",
        files=[("files", ("page.png", encoded.tobytes(), "image/png"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["collection"]["page_count"] == 1
    assert payload["collection"]["stamp_count"] == 1
    assert payload["pages"][0]["stamps"][0]["crop_image_url"].startswith("/media/crops/")

    page_id = payload["pages"][0]["page_id"]
    redetect_response = client.post(f"/api/pages/{page_id}/redetect")

    assert redetect_response.status_code == 200
    redetect_payload = redetect_response.json()
    assert redetect_payload["collection"]["page_count"] == 1
    assert redetect_payload["collection"]["stamp_count"] == 1

    crop_id = redetect_payload["pages"][0]["stamps"][0]["crop_id"]
    runs_response = client.get(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-runs"
    )
    assert runs_response.status_code == 200
    assert runs_response.json() == []

    estimate_response = client.post(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-cost-estimate"
    )
    assert estimate_response.status_code == 200
    assert estimate_response.json()["provider"] == "none"
    assert estimate_response.json()["estimated_total_cost_usd"] == 0.0

    latest_run_response = client.get(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-runs/latest"
    )
    assert latest_run_response.status_code == 404

    evaluate_response = client.post(
        f"/api/collections/{payload['collection']['collection_id']}/evaluate"
    )
    assert evaluate_response.status_code == 200
    evaluate_payload = evaluate_response.json()
    assert evaluate_payload["latest_evaluation_summary"]["evaluated_stamp_count"] == 1
    assert (
        evaluate_payload["pages"][0]["stamps"][0]["valuation"]["value_bucket"]
        == "needs_better_image"
    )
    assert evaluate_payload["pages"][0]["stamps"][0]["observation"]["status"] == "available"

    runs_response = client.get(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-runs"
    )
    assert runs_response.status_code == 200
    run_id = runs_response.json()[0]["run_id"]
    assert runs_response.json()[0]["pipeline_version"] == "tier1-identification-v2"

    latest_run_response = client.get(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-runs/latest"
    )
    assert latest_run_response.status_code == 200
    assert latest_run_response.json()["run"]["pipeline_version"] == "tier1-identification-v2"
    assert latest_run_response.json()["summary"]["evaluated_stamp_count"] == 1
    assert latest_run_response.json()["valuations"][0]["value_bucket"] == "needs_better_image"

    run_response = client.get(f"/api/evaluation-runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["run"]["run_id"] == run_id

    patch_response = client.patch(
        f"/api/crops/{crop_id}",
        json={
            "bbox_xywh": redetect_payload["pages"][0]["stamps"][0]["bbox_xywh"],
            "rotation_degrees": 17.5,
        },
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["crop"]["rotation_degrees"] == 17.5

    manual_crop_response = client.post(
        f"/api/pages/{page_id}/crops",
        json={"bbox_xywh": [320, 340, 120, 140], "rotation_degrees": -8.5},
    )

    assert manual_crop_response.status_code == 200
    manual_crop_payload = manual_crop_response.json()
    assert manual_crop_payload["collection"]["stamp_count"] == 2
    assert manual_crop_payload["pages"][0]["stamps"][1]["rotation_degrees"] == -8.5
    manual_crop_id = manual_crop_payload["pages"][0]["stamps"][1]["crop_id"]

    selected_evaluate_response = client.post(
        f"/api/collections/{payload['collection']['collection_id']}/evaluate",
        json={"crop_ids": [manual_crop_id]},
    )

    assert selected_evaluate_response.status_code == 200
    selected_evaluate_payload = selected_evaluate_response.json()
    assert selected_evaluate_payload["latest_evaluation_summary"]["evaluated_stamp_count"] == 1
    assert selected_evaluate_payload["evaluation_runs"][0]["settings"]["crop_scope"] == "selected"
    assert "cost_estimate" in selected_evaluate_payload["evaluation_runs"][0]["settings"]
    assert "cost_actual" in selected_evaluate_payload["evaluation_runs"][0]["settings"]

    evaluation_job_response = client.post(
        f"/api/collections/{payload['collection']['collection_id']}/evaluate/start",
        json={"crop_ids": [manual_crop_id]},
    )

    assert evaluation_job_response.status_code == 200
    job_payload = evaluation_job_response.json()
    assert job_payload["cost_estimate"]["provider"] == "none"
    job_id = job_payload["job_id"]
    for _ in range(20):
        job_response = client.get(f"/api/evaluation-jobs/{job_id}")
        assert job_response.status_code == 200
        job_payload = job_response.json()
        if job_payload["status"] == "completed":
            break
        time.sleep(0.05)
    assert job_payload["status"] == "completed"
    assert job_payload["run_id"]
    assert job_payload["cost_actual"]["api_call_count"] == 0

    resume_completed_response = client.post(
        f"/api/evaluation-runs/{job_payload['run_id']}/resume"
    )
    assert resume_completed_response.status_code == 400
    assert client.post("/api/evaluation-runs/run_missing/resume").status_code == 404

    mark_ready_response = client.post(
        "/api/crops/mark-ready",
        json={"crop_ids": [crop_id]},
    )

    assert mark_ready_response.status_code == 200
    # Hot review-queue endpoints return light payloads; the client updates
    # its state locally instead of refetching the full export.
    assert mark_ready_response.json() == {"ready_crop_ids": [crop_id]}
    marked_crop_state = client.get(
        f"/api/collections/{payload['collection']['collection_id']}"
    ).json()["pages"][0]["stamps"]
    marked_crop = next(stamp for stamp in marked_crop_state if stamp["crop_id"] == crop_id)
    assert marked_crop["review_state"] == "unreviewed"
    assert marked_crop["warnings"] == []

    delete_crop_response = client.delete(f"/api/crops/{crop_id}")

    assert delete_crop_response.status_code == 200
    assert delete_crop_response.json() == {"deleted_crop_id": crop_id}

    delete_selected_response = client.post(
        "/api/crops/delete",
        json={"crop_ids": [manual_crop_id]},
    )

    assert delete_selected_response.status_code == 200
    assert delete_selected_response.json() == {"deleted_crop_ids": [manual_crop_id]}
    after_deletes = client.get(
        f"/api/collections/{payload['collection']['collection_id']}"
    ).json()
    assert after_deletes["collection"]["stamp_count"] == 0
    assert after_deletes["pages"][0]["stamps"] == []

    settings_response = client.get("/api/settings")

    assert settings_response.status_code == 200
    assert "openai_api_key_set" in settings_response.json()

    delete_page_response = client.delete(f"/api/pages/{page_id}")

    assert delete_page_response.status_code == 200
    delete_page_payload = delete_page_response.json()
    assert delete_page_payload["collection"]["page_count"] == 0
    assert delete_page_payload["collection"]["stamp_count"] == 0
    assert delete_page_payload["pages"] == []

    collection_id = payload["collection"]["collection_id"]
    delete_collection_response = client.delete(f"/api/collections/{collection_id}")
    assert delete_collection_response.status_code == 200
    assert client.get(f"/api/collections/{collection_id}").status_code == 404
    assert client.delete(f"/api/collections/{collection_id}").status_code == 404
    collection_dirs = list((tmp_path / "data" / "collections").glob(collection_id))
    assert collection_dirs == []


def test_settings_update_takes_effect_without_restart(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PHILALENS_OPENAI_VISION_MODEL", raising=False)
    monkeypatch.delenv("PHILALENS_OPENAI_VISION_DETAIL", raising=False)

    import philalens.api

    importlib.reload(philalens.api)
    # Redirect the .env write away from the real repository root.
    monkeypatch.setattr(philalens.api, "PROJECT_ROOT", tmp_path)

    client = TestClient(philalens.api.app)
    before = client.get("/api/settings").json()
    assert before["vision_provider"] == "none"
    assert before["openai_api_key_set"] is False

    update_response = client.post(
        "/api/settings",
        json={
            "vision_provider": "openai",
            "openai_api_key": "sk-test",
            "openai_vision_model": "gpt-test",
            "openai_vision_detail": "low",
        },
    )
    assert update_response.status_code == 200

    after = client.get("/api/settings").json()
    assert after["vision_provider"] == "openai"
    assert after["openai_api_key_set"] is True
    assert after["openai_vision_model"] == "gpt-test"
    assert after["openai_vision_detail"] == "low"

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "PHILALENS_VISION_PROVIDER=openai" in env_text
    assert "OPENAI_API_KEY=sk-test" in env_text


def test_redetect_removes_orphaned_manual_crop_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))

    import philalens.api

    importlib.reload(philalens.api)

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    client = TestClient(philalens.api.app)
    upload = client.post(
        "/api/collections",
        files=[("files", ("page.png", encoded.tobytes(), "image/png"))],
    )
    assert upload.status_code == 200
    page_id = upload.json()["pages"][0]["page_id"]

    manual = client.post(
        f"/api/pages/{page_id}/crops",
        json={"bbox_xywh": [320, 340, 120, 140]},
    )
    assert manual.status_code == 200
    manual_files = list((tmp_path / "data" / "collections").glob("**/crops/*_manual.jpg"))
    assert len(manual_files) == 1

    redetect = client.post(f"/api/pages/{page_id}/redetect")
    assert redetect.status_code == 200
    assert redetect.json()["collection"]["stamp_count"] == 1
    assert list((tmp_path / "data" / "collections").glob("**/crops/*_manual.jpg")) == []


def test_evidence_endpoints_gather_and_report_gaps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")
    monkeypatch.delenv("PHILALENS_EBAY_APP_ID", raising=False)
    monkeypatch.delenv("PHILALENS_EBAY_CERT_ID", raising=False)

    import philalens.api

    importlib.reload(philalens.api)

    from philalens.sources import EvidenceItem, EvidenceQuery

    class FakeAdapter:
        source_name = "fake_reference"

        def __init__(self) -> None:
            self.queries: list[EvidenceQuery] = []

        def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
            self.queries.append(query)
            return [
                EvidenceItem(
                    source_name=self.source_name,
                    source_type="open_reference",
                    evidence_tier="reference_metadata",
                    confidence=0.3,
                    source_url="https://example.org/ref/1",
                )
            ]

    fake_adapter = FakeAdapter()
    monkeypatch.setattr(
        philalens.api, "build_source_adapters_from_settings", lambda settings: [fake_adapter]
    )

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    client = TestClient(philalens.api.app)
    upload = client.post(
        "/api/collections",
        files=[("files", ("page.png", encoded.tobytes(), "image/png"))],
    )
    assert upload.status_code == 200
    collection_id = upload.json()["collection"]["collection_id"]
    crop_id = upload.json()["pages"][0]["stamps"][0]["crop_id"]

    # Evidence needs a completed Tier 1 run to attach to.
    no_run = client.post(f"/api/crops/{crop_id}/evidence")
    assert no_run.status_code == 400
    assert "Tier 1" in no_run.json()["detail"]

    assert client.post(f"/api/collections/{collection_id}/evaluate").status_code == 200

    # The skeleton run has no identity candidates: the crop gets an explicit
    # gap instead of a fabricated search.
    single = client.post(f"/api/crops/{crop_id}/evidence")
    assert single.status_code == 200
    stamp = single.json()["pages"][0]["stamps"][0]
    assert fake_adapter.queries == []
    assert stamp["valuation"]["estimated_value_low"] is None
    assert any(
        item.startswith("No value range:") for item in stamp["valuation"]["assumptions"]
    )

    # Seed an identity candidate so the adapter is actually queried.
    run_id = single.json()["latest_evaluation_run_id"]
    from philalens.models import CatalogCandidateRecord

    philalens.api.store.add_catalog_candidate(
        CatalogCandidateRecord(
            candidate_id="cand_api_test",
            run_id=run_id,
            crop_id=crop_id,
            source_name="ai_vision_prior",
            issuer="Spain",
            title="Velazquez series",
            year=1959,
            match_score=0.8,
            rank=1,
        )
    )
    with_candidate = client.post(f"/api/crops/{crop_id}/evidence")
    assert with_candidate.status_code == 200
    stamp = with_candidate.json()["pages"][0]["stamps"][0]
    assert len(fake_adapter.queries) == 1
    assert fake_adapter.queries[0].issuer == "Spain"
    assert len(stamp["evidence"]) == 1
    assert stamp["evidence"][0]["source_name"] == "fake_reference"
    assert stamp["evidence"][0]["source_url"] == "https://example.org/ref/1"

    # Batch job over flagged crops: none are in attention buckets here, so it
    # completes with nothing to do.
    job = client.post(f"/api/collections/{collection_id}/evidence/start")
    assert job.status_code == 200
    job_id = job.json()["job_id"]
    for _ in range(20):
        job_payload = client.get(f"/api/evaluation-jobs/{job_id}").json()
        if job_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert job_payload["status"] == "completed"
    assert "No flagged stamps" in job_payload["message"]

    settings_payload = client.get("/api/settings").json()
    assert settings_payload["market_sources"]["wikidata"] == "available"
    assert settings_payload["market_sources"]["ebay_browse"] == "not_configured"


def test_settings_update_stores_ebay_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")
    monkeypatch.delenv("PHILALENS_EBAY_APP_ID", raising=False)
    monkeypatch.delenv("PHILALENS_EBAY_CERT_ID", raising=False)

    import philalens.api

    importlib.reload(philalens.api)
    monkeypatch.setattr(philalens.api, "PROJECT_ROOT", tmp_path)

    client = TestClient(philalens.api.app)
    assert client.get("/api/settings").json()["market_sources"]["ebay_browse"] == "not_configured"

    update = client.post(
        "/api/settings",
        json={
            "vision_provider": "none",
            "openai_vision_model": "gpt-4.1-mini",
            "openai_vision_detail": "high",
            "ebay_app_id": "app-123",
            "ebay_cert_id": "cert-456",
        },
    )
    assert update.status_code == 200
    assert update.json()["market_sources"]["ebay_browse"] == "configured"

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "PHILALENS_EBAY_APP_ID=app-123" in env_text
    assert "PHILALENS_EBAY_CERT_ID=cert-456" in env_text


def test_cancel_evaluation_job_validation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")

    import philalens.api

    importlib.reload(philalens.api)

    client = TestClient(philalens.api.app)
    assert client.post("/api/evaluation-jobs/evaljob_missing/cancel").status_code == 404

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    upload = client.post(
        "/api/collections",
        files=[("files", ("page.png", encoded.tobytes(), "image/png"))],
    )
    assert upload.status_code == 200
    collection_id = upload.json()["collection"]["collection_id"]

    job_id = client.post(f"/api/collections/{collection_id}/evaluate/start").json()["job_id"]
    for _ in range(20):
        job_payload = client.get(f"/api/evaluation-jobs/{job_id}").json()
        if job_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert job_payload["status"] == "completed"

    finished_cancel = client.post(f"/api/evaluation-jobs/{job_id}/cancel")
    assert finished_cancel.status_code == 400
    assert "Only queued or running jobs" in finished_cancel.json()["detail"]


def test_add_pages_to_collection_skips_duplicate_filenames(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")

    import philalens.api

    importlib.reload(philalens.api)

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    payload_bytes = encoded.tobytes()

    client = TestClient(philalens.api.app)
    upload = client.post(
        "/api/collections",
        files=[("files", ("page-a.png", payload_bytes, "image/png"))],
    )
    assert upload.status_code == 200
    collection_id = upload.json()["collection"]["collection_id"]

    # Re-uploading the whole folder: the existing page is skipped by filename
    # (case-insensitive), the new one is ingested and ordered after it.
    add = client.post(
        f"/api/collections/{collection_id}/pages",
        files=[
            ("files", ("PAGE-A.png", payload_bytes, "image/png")),
            ("files", ("page-b.png", payload_bytes, "image/png")),
        ],
    )
    assert add.status_code == 200
    add_payload = add.json()
    assert add_payload["added_page_count"] == 1
    assert add_payload["skipped_duplicate_filenames"] == ["PAGE-A.png"]
    assert add_payload["collection"]["page_count"] == 2
    filenames = [page["original_filename"] for page in add_payload["pages"]]
    assert filenames == ["page-a.png", "page-b.png"]
    orders = [page["page_order"] for page in add_payload["pages"]]
    assert orders == [1, 2]

    # Nothing new: everything skipped, nothing duplicated.
    repeat = client.post(
        f"/api/collections/{collection_id}/pages",
        files=[("files", ("page-b.png", payload_bytes, "image/png"))],
    )
    assert repeat.status_code == 200
    assert repeat.json()["added_page_count"] == 0
    assert repeat.json()["collection"]["page_count"] == 2

    missing = client.post(
        "/api/collections/col_missing/pages",
        files=[("files", ("page-c.png", payload_bytes, "image/png"))],
    )
    assert missing.status_code == 404


def test_backup_endpoint_streams_sqlite_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PHILALENS_VISION_PROVIDER", "none")

    import philalens.api

    importlib.reload(philalens.api)

    client = TestClient(philalens.api.app)
    response = client.get("/api/backup.sqlite")
    assert response.status_code == 200
    assert response.content[:16] == b"SQLite format 3\x00"
    assert "philalens-" in response.headers["content-disposition"]
    assert list((tmp_path / "data" / "backups").glob("philalens-*.sqlite"))


def test_relax_crop_review_unflags_confident_clean_crops(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))

    import philalens.api
    from philalens.models import REVIEW_NEEDS_CROP_REVIEW

    importlib.reload(philalens.api)

    image = np.zeros((700, 900, 3), dtype=np.uint8)
    cv2.rectangle(image, (80, 90), (270, 360), (240, 240, 240), -1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok

    client = TestClient(philalens.api.app)
    upload = client.post(
        "/api/collections",
        files=[("files", ("page.png", encoded.tobytes(), "image/png"))],
    )
    assert upload.status_code == 200
    collection_id = upload.json()["collection"]["collection_id"]
    crop_id = upload.json()["pages"][0]["stamps"][0]["crop_id"]

    # Simulate crops flagged under the old stricter rule: one clean and
    # confident (relaxable), one with a warning (must stay flagged).
    from dataclasses import replace as dc_replace

    store = philalens.api.store
    crop = store.get_crop(crop_id)
    store.update_crop(
        dc_replace(crop, review_state=REVIEW_NEEDS_CROP_REVIEW, warnings=[],
                   segmentation_confidence=0.6)
    )
    warned = dc_replace(
        crop,
        crop_id="crop_warned",
        crop_index=crop.crop_index + 1,
        review_state=REVIEW_NEEDS_CROP_REVIEW,
        warnings=["touches_image_edge"],
        segmentation_confidence=0.9,
    )
    store.add_crop(warned)

    response = client.post(f"/api/collections/{collection_id}/relax-crop-review")
    assert response.status_code == 200
    payload = response.json()
    assert payload["relaxed_crop_count"] == 1
    states = {
        stamp["crop_id"]: stamp["review_state"] for stamp in payload["pages"][0]["stamps"]
    }
    assert states[crop_id] == "unreviewed"
    assert states["crop_warned"] == "needs_crop_review"

    assert client.post("/api/collections/col_missing/relax-crop-review").status_code == 404
