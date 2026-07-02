import importlib
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient


def test_api_uploads_collection_to_temp_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHILALENS_DATA_DIR", str(tmp_path / "data"))

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
    assert runs_response.json()[0]["pipeline_version"] == "crop-readiness-skeleton-v1"

    latest_run_response = client.get(
        f"/api/collections/{payload['collection']['collection_id']}/evaluation-runs/latest"
    )
    assert latest_run_response.status_code == 200
    assert latest_run_response.json()["run"]["pipeline_version"] == "crop-readiness-skeleton-v1"
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

    mark_ready_response = client.post(
        "/api/crops/mark-ready",
        json={"crop_ids": [crop_id]},
    )

    assert mark_ready_response.status_code == 200
    mark_ready_payload = mark_ready_response.json()
    marked_crop = next(
        stamp for stamp in mark_ready_payload["pages"][0]["stamps"] if stamp["crop_id"] == crop_id
    )
    assert marked_crop["review_state"] == "unreviewed"
    assert marked_crop["warnings"] == []

    delete_crop_response = client.delete(f"/api/crops/{crop_id}")

    assert delete_crop_response.status_code == 200
    delete_crop_payload = delete_crop_response.json()
    assert delete_crop_payload["collection"]["page_count"] == 1
    assert delete_crop_payload["collection"]["stamp_count"] == 1
    assert len(delete_crop_payload["pages"][0]["stamps"]) == 1

    delete_selected_response = client.post(
        "/api/crops/delete",
        json={"crop_ids": [manual_crop_id]},
    )

    assert delete_selected_response.status_code == 200
    delete_selected_payload = delete_selected_response.json()
    assert delete_selected_payload["collection"]["stamp_count"] == 0
    assert delete_selected_payload["pages"][0]["stamps"] == []

    settings_response = client.get("/api/settings")

    assert settings_response.status_code == 200
    assert "openai_api_key_set" in settings_response.json()
    assert "cost_dashboard" in settings_response.json()
    assert settings_response.json()["cost_dashboard"]["evaluation_run_count"] >= 1

    delete_page_response = client.delete(f"/api/pages/{page_id}")

    assert delete_page_response.status_code == 200
    delete_page_payload = delete_page_response.json()
    assert delete_page_payload["collection"]["page_count"] == 0
    assert delete_page_payload["collection"]["stamp_count"] == 0
    assert delete_page_payload["pages"] == []
