import { useEffect, useState } from "react";
import type { CollectionExport, CollectionInfo, EvaluationJob } from "../types";

export type ViewName = "overview" | "curate" | "stamps";

interface Props {
  collections: CollectionInfo[];
  exp: CollectionExport | null;
  view: ViewName;
  job: EvaluationJob | null;
  jobRunning: boolean;
  theme: "light" | "dark";
  busy: boolean;
  needsReviewCount: number;
  stampCount: number;
  onViewChange: (view: ViewName) => void;
  onSelectCollection: (collectionId: string) => void;
  onUploadClick: () => void;
  onToggleTheme: () => void;
  onSettingsClick: () => void;
  onCancelJob: () => void;
}

function elapsedLabel(startedAt: string | undefined, now: number): string | null {
  if (!startedAt) return null;
  const started = Date.parse(startedAt);
  if (Number.isNaN(started)) return null;
  const seconds = Math.max(0, Math.floor((now - started) / 1000));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function TopBar({
  collections,
  exp,
  view,
  job,
  jobRunning,
  theme,
  busy,
  needsReviewCount,
  stampCount,
  onViewChange,
  onSelectCollection,
  onUploadClick,
  onToggleTheme,
  onSettingsClick,
  onCancelJob,
}: Props) {
  const [panelOpen, setPanelOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  // Tick the elapsed-time display while a run is active and the panel is open.
  useEffect(() => {
    if (!jobRunning || !panelOpen) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [jobRunning, panelOpen]);

  const runLabel = (() => {
    if (jobRunning && job) return job.message || "Analyzing…";
    if (job?.status === "failed") return `Run failed: ${job.error ?? "unknown error"}`;
    if (job?.status === "cancelled") return job.message || "Run stopped";
    if (job?.status === "completed") return job.message || "Run complete";
    const latest = exp?.evaluation_runs[0];
    if (!latest) return null;
    const cost = (latest.settings.cost_actual as Record<string, unknown> | undefined)
      ?.total_cost_usd;
    const costLabel = typeof cost === "number" ? ` · $${cost.toFixed(2)}` : "";
    return `Last run: ${latest.status}${costLabel}`;
  })();

  const pending = job && job.total > 0 ? Math.max(0, job.total - job.current) : 0;
  const done = job && job.total > 0 ? Math.max(0, job.current - (jobRunning ? 1 : 0)) : 0;
  const estimatedCost = job?.cost_estimate?.estimated_total_cost_usd ?? null;
  const elapsed = elapsedLabel(job?.started_at, now);

  return (
    <header className="topbar">
      <div className="brand">
        Phila<span>lens</span>
      </div>
      <select
        value={exp?.collection.collection_id ?? ""}
        onChange={(event) => onSelectCollection(event.target.value)}
        disabled={collections.length === 0}
        aria-label="Collection"
      >
        {collections.length === 0 && <option value="">No collections yet</option>}
        {collections.map((collection) => (
          <option key={collection.collection_id} value={collection.collection_id}>
            {(collection.title ?? collection.collection_id) +
              ` — ${collection.page_count}p · ${collection.stamp_count} stamps`}
          </option>
        ))}
      </select>
      <button
        className="btn"
        onClick={onUploadClick}
        disabled={busy}
        title="Adds pages to the current collection — files already uploaded (same filename) are skipped automatically"
      >
        Upload pages
      </button>
      {exp && (
        <nav className="tabs">
          <button
            className={`tab ${view === "overview" ? "on" : ""}`}
            onClick={() => onViewChange("overview")}
          >
            Overview
          </button>
          <button
            className={`tab ${view === "curate" ? "on" : ""}`}
            onClick={() => onViewChange("curate")}
          >
            Curate{needsReviewCount > 0 && <span className="n">{needsReviewCount}</span>}
          </button>
          <button
            className={`tab ${view === "stamps" ? "on" : ""}`}
            onClick={() => onViewChange("stamps")}
          >
            Stamps<span className="n">{stampCount}</span>
          </button>
        </nav>
      )}
      <span className="grow" />
      {runLabel && (
        <div style={{ position: "relative" }}>
          <button
            className="runpill"
            title={`${runLabel} — click for details`}
            onClick={() => setPanelOpen((open) => !open)}
          >
            <span
              className={`dot ${jobRunning ? "busy" : job?.status === "failed" ? "failed" : ""}`}
            />
            {jobRunning && job && job.total > 0 && (
              <span className="bar">
                <div style={{ width: `${(job.current / job.total) * 100}%` }} />
              </span>
            )}
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {jobRunning && job && job.total > 0
                ? `${job.current}/${job.total} · ${runLabel}`
                : runLabel}
            </span>
          </button>
          {panelOpen && job && (
            <div className="runpanel">
              <div className="runpanel-head">
                <b>
                  {job.status === "running" || job.status === "queued"
                    ? "Evaluation in progress"
                    : job.status === "cancelled"
                      ? "Run stopped"
                      : job.status === "failed"
                        ? "Run failed"
                        : "Run complete"}
                </b>
                <button className="close" onClick={() => setPanelOpen(false)}>
                  ×
                </button>
              </div>
              {job.total > 0 && (
                <>
                  <div className="runpanel-bar">
                    <div style={{ width: `${(job.current / job.total) * 100}%` }} />
                  </div>
                  <dl className="kv">
                    <dt>Analyzed</dt>
                    <dd>
                      {done} of {job.total} stamps
                    </dd>
                    <dt>Pending</dt>
                    <dd>{pending}</dd>
                    {elapsed && jobRunning && (
                      <>
                        <dt>Elapsed</dt>
                        <dd>{elapsed}</dd>
                      </>
                    )}
                    {estimatedCost !== null && (
                      <>
                        <dt>Est. cost</dt>
                        <dd>~${estimatedCost.toFixed(2)}</dd>
                      </>
                    )}
                  </dl>
                </>
              )}
              {jobRunning && job.current_crop_image_url && (
                <div className="runpanel-crop">
                  <img
                    src={job.current_crop_image_url}
                    alt={job.current_crop_label ?? "current stamp"}
                  />
                  <span>{job.current_crop_label}</span>
                </div>
              )}
              <p className="muted" style={{ margin: "8px 0" }}>
                {job.message}
              </p>
              {jobRunning && (
                <>
                  <button
                    className="btn danger"
                    onClick={onCancelJob}
                    disabled={Boolean(job.cancel_requested)}
                  >
                    {job.cancel_requested ? "Stopping…" : "⏹ Stop run"}
                  </button>
                  <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                    Every analyzed stamp is saved immediately; a stopped run can be
                    resumed from Overview without repeating finished stamps.
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      )}
      <button
        className="iconbtn"
        onClick={onToggleTheme}
        title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      >
        {theme === "dark" ? "☀️" : "🌙"}
      </button>
      <button className="iconbtn" onClick={onSettingsClick} title="Settings">
        ⚙
      </button>
    </header>
  );
}
