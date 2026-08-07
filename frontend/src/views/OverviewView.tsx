import { useMemo } from "react";
import { bucketMeta, stampBucket, topCandidate } from "../buckets";
import type { CollectionExport, Stamp } from "../types";

interface Props {
  exp: CollectionExport;
  busy: boolean;
  imageVersion: number;
  onStartQueue: () => void;
  onEvaluateAll: () => void;
  onResumeRun: (runId: string) => void;
  onOpenBucket: (bucket: string | null) => void;
  onOpenStamp: (cropId: string) => void;
  onDeleteCollection: () => void;
}

/* Fixed segment order = the color-validated adjacency order for the bar. */
const BAR_ORDER = [
  "needs_better_image",
  "investigate",
  "likely_common",
  "possibly_interesting",
  "needs_expert_check",
  "needs_source_matching",
  "not_enough_evidence",
];

export default function OverviewView({
  exp,
  busy,
  imageVersion,
  onStartQueue,
  onEvaluateAll,
  onResumeRun,
  onOpenBucket,
  onOpenStamp,
  onDeleteCollection,
}: Props) {
  const stamps = useMemo(() => exp.pages.flatMap((page) => page.stamps), [exp]);
  const needsReview = exp.collection.needs_crop_review_count;

  const bucketCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const stamp of stamps) {
      const bucket = stampBucket(stamp);
      if (bucket) counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
    }
    return counts;
  }, [stamps]);

  const analyzedCount = useMemo(
    () =>
      stamps.filter(
        (stamp) =>
          stamp.observation.status === "available" && (stamp.observation.confidence ?? 0) > 0,
      ).length,
    [stamps],
  );

  const attentionStamps = useMemo(
    () => stamps.filter((stamp) => bucketMeta(stampBucket(stamp)).attention),
    [stamps],
  );

  const notAnalyzed = exp.collection.stamp_count - analyzedCount;

  const countries = useMemo(() => {
    const counts = new Map<string, number>();
    for (const stamp of stamps) {
      const candidate = topCandidate(stamp);
      if (candidate?.issuer) counts.set(candidate.issuer, (counts.get(candidate.issuer) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [stamps]);
  const maxCountry = countries[0]?.[1] ?? 1;

  const latestRun = exp.evaluation_runs[0] ?? null;
  const lastCost = (() => {
    const cost = (latestRun?.settings.cost_actual as Record<string, unknown> | undefined)
      ?.total_cost_usd;
    return typeof cost === "number" ? cost : null;
  })();
  const resumableRun = exp.evaluation_runs.find(
    (run) => run.status === "interrupted" || run.status === "failed",
  );

  const nextStep = (() => {
    if (resumableRun) {
      return {
        icon: "▶",
        title: `An evaluation run was ${resumableRun.status}`,
        detail: "Resume it to finish the remaining stamps without repeating completed ones.",
        action: "Resume run",
        onClick: () => onResumeRun(resumableRun.run_id),
      };
    }
    if (needsReview > 0) {
      return {
        icon: "✂️",
        title: `${needsReview} stamps are waiting on crop review`,
        detail:
          "The AI skips crops whose boxes look wrong. The review queue walks you through them one by one — keyboard-first.",
        action: "Start review queue →",
        onClick: onStartQueue,
      };
    }
    if (notAnalyzed > 0) {
      return {
        icon: "🔍",
        title: `${notAnalyzed} stamps haven't been analyzed yet`,
        detail: "Crops look ready. Run the AI identification pass over the collection.",
        action: "Evaluate all",
        onClick: onEvaluateAll,
      };
    }
    if (attentionStamps.length > 0) {
      return {
        icon: "⭐",
        title: `${attentionStamps.length} stamps are flagged for attention`,
        detail: "Review the flagged stamps and gather market evidence for the promising ones.",
        action: "See flagged stamps",
        onClick: () => onOpenBucket("investigate"),
      };
    }
    return {
      icon: "✓",
      title: "Everything is analyzed",
      detail: "No stamps are flagged. Export the inventory or upload more pages.",
      action: null as string | null,
      onClick: () => {},
    };
  })();

  const barTotal = BAR_ORDER.reduce((sum, bucket) => sum + (bucketCounts.get(bucket) ?? 0), 0);

  return (
    <div className="view-inner">
      <div className="stat-row">
        <div className="stat">
          <div className="v">
            {exp.collection.stamp_count} <small>stamps</small>
          </div>
          <div className="l">across {exp.collection.page_count} pages</div>
        </div>
        <div className="stat">
          <div className="v">
            {analyzedCount} <small>analyzed</small>
          </div>
          <div className="l">by AI vision (Tier 1)</div>
        </div>
        <div className="stat">
          <div className="v">
            {needsReview} <small>waiting</small>
          </div>
          <div className="l">need a crop fix before analysis</div>
        </div>
        <div className="stat">
          <div className="v">{lastCost !== null ? `$${lastCost.toFixed(2)}` : "—"}</div>
          <div className="l">
            {lastCost !== null && analyzedCount > 0
              ? `last run · ~$${((lastCost / analyzedCount) * 1000).toFixed(2)} per 1k stamps`
              : "no run cost recorded yet"}
          </div>
        </div>
      </div>

      <div className="next-card">
        <div className="icon">{nextStep.icon}</div>
        <div className="grow">
          <div className="t">{nextStep.title}</div>
          <div className="d">{nextStep.detail}</div>
        </div>
        {nextStep.action && (
          <button className="btn primary" onClick={nextStep.onClick} disabled={busy}>
            {nextStep.action}
          </button>
        )}
      </div>

      <div className="two-col">
        <div className="panel">
          <h3>Value triage</h3>
          {barTotal > 0 ? (
            <>
              <div className="bucketbar">
                {BAR_ORDER.filter((bucket) => (bucketCounts.get(bucket) ?? 0) > 0).map(
                  (bucket) => (
                    <button
                      key={bucket}
                      title={`${bucketMeta(bucket).label}: ${bucketCounts.get(bucket)}`}
                      style={{
                        background: `var(${bucketMeta(bucket).cssVar})`,
                        width: `${((bucketCounts.get(bucket) ?? 0) / barTotal) * 100}%`,
                      }}
                      onClick={() => onOpenBucket(bucket)}
                    />
                  ),
                )}
              </div>
              <div className="legend">
                {BAR_ORDER.filter((bucket) => bucketCounts.has(bucket)).map((bucket) => (
                  <button key={bucket} onClick={() => onOpenBucket(bucket)}>
                    <i style={{ background: `var(${bucketMeta(bucket).cssVar})` }} />
                    {bucketMeta(bucket).label} <b>{bucketCounts.get(bucket)}</b>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p className="muted">No evaluation run yet.</p>
          )}
          {attentionStamps.length > 0 ? (
            <div className="attention-grid">
              {attentionStamps.slice(0, 8).map((stamp: Stamp) => (
                <button key={stamp.crop_id} className="card" onClick={() => onOpenStamp(stamp.crop_id)}>
                  <div className="card-img" style={{ height: 90 }}>
                    <img src={`${stamp.crop_image_url}?v=${imageVersion}`} alt="" loading="lazy" />
                  </div>
                  <div className="card-body">
                    <div className="card-title">{stamp.description}</div>
                    <span
                      className="pill"
                      style={{
                        background: `color-mix(in srgb, var(${bucketMeta(stampBucket(stamp)).cssVar}) 16%, transparent)`,
                        color: `var(${bucketMeta(stampBucket(stamp)).cssVar})`,
                      }}
                    >
                      {bucketMeta(stampBucket(stamp)).label}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="attention-empty">
              Nothing flagged as valuable yet — flagged stamps will appear here the moment a run
              finds one.
            </div>
          )}
        </div>

        <div>
          <div className="panel" style={{ marginBottom: 14 }}>
            <h3>Collection at a glance</h3>
            {countries.length === 0 ? (
              <p className="muted">Country breakdown appears after the first AI run.</p>
            ) : (
              <>
                {countries.slice(0, 8).map(([name, count]) => (
                  <div className="country-row" key={name}>
                    <span
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {name}
                    </span>
                    <div className="country-bar">
                      <div style={{ width: `${(count / maxCountry) * 100}%` }} />
                    </div>
                    <b>{count}</b>
                  </div>
                ))}
                <div className="muted" style={{ marginTop: 10 }}>
                  From AI identifications · unverified priors
                </div>
              </>
            )}
          </div>
          <div className="panel">
            <h3>Collection</h3>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <a href={`/api/collections/${exp.collection.collection_id}/export.json`}>
                <button className="btn">Export JSON</button>
              </a>
              <a href={`/api/collections/${exp.collection.collection_id}/export.csv`}>
                <button className="btn">Export CSV</button>
              </a>
              <button className="btn danger" onClick={onDeleteCollection} disabled={busy}>
                Delete collection
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
