import { useCallback, useRef, useState } from "react";
import type { BBox, Page, Stamp } from "../types";

interface Props {
  page: Page;
  selectedCropId: string | null;
  drawMode: boolean;
  onSelect: (cropId: string | null) => void;
  onDrawComplete: (bbox: BBox) => void;
}

interface Draft {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

function draftToBBox(draft: Draft): BBox {
  const x = Math.round(Math.min(draft.x0, draft.x1));
  const y = Math.round(Math.min(draft.y0, draft.y1));
  const w = Math.round(Math.abs(draft.x1 - draft.x0));
  const h = Math.round(Math.abs(draft.y1 - draft.y0));
  return [x, y, w, h];
}

function holePath(stamp: Stamp): string {
  const [x, y, w, h] = stamp.bbox_xywh;
  return `M${x} ${y} h${w} v${h} h${-w} Z`;
}

export default function PageViewer({
  page,
  selectedCropId,
  drawMode,
  onSelect,
  onDrawComplete,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [draft, setDraft] = useState<Draft | null>(null);

  const toPageCoords = useCallback(
    (event: React.PointerEvent): { x: number; y: number } => {
      const svg = svgRef.current!;
      const rect = svg.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * page.width;
      const y = ((event.clientY - rect.top) / rect.height) * page.height;
      return {
        x: Math.max(0, Math.min(page.width, x)),
        y: Math.max(0, Math.min(page.height, y)),
      };
    },
    [page.width, page.height],
  );

  const handlePointerDown = useCallback(
    (event: React.PointerEvent) => {
      if (!drawMode) return;
      event.preventDefault();
      svgRef.current?.setPointerCapture(event.pointerId);
      const { x, y } = toPageCoords(event);
      setDraft({ x0: x, y0: y, x1: x, y1: y });
    },
    [drawMode, toPageCoords],
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent) => {
      if (!draft) return;
      const { x, y } = toPageCoords(event);
      setDraft({ ...draft, x1: x, y1: y });
    },
    [draft, toPageCoords],
  );

  const handlePointerUp = useCallback(() => {
    if (!draft) return;
    const bbox = draftToBBox(draft);
    setDraft(null);
    if (bbox[2] >= 8 && bbox[3] >= 8) onDrawComplete(bbox);
  }, [draft, onDrawComplete]);

  const outerPath = `M0 0 h${page.width} v${page.height} h${-page.width} Z`;
  const selectedStamp = page.stamps.find((stamp) => stamp.crop_id === selectedCropId) ?? null;

  // No selection: shade everything not covered by a crop box (coverage review).
  // With a selection: dim everything except the selected crop.
  const shadePath = selectedStamp
    ? `${outerPath} ${holePath(selectedStamp)}`
    : `${outerPath} ${page.stamps.map(holePath).join(" ")}`;
  const shadeOpacity = selectedStamp ? 0.5 : 0.45;

  return (
    <svg
      ref={svgRef}
      className={`page-svg ${drawMode ? "drawing" : ""}`}
      viewBox={`0 0 ${page.width} ${page.height}`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      style={{ touchAction: "none" }}
    >
      <image
        href={page.normalized_image_url}
        width={page.width}
        height={page.height}
        onClick={() => !drawMode && onSelect(null)}
      />
      <path d={shadePath} fillRule="evenodd" fill="#000" opacity={shadeOpacity} pointerEvents="none" />
      {page.stamps.map((stamp) => {
        const [x, y, w, h] = stamp.bbox_xywh;
        const selected = stamp.crop_id === selectedCropId;
        const needsReview = stamp.review_state === "needs_crop_review";
        return (
          <rect
            key={stamp.crop_id}
            x={x}
            y={y}
            width={w}
            height={h}
            transform={
              stamp.rotation_degrees
                ? `rotate(${stamp.rotation_degrees} ${x + w / 2} ${y + h / 2})`
                : undefined
            }
            fill="transparent"
            stroke={selected ? "#4da3ff" : needsReview ? "#e5b567" : "#7bc98a"}
            strokeWidth={selected ? 3 : 1.5}
            vectorEffect="non-scaling-stroke"
            style={{ cursor: drawMode ? "crosshair" : "pointer" }}
            pointerEvents={drawMode ? "none" : "auto"}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(stamp.crop_id);
            }}
          />
        );
      })}
      {draft &&
        (() => {
          const [x, y, w, h] = draftToBBox(draft);
          return (
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="rgba(77,163,255,0.15)"
              stroke="#4da3ff"
              strokeDasharray="6 4"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              pointerEvents="none"
            />
          );
        })()}
    </svg>
  );
}
