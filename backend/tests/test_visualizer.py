from philalens.visualizer import VISUALIZER_HTML


def test_visualizer_exposes_crop_resize_and_independent_scroll_controls() -> None:
    assert 'id="redetectPage"' in VISUALIZER_HTML
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
    assert "deleteCurrentPage" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}/redetect" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}/crops" in VISUALIZER_HTML
    assert "/api/crops/${stamp.crop_id}" in VISUALIZER_HTML
    assert "/api/pages/${page.page_id}" in VISUALIZER_HTML
    assert "overlay.appendChild(node)" not in VISUALIZER_HTML
