"""Initial analysis pipeline contracts.

The first implementation returns structured placeholders. Real segmentation,
catalog matching, and valuation should fill the same contracts as they mature.
"""

from .models import CollectionSummary, PageAnalysis


def build_empty_page_analysis(page_id: str, image_filename: str) -> PageAnalysis:
    return PageAnalysis(
        page_id=page_id,
        image_filename=image_filename,
        notes=[
            "Image accepted. Stamp detection, catalog matching, and valuation are not enabled yet."
        ],
    )


def summarize_collection(pages: list[PageAnalysis]) -> CollectionSummary:
    stamp_count = sum(len(page.stamps) for page in pages)
    low_values = [
        stamp.estimated_value_low
        for page in pages
        for stamp in page.stamps
        if stamp.estimated_value_low is not None
    ]
    high_values = [
        stamp.estimated_value_high
        for page in pages
        for stamp in page.stamps
        if stamp.estimated_value_high is not None
    ]

    return CollectionSummary(
        page_count=len(pages),
        stamp_count=stamp_count,
        estimated_value_low=sum(low_values) if low_values else None,
        estimated_value_high=sum(high_values) if high_values else None,
    )

