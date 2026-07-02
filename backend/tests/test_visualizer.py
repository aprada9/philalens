from philalens.visualizer import VISUALIZER_HTML


def test_visualizer_exposes_crop_resize_and_independent_scroll_controls() -> None:
    assert 'id="redetectPage"' in VISUALIZER_HTML
    assert 'id="evaluateCollection"' in VISUALIZER_HTML
    assert 'id="evaluateSelected"' in VISUALIZER_HTML
    assert 'id="deleteSelected"' in VISUALIZER_HTML
    assert 'id="selectVisible"' in VISUALIZER_HTML
    assert 'id="clearSelected"' in VISUALIZER_HTML
    assert 'id="markReadySelected"' in VISUALIZER_HTML
    assert 'id="settingsButton"' in VISUALIZER_HTML
    assert 'id="settingsPanel"' in VISUALIZER_HTML
    assert 'id="settingsCostDashboard"' in VISUALIZER_HTML
    assert 'id="evaluationProgress"' in VISUALIZER_HTML
    assert 'id="evaluationProgressBar"' in VISUALIZER_HTML
    assert 'id="evaluationProgressImage"' in VISUALIZER_HTML
    assert "scroll-band" in VISUALIZER_HTML
    assert 'id="cropEditorBox"' in VISUALIZER_HTML
    assert 'id="reviewOnly"' in VISUALIZER_HTML
    assert 'id="addCrop"' in VISUALIZER_HTML
    assert 'id="deleteCrop"' in VISUALIZER_HTML
    assert 'id="deletePage"' in VISUALIZER_HTML
    assert "coverage-mask" in VISUALIZER_HTML
    assert "drawCoverageMask" in VISUALIZER_HTML
    assert "manual-crop-preview" in VISUALIZER_HTML
    assert "startManualCrop" in VISUALIZER_HTML
    assert "resize-handle" in VISUALIZER_HTML
    assert "rotate-handle" in VISUALIZER_HTML
    assert "startResize" in VISUALIZER_HTML
    assert "startRotate" in VISUALIZER_HTML
    assert "deleteCurrentCrop" in VISUALIZER_HTML
    assert "deleteSelectedCrops" in VISUALIZER_HTML
    assert "markSelectedCropsReady" in VISUALIZER_HTML
    assert "selectVisibleStamps" in VISUALIZER_HTML
    assert "Crop: ${cropLabel" in VISUALIZER_HTML
    assert "Eval: ${bucketLabel" in VISUALIZER_HTML
    assert "evaluateSelectedCrops" in VISUALIZER_HTML
    assert "openSettings" in VISUALIZER_HTML
    assert "renderSettingsCostDashboard" in VISUALIZER_HTML
    assert "evaluationCostText" in VISUALIZER_HTML
    assert "showEvaluationProgress" in VISUALIZER_HTML
    assert "pollEvaluationJob" in VISUALIZER_HTML
    assert "deleteCurrentPage" in VISUALIZER_HTML
    assert "/api/collections/${collectionId}/evaluate" in VISUALIZER_HTML
    assert "/api/collections/${collectionId}/evaluation-cost-estimate" in VISUALIZER_HTML
    assert "/api/crops/delete" in VISUALIZER_HTML
    assert "/api/crops/mark-ready" in VISUALIZER_HTML
    assert "/api/collections/${collectionId}/evaluate/start" in VISUALIZER_HTML
    assert "/api/evaluation-jobs/${jobId}" in VISUALIZER_HTML
    assert "/api/settings" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}/redetect" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}/crops" in VISUALIZER_HTML
    assert "/api/crops/${stamp.crop_id}" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}" in VISUALIZER_HTML
    assert "overlay.appendChild(node)" not in VISUALIZER_HTML
