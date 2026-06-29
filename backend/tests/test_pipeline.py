from philalens.pipeline import build_empty_page_analysis, summarize_collection


def test_build_empty_page_analysis_records_input_image() -> None:
    page = build_empty_page_analysis(page_id="page-1", image_filename="album.jpg")

    assert page.page_id == "page-1"
    assert page.image_filename == "album.jpg"
    assert page.stamps == []
    assert page.notes


def test_summarize_collection_without_values() -> None:
    pages = [
        build_empty_page_analysis(page_id="page-1", image_filename="one.jpg"),
        build_empty_page_analysis(page_id="page-2", image_filename="two.jpg"),
    ]

    summary = summarize_collection(pages)

    assert summary.page_count == 2
    assert summary.stamp_count == 0
    assert summary.estimated_value_low is None
    assert summary.estimated_value_high is None

