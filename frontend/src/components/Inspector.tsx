import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { BBox, Page, Stamp } from "../types";
import { bucketLabel } from "./StampList";

interface Props {
  page: Page;
  stamp: Stamp;
  imageVersion: number;
  busy: boolean;
  onCommit: (bbox: BBox, rotationDegrees: number) => void;
  onDelete: () => void;
  onMarkReady: () => void;
  onEvaluate: () => void;
}

type DragMode =
  | { type: "corner"; corner: 0 | 1 | 2 | 3 }
  | { type: "move"; offsetX: number; offsetY: number }
  | { type: "rotate" };

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

const MIN_SIZE = 8;

function clampBox(box: Box, pageWidth: number, pageHeight: number): Box {
  const w = Math.max(MIN_SIZE, Math.min(Math.round(box.w), pageWidth));
  const h = Math.max(MIN_SIZE, Math.min(Math.round(box.h), pageHeight));
  const x = Math.max(0, Math.min(Math.round(box.x), pageWidth - w));
  const y = Math.max(0, Math.min(Math.round(box.y), pageHeight - h));
  return { x, y, w, h };
}

function TagList({ items, className }: { items: string[]; className?: string }) {
  if (items.length === 0) return null;
  return (
    <div className="tag-list">
      {items.map((item) => (
        <span key={item} className={`badge ${className ?? ""}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

export default function Inspector({
  page,
  stamp,
  imageVersion,
  busy,
  onCommit,
  onDelete,
  onMarkReady,
  onEvaluate,
}: Props) {
  const [box, setBox] = useState<Box>({
    x: stamp.bbox_xywh[0],
    y: stamp.bbox_xywh[1],
    w: stamp.bbox_xywh[2],
    h: stamp.bbox_xywh[3],
  });
  const [rotation, setRotation] = useState(stamp.rotation_degrees);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<DragMode | null>(null);

  useEffect(() => {
    setBox({
      x: stamp.bbox_xywh[0],
      y: stamp.bbox_xywh[1],
      w: stamp.bbox_xywh[2],
      h: stamp.bbox_xywh[3],
    });
    setRotation(stamp.rotation_degrees);
  }, [stamp.bbox_xywh, stamp.rotation_degrees]);

  // The editor view is framed around the last committed bbox so it stays
  // stable while dragging; it re-centers after each commit.
  const viewBox = useMemo(() => {
    const [x, y, w, h] = stamp.bbox_xywh;
    const margin = Math.max(w, h) * 0.45 + 24;
    return {
      x: x - margin,
      y: y - margin,
      w: w + margin * 2,
      h: h + margin * 2,
    };
  }, [stamp.bbox_xywh]);

  const toPageCoords = useCallback(
    (event: PointerEvent | React.PointerEvent): { x: number; y: number } => {
      const svg = svgRef.current!;
      const rect = svg.getBoundingClientRect();
      return {
        x: viewBox.x + ((event.clientX - rect.left) / rect.width) * viewBox.w,
        y: viewBox.y + ((event.clientY - rect.top) / rect.height) * viewBox.h,
      };
    },
    [viewBox],
  );

  const startDrag = useCallback((event: React.PointerEvent, mode: DragMode) => {
    event.preventDefault();
    event.stopPropagation();
    dragRef.current = mode;
    svgRef.current?.setPointerCapture(event.pointerId);
  }, []);

  const handlePointerMove = useCallback(
    (event: React.PointerEvent) => {
      const mode = dragRef.current;
      if (!mode) return;
      const point = toPageCoords(event);
      if (mode.type === "move") {
        setBox((current) =>
          clampBox(
            { ...current, x: point.x - mode.offsetX, y: point.y - mode.offsetY },
            page.width,
            page.height,
          ),
        );
      } else if (mode.type === "corner") {
        setBox((current) => {
          // The dragged corner moves; the opposite corner stays anchored.
          const movingRight = mode.corner === 1 || mode.corner === 3;
          const movingBottom = mode.corner === 2 || mode.corner === 3;
          const anchorX = movingRight ? current.x : current.x + current.w;
          const anchorY = movingBottom ? current.y : current.y + current.h;
          const movedX = movingRight
            ? Math.max(point.x, anchorX + MIN_SIZE)
            : Math.min(point.x, anchorX - MIN_SIZE);
          const movedY = movingBottom
            ? Math.max(point.y, anchorY + MIN_SIZE)
            : Math.min(point.y, anchorY - MIN_SIZE);
          return clampBox(
            {
              x: Math.min(anchorX, movedX),
              y: Math.min(anchorY, movedY),
              w: Math.abs(movedX - anchorX),
              h: Math.abs(movedY - anchorY),
            },
            page.width,
            page.height,
          );
        });
      } else {
        setBox((current) => {
          const cx = current.x + current.w / 2;
          const cy = current.y + current.h / 2;
          let degrees = (Math.atan2(point.x - cx, -(point.y - cy)) * 180) / Math.PI;
          if (Math.abs(degrees) < 1.5) degrees = 0;
          setRotation(Math.round(degrees * 10) / 10);
          return current;
        });
      }
    },
    [toPageCoords, page.width, page.height],
  );

  const handlePointerUp = useCallback(() => {
    if (!dragRef.current) return;
    dragRef.current = null;
    const changed =
      box.x !== stamp.bbox_xywh[0] ||
      box.y !== stamp.bbox_xywh[1] ||
      box.w !== stamp.bbox_xywh[2] ||
      box.h !== stamp.bbox_xywh[3] ||
      rotation !== stamp.rotation_degrees;
    if (changed) onCommit([box.x, box.y, box.w, box.h], rotation);
  }, [box, rotation, stamp, onCommit]);

  const cx = box.x + box.w / 2;
  const cy = box.y + box.h / 2;
  const handleRadius = viewBox.w / 46;
  const rotationOffset = box.h / 2 + viewBox.w / 12;
  const theta = (rotation * Math.PI) / 180;
  const rotationHandle = {
    x: cx + rotationOffset * Math.sin(theta),
    y: cy - rotationOffset * Math.cos(theta),
  };
  const corners: Array<[number, number]> = [
    [box.x, box.y],
    [box.x + box.w, box.y],
    [box.x, box.y + box.h],
    [box.x + box.w, box.y + box.h],
  ];

  const observation = stamp.observation;
  const valuation = stamp.valuation;
  const numericChanged =
    box.x !== stamp.bbox_xywh[0] ||
    box.y !== stamp.bbox_xywh[1] ||
    box.w !== stamp.bbox_xywh[2] ||
    box.h !== stamp.bbox_xywh[3] ||
    rotation !== stamp.rotation_degrees;

  return (
    <div>
      <div className="inspector-block">
        <img
          className="crop-preview"
          src={`${stamp.crop_image_url}?v=${imageVersion}`}
          alt={`Stamp ${stamp.crop_index} crop`}
        />
        <div className="row">
          <span className="badge">#{stamp.crop_index}</span>
          {stamp.review_state === "needs_crop_review" ? (
            <span className="badge review">needs crop review</span>
          ) : (
            <span className="badge ok">{stamp.review_state}</span>
          )}
          <span className="badge">conf {stamp.segmentation_confidence.toFixed(2)}</span>
        </div>
        <TagList items={stamp.warnings} className="review" />
        <div className="row">
          <button onClick={onEvaluate} disabled={busy}>
            Evaluate this stamp
          </button>
          <button onClick={onMarkReady} disabled={busy}>
            Mark crop ready
          </button>
          <button className="danger" onClick={onDelete} disabled={busy}>
            Delete crop
          </button>
        </div>
      </div>

      <div className="inspector-block">
        <h3>Crop editor</h3>
        <svg
          ref={svgRef}
          className="zoom-editor"
          viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          <image href={page.normalized_image_url} width={page.width} height={page.height} />
          <g transform={rotation ? `rotate(${rotation} ${cx} ${cy})` : undefined}>
            <rect
              x={box.x}
              y={box.y}
              width={box.w}
              height={box.h}
              fill="rgba(77,163,255,0.10)"
              stroke="#4da3ff"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              style={{ cursor: "move" }}
              onPointerDown={(event) => {
                const point = toPageCoords(event);
                startDrag(event, {
                  type: "move",
                  offsetX: point.x - box.x,
                  offsetY: point.y - box.y,
                });
              }}
            />
          </g>
          <line
            x1={cx}
            y1={cy}
            x2={rotationHandle.x}
            y2={rotationHandle.y}
            stroke="#4da3ff"
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
            pointerEvents="none"
          />
          <circle
            cx={rotationHandle.x}
            cy={rotationHandle.y}
            r={handleRadius}
            fill="#e5b567"
            style={{ cursor: "grab" }}
            onPointerDown={(event) => startDrag(event, { type: "rotate" })}
          />
          {corners.map(([hx, hy], index) => (
            <rect
              key={index}
              x={hx - handleRadius}
              y={hy - handleRadius}
              width={handleRadius * 2}
              height={handleRadius * 2}
              fill="#4da3ff"
              style={{ cursor: index === 0 || index === 3 ? "nwse-resize" : "nesw-resize" }}
              onPointerDown={(event) =>
                startDrag(event, { type: "corner", corner: index as 0 | 1 | 2 | 3 })
              }
            />
          ))}
        </svg>
        <div className="row">
          <label>
            x{" "}
            <input
              type="number"
              value={box.x}
              onChange={(event) => setBox({ ...box, x: Number(event.target.value) })}
            />
          </label>
          <label>
            y{" "}
            <input
              type="number"
              value={box.y}
              onChange={(event) => setBox({ ...box, y: Number(event.target.value) })}
            />
          </label>
          <label>
            w{" "}
            <input
              type="number"
              value={box.w}
              onChange={(event) => setBox({ ...box, w: Number(event.target.value) })}
            />
          </label>
          <label>
            h{" "}
            <input
              type="number"
              value={box.h}
              onChange={(event) => setBox({ ...box, h: Number(event.target.value) })}
            />
          </label>
          <label>
            rot{" "}
            <input
              type="number"
              step={0.5}
              value={rotation}
              onChange={(event) => setRotation(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="row">
          <button
            className="primary"
            disabled={busy || !numericChanged}
            onClick={() => {
              const clamped = clampBox(box, page.width, page.height);
              onCommit([clamped.x, clamped.y, clamped.w, clamped.h], rotation);
            }}
          >
            Apply crop changes
          </button>
        </div>
      </div>

      <div className="inspector-block">
        <h3>Observation</h3>
        {observation.status !== "available" ? (
          <p className="muted">{observation.note ?? "No observation recorded yet."}</p>
        ) : (
          <>
            <dl className="kv">
              <dt>Issuer</dt>
              <dd>{observation.issuer_hint ?? "—"}</dd>
              <dt>Denomination</dt>
              <dd>{observation.denomination_hint ?? "—"}</dd>
              <dt>Date hint</dt>
              <dd>{observation.date_hint ?? "—"}</dd>
              <dt>Design</dt>
              <dd>{observation.design_subject ?? "—"}</dd>
              <dt>Cancellation</dt>
              <dd>{observation.cancellation_state ?? "—"}</dd>
              <dt>Confidence</dt>
              <dd>{(observation.confidence ?? 0).toFixed(2)}</dd>
            </dl>
            {(observation.visible_text?.length ?? 0) > 0 && (
              <>
                <span className="muted">Visible text</span>
                <TagList items={observation.visible_text ?? []} />
              </>
            )}
            {(observation.condition_notes?.length ?? 0) > 0 && (
              <>
                <span className="muted">Condition</span>
                <TagList items={observation.condition_notes ?? []} />
              </>
            )}
            {(observation.image_quality_warnings?.length ?? 0) > 0 && (
              <>
                <span className="muted">Image quality warnings</span>
                <TagList items={observation.image_quality_warnings ?? []} className="review" />
              </>
            )}
            {(observation.unobservable_factors?.length ?? 0) > 0 && (
              <>
                <span className="muted">Not observable from this photo</span>
                <TagList items={observation.unobservable_factors ?? []} />
              </>
            )}
          </>
        )}
      </div>

      <div className="inspector-block">
        <h3>Valuation</h3>
        {valuation.status !== "available" ? (
          <p className="muted">{valuation.note ?? "No valuation recorded yet."}</p>
        ) : (
          <>
            <dl className="kv">
              <dt>Bucket</dt>
              <dd>{valuation.value_bucket ? bucketLabel(valuation.value_bucket) : "—"}</dd>
              <dt>Range</dt>
              <dd>
                {valuation.estimated_value_low === null &&
                valuation.estimated_value_high === null
                  ? "no range yet"
                  : `${valuation.estimated_value_low ?? "?"} – ${valuation.estimated_value_high ?? "?"} ${valuation.currency}`}
              </dd>
              <dt>Confidence</dt>
              <dd>{valuation.confidence.toFixed(2)}</dd>
              <dt>Next action</dt>
              <dd>{valuation.recommended_next_action ?? "—"}</dd>
            </dl>
            {(valuation.uncertainty_warnings?.length ?? 0) > 0 && (
              <>
                <span className="muted">Uncertainty</span>
                <TagList items={valuation.uncertainty_warnings ?? []} className="review" />
              </>
            )}
            {(valuation.assumptions?.length ?? 0) > 0 && (
              <>
                <span className="muted">Assumptions</span>
                <ul className="muted" style={{ margin: "4px 0", paddingLeft: 18 }}>
                  {(valuation.assumptions ?? []).map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>

      {stamp.identification.candidates.length > 0 && (
        <div className="inspector-block">
          <h3>Identity candidates</h3>
          <p className="muted">
            AI priors from the photo — not verified against any catalog or source.
          </p>
          {stamp.identification.candidates.map((candidate) => (
            <div key={candidate.candidate_id} style={{ marginBottom: 10 }}>
              <div>
                <span className="badge attention">#{candidate.rank}</span>{" "}
                <b>{candidate.title ?? candidate.issuer ?? "Unknown"}</b>{" "}
                <span className="muted">confidence {candidate.match_score.toFixed(2)}</span>
              </div>
              <dl className="kv">
                {candidate.issuer && (
                  <>
                    <dt>Country</dt>
                    <dd>{candidate.issuer}</dd>
                  </>
                )}
                {candidate.year !== null && (
                  <>
                    <dt>Year</dt>
                    <dd>{candidate.year}</dd>
                  </>
                )}
                {candidate.denomination && (
                  <>
                    <dt>Denomination</dt>
                    <dd>{candidate.denomination}</dd>
                  </>
                )}
              </dl>
              {candidate.variant_notes.length > 0 && (
                <ul className="muted" style={{ margin: "4px 0", paddingLeft: 18 }}>
                  {candidate.variant_notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {stamp.evidence.length > 0 && (
        <div className="inspector-block">
          <h3>Evidence</h3>
          {stamp.evidence.map((item) => (
            <dl className="kv" key={item.evidence_id}>
              <dt>{item.source_name}</dt>
              <dd>
                {item.evidence_tier ?? item.source_type}
                {item.price !== null && ` · ${item.price} ${item.currency ?? ""}`}
                {item.source_url && (
                  <>
                    {" "}
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      source
                    </a>
                  </>
                )}
              </dd>
            </dl>
          ))}
        </div>
      )}
    </div>
  );
}
