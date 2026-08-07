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
}: Props) {
  const runLabel = (() => {
    if (jobRunning && job) return job.message || "Analyzing…";
    if (job?.status === "failed") return `Run failed: ${job.error ?? "unknown error"}`;
    if (job?.status === "completed") return job.message || "Run complete";
    const latest = exp?.evaluation_runs[0];
    if (!latest) return null;
    const cost = (latest.settings.cost_actual as Record<string, unknown> | undefined)
      ?.total_cost_usd;
    const costLabel = typeof cost === "number" ? ` · $${cost.toFixed(2)}` : "";
    return `Last run: ${latest.status}${costLabel}`;
  })();

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
      <button className="btn" onClick={onUploadClick} disabled={busy}>
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
        <div className="runpill" title={runLabel}>
          <span
            className={`dot ${jobRunning ? "busy" : job?.status === "failed" ? "failed" : ""}`}
          />
          {jobRunning && job && job.total > 0 && (
            <span className="bar">
              <div style={{ width: `${(job.current / job.total) * 100}%` }} />
            </span>
          )}
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {runLabel}
          </span>
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
