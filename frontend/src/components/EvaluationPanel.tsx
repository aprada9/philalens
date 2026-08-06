import { useEffect, useState } from "react";
import { estimateEvaluationCost } from "../api";
import type { CollectionExport, CostEstimate, EvaluationJob } from "../types";
import { bucketLabel } from "./StampList";

interface Props {
  exp: CollectionExport;
  job: EvaluationJob | null;
  jobRunning: boolean;
  checkedCount: number;
  busy: boolean;
  onEvaluateAll: () => void;
  onEvaluateChecked: () => void;
  onResumeRun: (runId: string) => void;
  onBucketClick: (bucket: string) => void;
}

function formatUsd(value: unknown): string | null {
  if (typeof value !== "number") return null;
  return value < 0.01 && value > 0 ? `$${value.toFixed(4)}` : `$${value.toFixed(2)}`;
}

export default function EvaluationPanel({
  exp,
  job,
  jobRunning,
  checkedCount,
  busy,
  onEvaluateAll,
  onEvaluateChecked,
  onResumeRun,
  onBucketClick,
}: Props) {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const summary = exp.latest_evaluation_summary;
  const resumableRuns = exp.evaluation_runs.filter(
    (run) => run.status === "interrupted" || run.status === "failed",
  );
  const latestRun = exp.evaluation_runs[0] ?? null;
  const latestCost = latestRun
    ? formatUsd(
        (latestRun.settings.cost_actual as Record<string, unknown> | undefined)
          ?.total_cost_usd ??
          (latestRun.settings.cost_actual as Record<string, unknown> | undefined)
            ?.known_total_cost_usd,
      )
    : null;

  useEffect(() => {
    setEstimate(null);
  }, [exp.collection.collection_id, exp.collection.stamp_count]);

  const loadEstimate = async () => {
    try {
      setEstimate(await estimateEvaluationCost(exp.collection.collection_id));
    } catch {
      setEstimate(null);
    }
  };

  return (
    <div className="eval-panel">
      <span className="stat">
        <b>{exp.collection.stamp_count}</b> stamps ·{" "}
        <b>{exp.collection.needs_crop_review_count}</b> need crop review
      </span>
      {summary && (
        <span className="stat">
          evaluated <b>{summary.evaluated_stamp_count}</b> / remaining{" "}
          <b>{summary.unevaluated_stamp_count}</b>
        </span>
      )}
      {summary &&
        Object.entries(summary.value_bucket_counts).map(([bucket, count]) => (
          <button key={bucket} className="chip" onClick={() => onBucketClick(bucket)}>
            {bucketLabel(bucket)} {count}
          </button>
        ))}
      {latestCost && <span className="stat">last run cost {latestCost}</span>}

      {jobRunning && job ? (
        <div className="progress">
          {job.current_crop_image_url && (
            <img src={job.current_crop_image_url} alt="Current stamp" />
          )}
          <div className="bar">
            <div
              style={{
                width: job.total > 0 ? `${(job.current / job.total) * 100}%` : "10%",
              }}
            />
          </div>
          <span className="stat">
            {job.message} ({job.current}/{job.total})
          </span>
        </div>
      ) : (
        <>
          {job && job.status === "failed" && (
            <span className="stat" style={{ color: "var(--danger)" }}>
              Last job failed: {job.error}
            </span>
          )}
          {job && job.status === "completed" && <span className="stat">{job.message}</span>}
          <span className="spacer" style={{ flex: 1 }} />
          {resumableRuns.map((run) => (
            <button key={run.run_id} onClick={() => onResumeRun(run.run_id)} disabled={busy}>
              Resume {run.status} run
            </button>
          ))}
          <button onClick={() => void loadEstimate()} disabled={busy}>
            Estimate cost
          </button>
          {estimate && (
            <span className="stat">
              {estimate.provider === "none"
                ? "no vision provider configured"
                : `~${formatUsd(estimate.estimated_total_cost_usd) ?? "?"} for ${estimate.billable_api_call_count} calls`}
              {estimate.skipped_crop_review_count > 0 &&
                ` (${estimate.skipped_crop_review_count} skipped for crop review)`}
            </span>
          )}
          <button onClick={onEvaluateChecked} disabled={busy || checkedCount === 0}>
            Evaluate {checkedCount || ""} selected
          </button>
          <button className="primary" onClick={onEvaluateAll} disabled={busy}>
            Evaluate all
          </button>
        </>
      )}
    </div>
  );
}
