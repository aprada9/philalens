import { useCallback, useEffect, useMemo, useState } from "react";
import Inspector from "../components/Inspector";
import PageViewer from "../components/PageViewer";
import type { BBox, CollectionExport, Stamp } from "../types";

interface Props {
  exp: CollectionExport;
  imageVersion: number;
  busy: boolean;
  selectedPageId: string | null;
  selectedCropId: string | null;
  drawMode: boolean;
  onSelectPage: (pageId: string) => void;
  onSelectCrop: (cropId: string | null) => void;
  onToggleDraw: () => void;
  onDrawComplete: (bbox: BBox) => void;
  onRedetect: (pageId: string) => void;
  onDeletePage: (pageId: string) => void;
  onCropCommit: (cropId: string, bbox: BBox, rotation: number) => void;
  onDeleteCrop: (cropId: string) => void;
  onMarkReady: (cropId: string) => void;
  onMarkReadyMany: (cropIds: string[]) => void;
  onEvaluateCrop: (cropId: string) => void;
}

export default function CurateView({
  exp,
  imageVersion,
  busy,
  selectedPageId,
  selectedCropId,
  drawMode,
  onSelectPage,
  onSelectCrop,
  onToggleDraw,
  onDrawComplete,
  onRedetect,
  onDeletePage,
  onCropCommit,
  onDeleteCrop,
  onMarkReady,
  onMarkReadyMany,
  onEvaluateCrop,
}: Props) {
  const pages = exp.pages;
  const currentPage = pages.find((page) => page.page_id === selectedPageId) ?? pages[0] ?? null;

  const queue: Array<{ stamp: Stamp; pageId: string; pageOrder: number }> = useMemo(
    () =>
      pages.flatMap((page) =>
        page.stamps
          .filter((stamp) => stamp.review_state === "needs_crop_review")
          .map((stamp) => ({ stamp, pageId: page.page_id, pageOrder: page.page_order })),
      ),
    [pages],
  );

  const [queuePos, setQueuePos] = useState(0);
  const position = queue.length === 0 ? 0 : Math.min(queuePos, queue.length - 1);
  const current = queue[position] ?? null;

  // Flagged crops on the page currently under review, for the bulk accept.
  const currentPageQueueIds = useMemo(
    () =>
      current
        ? queue
            .filter((item) => item.pageId === current.pageId)
            .map((item) => item.stamp.crop_id)
        : [],
    [queue, current],
  );

  // Keep the canvas on the page of the crop under review.
  useEffect(() => {
    if (!selectedCropId && current && current.pageId !== currentPage?.page_id) {
      onSelectPage(current.pageId);
    }
  }, [current, selectedCropId, currentPage?.page_id, onSelectPage]);

  const queueKeep = useCallback(() => {
    if (current) onMarkReady(current.stamp.crop_id);
  }, [current, onMarkReady]);

  const queueDelete = useCallback(() => {
    if (current) onDeleteCrop(current.stamp.crop_id);
  }, [current, onDeleteCrop]);

  const queueFix = useCallback(() => {
    if (!current) return;
    onSelectPage(current.pageId);
    onSelectCrop(current.stamp.crop_id);
  }, [current, onSelectPage, onSelectCrop]);

  const queueSkip = useCallback(() => {
    if (queue.length > 0) setQueuePos((pos) => (pos + 1) % queue.length);
  }, [queue.length]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (selectedCropId || busy || !current) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "SELECT" || target.tagName === "TEXTAREA")) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === "k") queueKeep();
      else if (key === "d") queueDelete();
      else if (key === "f") queueFix();
      else if (event.key === "ArrowRight") queueSkip();
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedCropId, busy, current, queueKeep, queueDelete, queueFix, queueSkip]);

  const selectedStamp =
    pages.flatMap((page) => page.stamps).find((stamp) => stamp.crop_id === selectedCropId) ?? null;
  const selectedStampPage =
    pages.find((page) => page.stamps.some((stamp) => stamp.crop_id === selectedCropId)) ?? null;

  const highlightCropId =
    selectedCropId ?? (current && current.pageId === currentPage?.page_id ? current.stamp.crop_id : null);
  const reviewedTotal = exp.collection.stamp_count - queue.length;

  return (
    <div className="view-inner">
      <div className="curate">
        <div>
          {pages.map((page) => {
            const pending = page.stamps.filter(
              (stamp) => stamp.review_state === "needs_crop_review",
            ).length;
            const done = page.stamps.length - pending;
            return (
              <button
                key={page.page_id}
                className={`page-card ${page.page_id === currentPage?.page_id ? "active" : ""}`}
                onClick={() => {
                  onSelectPage(page.page_id);
                  onSelectCrop(null);
                }}
              >
                <img src={page.normalized_image_url} alt="" loading="lazy" />
                <div>
                  <div className="name">Page {page.page_order}</div>
                  <div className="meta">{page.stamps.length} stamps</div>
                  <div className="progress-mini">
                    <div
                      style={{
                        width: `${page.stamps.length ? Math.round((100 * done) / page.stamps.length) : 100}%`,
                      }}
                    />
                  </div>
                  {pending > 0 ? (
                    <div className="meta warn">{pending} to review</div>
                  ) : (
                    <div className="meta">all reviewed</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        <div className="canvas-panel">
          <div className="canvas-toolbar">
            <button className={`btn ${drawMode ? "primary" : ""}`} onClick={onToggleDraw} disabled={!currentPage || busy}>
              {drawMode ? "Drawing… (drag on page)" : "✏️ Add missing stamp"}
            </button>
            <button
              className="btn"
              onClick={() => currentPage && onRedetect(currentPage.page_id)}
              disabled={!currentPage || busy}
            >
              ↻ Re-detect
            </button>
            <button
              className="btn danger"
              onClick={() => {
                if (!currentPage) return;
                if (!window.confirm(`Delete page "${currentPage.original_filename}"?`)) return;
                onDeletePage(currentPage.page_id);
              }}
              disabled={!currentPage || busy}
            >
              Delete page
            </button>
            <span className="grow" />
            <span className="hint">
              {highlightCropId
                ? "Highlighted box is the crop being reviewed."
                : "Shaded = not covered by any crop. Click a box to inspect it."}
            </span>
          </div>
          {currentPage && (
            <PageViewer
              page={currentPage}
              selectedCropId={highlightCropId}
              drawMode={drawMode}
              onSelect={onSelectCrop}
              onDrawComplete={onDrawComplete}
            />
          )}
        </div>

        <div className="side-panel">
          {selectedStamp && selectedStampPage ? (
            <>
              <button className="btn small" onClick={() => onSelectCrop(null)}>
                ← Back{queue.length > 0 ? " to queue" : ""}
              </button>
              <Inspector
                key={selectedStamp.crop_id}
                page={selectedStampPage}
                stamp={selectedStamp}
                imageVersion={imageVersion}
                busy={busy}
                onCommit={(bbox, rotation) => onCropCommit(selectedStamp.crop_id, bbox, rotation)}
                onDelete={() => {
                  onDeleteCrop(selectedStamp.crop_id);
                  onSelectCrop(null);
                }}
                onMarkReady={() => {
                  onMarkReady(selectedStamp.crop_id);
                  onSelectCrop(null);
                }}
                onEvaluate={() => onEvaluateCrop(selectedStamp.crop_id)}
              />
            </>
          ) : queue.length > 0 && current ? (
            <>
              <h3>Review queue</h3>
              <div className="queue-prog">
                Crop {position + 1} of {queue.length} · Page {current.pageOrder} · stamp #
                {current.stamp.crop_index}
              </div>
              <div className="queue-bar">
                <div
                  style={{
                    width: `${(100 * reviewedTotal) / Math.max(1, exp.collection.stamp_count)}%`,
                  }}
                />
              </div>
              <div className="queue-img">
                <img
                  src={`${current.stamp.crop_image_url}?v=${imageVersion}`}
                  alt={`Stamp ${current.stamp.crop_index}`}
                />
              </div>
              {current.stamp.warnings.length > 0 && (
                <div className="chiprow">
                  {current.stamp.warnings.map((warning) => (
                    <span key={warning} className="chip">
                      {warning.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              )}
              <div className="qbtns">
                <button
                  className="btn"
                  style={{ borderColor: "var(--bucket-common)", color: "var(--bucket-common)" }}
                  onClick={queueKeep}
                  disabled={busy}
                >
                  ✓ Keep<small>K</small>
                </button>
                <button
                  className="btn"
                  style={{ borderColor: "var(--accent)", color: "var(--accent)" }}
                  onClick={queueFix}
                  disabled={busy}
                >
                  ⤢ Fix box<small>F</small>
                </button>
                <button
                  className="btn"
                  style={{
                    borderColor: "var(--bucket-investigate)",
                    color: "var(--bucket-investigate)",
                  }}
                  onClick={queueDelete}
                  disabled={busy}
                >
                  ✕ Delete<small>D</small>
                </button>
              </div>
              <div className="kbd-hint">
                <kbd>K</kbd> keep · <kbd>F</kbd> fix · <kbd>D</kbd> delete · <kbd>→</kbd> skip
              </div>
              {currentPageQueueIds.length > 1 && (
                <button
                  className="btn"
                  style={{ marginTop: 10 }}
                  onClick={() => onMarkReadyMany(currentPageQueueIds)}
                  disabled={busy}
                  title="Keeps every crop still flagged on this page — check the page canvas first"
                >
                  ✓✓ Accept all {currentPageQueueIds.length} remaining on this page
                </button>
              )}
            </>
          ) : (
            <>
              <h3>Review queue</h3>
              <p className="muted">
                No crops are waiting for review. Click any box on the page to inspect or edit it,
                or use “Add missing stamp” for anything the detector missed.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
