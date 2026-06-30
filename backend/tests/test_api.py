import importlib
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

    delete_crop_response = client.delete(f"/api/crops/{crop_id}")

    assert delete_crop_response.status_code == 200
    delete_crop_payload = delete_crop_response.json()
    assert delete_crop_payload["collection"]["page_count"] == 1
    assert delete_crop_payload["collection"]["stamp_count"] == 1
    assert len(delete_crop_payload["pages"][0]["stamps"]) == 1

    delete_page_response = client.delete(f"/api/pages/{page_id}")

    assert delete_page_response.status_code == 200
    delete_page_payload = delete_page_response.json()
    assert delete_page_payload["collection"]["page_count"] == 0
    assert delete_page_payload["collection"]["stamp_count"] == 0
    assert delete_page_payload["pages"] == []
