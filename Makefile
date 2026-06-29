.PHONY: context-check smoke test

context-check:
	python3 scripts/check_agent_context.py --base HEAD~1 --head HEAD

smoke:
	PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys; sys.path.insert(0, 'backend/src'); from philalens.pipeline import build_empty_page_analysis, summarize_collection; page = build_empty_page_analysis('page-1', 'album.jpg'); summary = summarize_collection([page]); assert page.image_filename == 'album.jpg'; assert summary.page_count == 1; assert summary.stamp_count == 0; print('smoke test passed')"

test:
	cd backend && pytest

