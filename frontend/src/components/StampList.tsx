import { useMemo } from "react";
import type { StampFilter } from "../App";
import type { Page, Stamp } from "../types";

interface Props {
  stamps: Stamp[];
  pages: Page[];
  selectedCropId: string | null;
  checkedCropIds: Set<string>;
  filter: StampFilter;
  imageVersion: number;
  busy: boolean;
  onFilterChange: (filter: StampFilter) => void;
  onSelect: (stamp: Stamp) => void;
  onToggleCheck: (cropId: string) => void;
  onCheckMany: (cropIds: string[], checked: boolean) => void;
  onDeleteChecked: () => void;
  onMarkReadyChecked: () => void;
  onEvaluateChecked: () => void;
}

export function bucketLabel(bucket: string): string {
  return bucket.replaceAll("_", " ");
}

export default function StampList({
  stamps,
  pages,
  selectedCropId,
  checkedCropIds,
  filter,
  imageVersion,
  busy,
  onFilterChange,
  onSelect,
  onToggleCheck,
  onCheckMany,
  onDeleteChecked,
  onMarkReadyChecked,
  onEvaluateChecked,
}: Props) {
  const pageOrderById = useMemo(
    () => new Map(pages.map((page) => [page.page_id, page.page_order])),
    [pages],
  );
  const pageIdByCrop = useMemo(() => {
    const map = new Map<string, string>();
    for (const page of pages) {
      for (const stamp of page.stamps) map.set(stamp.crop_id, page.page_id);
    }
    return map;
  }, [pages]);

  const buckets = useMemo(() => {
    const counts = new Map<string, number>();
    for (const stamp of stamps) {
      const bucket = stamp.valuation.value_bucket;
      if (bucket) counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [stamps]);

  const pendingReviewCount = useMemo(
    () => stamps.filter((stamp) => stamp.review_state === "needs_crop_review").length,
    [stamps],
  );

  const visible = useMemo(() => {
    if (filter.kind === "pending_review") {
      return stamps.filter((stamp) => stamp.review_state === "needs_crop_review");
    }
    if (filter.kind === "bucket") {
      return stamps.filter((stamp) => stamp.valuation.value_bucket === filter.bucket);
    }
    return stamps;
  }, [stamps, filter]);

  const allVisibleChecked =
    visible.length > 0 && visible.every((stamp) => checkedCropIds.has(stamp.crop_id));

  return (
    <div className="stamp-section">
      <h3>
        Stamps ({visible.length}
        {visible.length !== stamps.length ? ` of ${stamps.length}` : ""})
      </h3>
      <div className="filter-chips">
        <button
          className={`chip ${filter.kind === "all" ? "active" : ""}`}
          onClick={() => onFilterChange({ kind: "all" })}
        >
          All {stamps.length}
        </button>
        <button
          className={`chip ${filter.kind === "pending_review" ? "active" : ""}`}
          onClick={() => onFilterChange({ kind: "pending_review" })}
        >
          Needs crop review {pendingReviewCount}
        </button>
        {buckets.map(([bucket, count]) => (
          <button
            key={bucket}
            className={`chip ${filter.kind === "bucket" && filter.bucket === bucket ? "active" : ""}`}
            onClick={() => onFilterChange({ kind: "bucket", bucket })}
          >
            {bucketLabel(bucket)} {count}
          </button>
        ))}
      </div>
      <div className="stamp-list">
        {visible.length > 0 && (
          <label className="stamp-row" style={{ color: "var(--text-dim)", fontSize: 12 }}>
            <input
              type="checkbox"
              checked={allVisibleChecked}
              onChange={(event) =>
                onCheckMany(
                  visible.map((stamp) => stamp.crop_id),
                  event.target.checked,
                )
              }
            />
            Select all shown
          </label>
        )}
        {visible.map((stamp) => {
          const bucket = stamp.valuation.value_bucket;
          const needsReview = stamp.review_state === "needs_crop_review";
          const attention =
            bucket === "possibly_interesting" || bucket === "needs_expert_check";
          const pageOrder = pageOrderById.get(pageIdByCrop.get(stamp.crop_id) ?? "") ?? "?";
          return (
            <div
              key={stamp.crop_id}
              className={`stamp-row ${stamp.crop_id === selectedCropId ? "selected" : ""}`}
              onClick={() => onSelect(stamp)}
            >
              <input
                type="checkbox"
                checked={checkedCropIds.has(stamp.crop_id)}
                onClick={(event) => event.stopPropagation()}
                onChange={() => onToggleCheck(stamp.crop_id)}
              />
              <img
                src={`${stamp.crop_image_url}?v=${imageVersion}`}
                alt={`Stamp ${stamp.crop_index}`}
                loading="lazy"
              />
              <div className="label">
                <div>
                  p{pageOrder} · #{stamp.crop_index}{" "}
                  {needsReview ? (
                    <span className="badge review">crop review</span>
                  ) : (
                    <span className="badge ok">crop ok</span>
                  )}
                  {bucket && (
                    <span className={`badge ${attention ? "attention" : ""}`}>
                      {bucketLabel(bucket)}
                    </span>
                  )}
                </div>
                <div className="desc">{stamp.description}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="batch-actions">
        <span className="muted">{checkedCropIds.size} selected</span>
        <button onClick={onEvaluateChecked} disabled={busy || checkedCropIds.size === 0}>
          Evaluate
        </button>
        <button onClick={onMarkReadyChecked} disabled={busy || checkedCropIds.size === 0}>
          Mark crop ready
        </button>
        <button className="danger" onClick={onDeleteChecked} disabled={busy || checkedCropIds.size === 0}>
          Delete
        </button>
      </div>
    </div>
  );
}
