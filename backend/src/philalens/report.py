"""Printable recapture kit and collection report (Phase 4).

Both documents are self-contained HTML pages built from the collection
export (which overlays each crop's newest results across runs). Model
output is escaped before rendering. Language stays conservative: research
estimates with evidence, never formal appraisals.
"""

from __future__ import annotations

import html
from collections import Counter
from typing import Any, cast

from .exports import build_collection_export
from .storage import PhilalensStore

ATTENTION_BUCKETS = {"possibly_interesting", "investigate", "needs_expert_check"}

OWNER_REVIEWED_PREFIX = "Owner-reviewed range"

# Photo instructions per unobservable factor reported by the vision pass.
_RECAPTURE_INSTRUCTIONS: list[tuple[tuple[str, ...], str]] = [
    (("watermark",), "Back of the stamp, backlit (or with watermark fluid), to reveal the watermark."),
    (("gum",), "Back of the stamp in flat, even light, to judge gum condition."),
    (("paper",), "Back of the stamp, slightly raking light, to judge the paper type."),
    (("perforation",), "Straight-on close-up of one perforated edge next to a ruler (for gauge measurement)."),
    (("thin", "repair", "fault"), "Back of the stamp, backlit, to expose thins or repairs."),
]

_PAGE_STYLE = """
body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 24px auto; max-width: 900px;
       color: #1a1a1a; line-height: 1.45; }
h1 { font-size: 22px; margin-bottom: 2px; }
h2 { font-size: 16px; margin: 22px 0 6px; }
p.meta { color: #666; margin-top: 0; font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f2f2f2; }
img.thumb { width: 72px; height: 72px; object-fit: contain; background: #eee; border-radius: 4px; }
.stamp-card { border: 1px solid #ccc; border-radius: 8px; padding: 10px 12px; margin: 10px 0;
              page-break-inside: avoid; display: flex; gap: 12px; }
.stamp-card img { width: 110px; height: 110px; object-fit: contain; background: #eee;
                  border-radius: 6px; flex-shrink: 0; }
ul { margin: 6px 0 0 18px; padding: 0; }
.disclaimer { border: 1px solid #d0a000; background: #fff8e0; padding: 10px 12px;
              border-radius: 6px; font-size: 13px; margin: 14px 0; }
.small { font-size: 12px; color: #555; }
@media print { body { margin: 8mm; } a { color: inherit; text-decoration: none; } }
"""


def _esc(value: object) -> str:
    return html.escape(str(value)) if value is not None else ""


def _stamp_headline(stamp: dict[str, Any]) -> str:
    candidates = stamp.get("identification", {}).get("candidates", [])
    top = min(candidates, key=lambda c: c.get("rank", 99), default=None)
    if not top:
        return "Unidentified"
    parts = [top.get("issuer"), top.get("title"), top.get("year"), top.get("denomination")]
    return " · ".join(_esc(part) for part in parts if part)


def _is_owner_reviewed(valuation: dict[str, Any]) -> bool:
    return any(
        str(item).startswith(OWNER_REVIEWED_PREFIX) for item in valuation.get("assumptions", [])
    )


def _recapture_checklist(stamp: dict[str, Any]) -> list[str]:
    factors = " ".join(
        str(factor) for factor in stamp.get("observation", {}).get("unobservable_factors", [])
    ).lower()
    checklist = ["Sharp, straight-on macro photo of the front in daylight (no shadows)."]
    for keywords, instruction in _RECAPTURE_INSTRUCTIONS:
        if any(keyword in factors for keyword in keywords):
            checklist.append(instruction)
    return checklist


def build_recapture_kit_html(store: PhilalensStore, collection_id: str) -> str | None:
    export = build_collection_export(store, collection_id)
    if export is None:
        return None

    flagged: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for page in cast(list[dict[str, Any]], export["pages"]):
        for stamp in cast(list[dict[str, Any]], page["stamps"]):
            bucket = cast(dict[str, Any], stamp["valuation"]).get("value_bucket")
            if bucket in ATTENTION_BUCKETS:
                flagged.append((page, stamp))

    cards: list[str] = []
    for page, stamp in flagged:
        valuation = cast(dict[str, Any], stamp["valuation"])
        rationale = next(
            (
                _esc(str(item).removeprefix("Model rationale:").strip())
                for item in valuation.get("assumptions", [])
                if str(item).startswith("Model rationale:")
            ),
            "",
        )
        checklist = "".join(f"<li>{_esc(item)}</li>" for item in _recapture_checklist(stamp))
        reviewed_note = (
            " · <b>owner-reviewed range already set</b>" if _is_owner_reviewed(valuation) else ""
        )
        cards.append(
            f"""
<div class="stamp-card">
  <img src="{_esc(stamp["crop_image_url"])}" alt="stamp" />
  <div>
    <b>Page {_esc(page["page_order"])}</b> ({_esc(page["original_filename"])}) ·
    stamp #{_esc(stamp["crop_index"])} · bucket:
    <b>{_esc(valuation.get("value_bucket", "?"))}</b>{reviewed_note}<br/>
    {_stamp_headline(stamp)}<br/>
    <span class="small">{rationale}</span>
    <ul>{checklist}</ul>
  </div>
</div>"""
        )

    collection = cast(dict[str, Any], export["collection"])
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Philalens recapture kit</title>
<style>{_PAGE_STYLE}</style></head><body>
<h1>Recapture kit — {len(flagged)} flagged stamps</h1>
<p class="meta">Collection {_esc(collection["collection_id"])} ·
{_esc(collection["page_count"])} pages · {_esc(collection["stamp_count"])} stamps.
Print this list and take it to the albums; upload each new photo on the stamp's card
("Replace photo"), then re-analyze the stamp.</p>
<div class="disclaimer">General tips: daylight or bright diffuse light, no flash glare,
fill the frame with the stamp, hold the camera parallel to the page. Back-side photos
require removing the stamp from its mount only if it is safe to do so.</div>
{"".join(cards) if cards else "<p>No stamps are currently flagged for recapture.</p>"}
</body></html>"""


def build_collection_report_html(store: PhilalensStore, collection_id: str) -> str | None:
    export = build_collection_export(store, collection_id)
    if export is None:
        return None

    collection = cast(dict[str, Any], export["collection"])
    pages = cast(list[dict[str, Any]], export["pages"])
    stamps = [stamp for page in pages for stamp in cast(list[dict[str, Any]], page["stamps"])]

    bucket_counts: Counter[str] = Counter()
    analyzed = 0
    reviewed_rows: list[str] = []
    reviewed_totals: dict[str, list[float]] = {}
    attention_rows: list[str] = []
    for page in pages:
        for stamp in cast(list[dict[str, Any]], page["stamps"]):
            valuation = cast(dict[str, Any], stamp["valuation"])
            observation = cast(dict[str, Any], stamp["observation"])
            bucket = valuation.get("value_bucket")
            if bucket:
                bucket_counts[str(bucket)] += 1
            if observation.get("status") == "available" and (observation.get("confidence") or 0) > 0:
                analyzed += 1

            low = valuation.get("estimated_value_low")
            high = valuation.get("estimated_value_high")
            owner_reviewed = _is_owner_reviewed(valuation)
            row = (
                f"<tr><td><img class='thumb' src='{_esc(stamp['crop_image_url'])}'/></td>"
                f"<td>p{_esc(page['page_order'])} · #{_esc(stamp['crop_index'])}</td>"
                f"<td>{_stamp_headline(stamp)}</td>"
                f"<td>{_esc(bucket)}</td>"
            )
            if owner_reviewed and low is not None and high is not None:
                currency = _esc(valuation.get("currency", ""))
                note = next(
                    (
                        _esc(str(item).removeprefix("Owner note:").strip())
                        for item in valuation.get("assumptions", [])
                        if str(item).startswith("Owner note:")
                    ),
                    "",
                )
                reviewed_rows.append(
                    row + f"<td>{low:g}–{high:g} {currency}</td><td>{note}</td></tr>"
                )
                totals = reviewed_totals.setdefault(str(valuation.get("currency", "?")), [0.0, 0.0])
                totals[0] += float(low)
                totals[1] += float(high)
            elif bucket in ATTENTION_BUCKETS:
                attention_rows.append(
                    row + "<td>no evidence-backed range yet</td><td></td></tr>"
                )

    bucket_table = "".join(
        f"<tr><td>{_esc(bucket)}</td><td>{count}</td></tr>"
        for bucket, count in bucket_counts.most_common()
    )
    totals_line = (
        " · ".join(
            f"{totals[0]:g}–{totals[1]:g} {_esc(currency)}"
            for currency, totals in sorted(reviewed_totals.items())
        )
        or "none yet"
    )
    table_head = (
        "<tr><th></th><th>Location</th><th>Identity (AI prior)</th>"
        "<th>Bucket</th><th>Range</th><th>Note</th></tr>"
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Philalens collection report</title>
<style>{_PAGE_STYLE}</style></head><body>
<h1>Collection report</h1>
<p class="meta">Collection {_esc(collection["collection_id"])} ·
{_esc(collection["page_count"])} pages · {_esc(collection["stamp_count"])} stamps ·
{analyzed} analyzed by AI vision · {_esc(collection["needs_crop_review_count"])} still
pending crop review.</p>
<div class="disclaimer"><b>This is a research estimate, not a formal appraisal.</b>
Identifications are AI priors unless noted; value ranges exist only where the owner
reviewed realized-sale evidence. Watermarks, gum, paper, hidden faults, and authenticity
cannot be judged from front photos alone.</div>
<h2>Value triage</h2>
<table><tr><th>Bucket</th><th>Stamps</th></tr>{bucket_table}</table>
<h2>Owner-reviewed value ranges ({len(reviewed_rows)} stamps · total {totals_line})</h2>
<table>{table_head}{"".join(reviewed_rows) if reviewed_rows else ""}</table>
{"" if reviewed_rows else "<p class='small'>None yet — use the sold-listings link on a flagged stamp, then Set value range.</p>"}
<h2>Flagged, awaiting evidence or review ({len(attention_rows)} stamps)</h2>
<table>{table_head}{"".join(attention_rows) if attention_rows else ""}</table>
{"" if attention_rows else "<p class='small'>Nothing outstanding.</p>"}
</body></html>"""
