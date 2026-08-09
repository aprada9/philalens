import { useEffect, useMemo, useState } from "react";
import { BUCKETS, bucketMeta, stampBucket, stampHeadline, topCandidate } from "../buckets";
import type { CollectionExport, Stamp } from "../types";

export type StampSort = "attention" | "page" | "confidence" | "year_asc" | "year_desc";

interface Props {
  exp: CollectionExport;
  imageVersion: number;
  busy: boolean;
  bucketFilter: string | null;
  drawerCropId: string | null;
  onBucketFilter: (bucket: string | null) => void;
  onOpenStamp: (cropId: string | null) => void;
  onFixCrop: (cropId: string) => void;
  onReanalyze: (cropId: string) => void;
  onGatherEvidence: (cropId: string) => void;
  onDeleteCrop: (cropId: string) => void;
}

function pill(bucket: string | null) {
  const meta = bucketMeta(bucket);
  return (
    <span
      className="pill"
      style={{
        background: `color-mix(in srgb, var(${meta.cssVar}) 16%, transparent)`,
        color: `var(${meta.cssVar})`,
      }}
    >
      {meta.label}
    </span>
  );
}

export default function StampsView({
  exp,
  imageVersion,
  busy,
  bucketFilter,
  drawerCropId,
  onBucketFilter,
  onOpenStamp,
  onFixCrop,
  onReanalyze,
  onGatherEvidence,
  onDeleteCrop,
}: Props) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<StampSort>("attention");
  const [countryFilter, setCountryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "analyzed" | "not_analyzed">("all");
  const [yearRange, setYearRange] = useState<[number, number] | null>(null);

  const pageByCrop = useMemo(() => {
    const map = new Map<string, number>();
    for (const page of exp.pages) {
      for (const stamp of page.stamps) map.set(stamp.crop_id, page.page_order);
    }
    return map;
  }, [exp]);

  const stamps = useMemo(() => exp.pages.flatMap((page) => page.stamps), [exp]);

  const bucketCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const stamp of stamps) {
      const bucket = stampBucket(stamp);
      if (bucket) counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
    }
    return counts;
  }, [stamps]);

  const countries = useMemo(() => {
    const counts = new Map<string, number>();
    for (const stamp of stamps) {
      const issuer = topCandidate(stamp)?.issuer;
      if (issuer) counts.set(issuer, (counts.get(issuer) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [stamps]);

  // Bounds of the year slider: the span of AI-identified years in the
  // collection. Null when no stamp has a year yet.
  const yearBounds = useMemo<[number, number] | null>(() => {
    const years = stamps
      .map((stamp) => topCandidate(stamp)?.year)
      .filter((year): year is number => typeof year === "number");
    if (years.length === 0) return null;
    return [Math.min(...years), Math.max(...years)];
  }, [stamps]);

  // Keep the selected range valid when the collection (and its bounds) change.
  useEffect(() => {
    if (!yearBounds) {
      setYearRange(null);
      return;
    }
    setYearRange((range) => {
      if (!range) return null;
      const lo = Math.max(yearBounds[0], Math.min(range[0], yearBounds[1]));
      const hi = Math.min(yearBounds[1], Math.max(range[1], yearBounds[0]));
      return lo === yearBounds[0] && hi === yearBounds[1] ? null : [lo, hi];
    });
  }, [yearBounds]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const isAnalyzed = (stamp: Stamp) =>
      stamp.observation.status === "available" && (stamp.observation.confidence ?? 0) > 0;
    let list = stamps.filter((stamp) => {
      if (bucketFilter && stampBucket(stamp) !== bucketFilter) return false;
      if (statusFilter === "analyzed" && !isAnalyzed(stamp)) return false;
      if (statusFilter === "not_analyzed" && isAnalyzed(stamp)) return false;
      const candidate = topCandidate(stamp);
      if (countryFilter && candidate?.issuer !== countryFilter) return false;
      if (yearRange) {
        // A narrowed year range only matches stamps with an identified year.
        const year = candidate?.year ?? null;
        if (year === null || year < yearRange[0] || year > yearRange[1]) return false;
      }
      if (!term) return true;
      const haystack = [
        candidate?.issuer,
        candidate?.title,
        candidate?.denomination,
        stamp.description,
        stamp.observation.issuer_hint,
        ...(stamp.observation.visible_text ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(term);
    });
    list = [...list];
    if (sort === "attention") {
      list.sort(
        (a, b) =>
          bucketMeta(stampBucket(a)).rank - bucketMeta(stampBucket(b)).rank ||
          (topCandidate(b)?.match_score ?? 0) - (topCandidate(a)?.match_score ?? 0),
      );
    } else if (sort === "confidence") {
      list.sort(
        (a, b) => (topCandidate(b)?.match_score ?? 0) - (topCandidate(a)?.match_score ?? 0),
      );
    } else if (sort === "year_asc") {
      // Stamps without an identified year sort last.
      list.sort(
        (a, b) => (topCandidate(a)?.year ?? 9999) - (topCandidate(b)?.year ?? 9999),
      );
    } else if (sort === "year_desc") {
      list.sort(
        (a, b) => (topCandidate(b)?.year ?? -1) - (topCandidate(a)?.year ?? -1),
      );
    } else {
      list.sort(
        (a, b) =>
          (pageByCrop.get(a.crop_id) ?? 0) - (pageByCrop.get(b.crop_id) ?? 0) ||
          a.crop_index - b.crop_index,
      );
    }
    return list;
  }, [stamps, bucketFilter, query, sort, pageByCrop, countryFilter, statusFilter, yearRange]);

  const drawerStamp = stamps.find((stamp) => stamp.crop_id === drawerCropId) ?? null;

  const filterChips: Array<[string, number]> = Object.keys(BUCKETS)
    .filter((bucket) => bucketCounts.has(bucket))
    .map((bucket) => [bucket, bucketCounts.get(bucket) ?? 0]);

  return (
    <div className="view-inner">
      <div className="filters">
        <input
          className="search"
          placeholder="Search country, series, text…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button
          className={`fchip ${bucketFilter === null ? "on" : ""}`}
          onClick={() => onBucketFilter(null)}
        >
          All <b>{stamps.length}</b>
        </button>
        {filterChips.map(([bucket, count]) => (
          <button
            key={bucket}
            className={`fchip ${bucketFilter === bucket ? "on" : ""}`}
            onClick={() => onBucketFilter(bucketFilter === bucket ? null : bucket)}
          >
            <i style={{ background: `var(${bucketMeta(bucket).cssVar})` }} />
            {bucketMeta(bucket).label} {count}
          </button>
        ))}
        <span className="grow" />
        <select
          value={statusFilter}
          onChange={(event) =>
            setStatusFilter(event.target.value as "all" | "analyzed" | "not_analyzed")
          }
          title="Filter by AI analysis status"
        >
          <option value="all">All statuses</option>
          <option value="analyzed">Analyzed</option>
          <option value="not_analyzed">Not analyzed yet</option>
        </select>
        <select
          value={countryFilter}
          onChange={(event) => setCountryFilter(event.target.value)}
          title="Filter by AI-identified country (unverified prior)"
        >
          <option value="">All countries</option>
          {countries.map(([name, count]) => (
            <option key={name} value={name}>
              {name} ({count})
            </option>
          ))}
        </select>
        {yearBounds && yearBounds[0] < yearBounds[1] && (
          <YearRangeSlider
            bounds={yearBounds}
            range={yearRange}
            onChange={setYearRange}
          />
        )}
        <select value={sort} onChange={(event) => setSort(event.target.value as StampSort)}>
          <option value="attention">Sort: Attention first</option>
          <option value="page">Sort: Page order</option>
          <option value="confidence">Sort: Identity confidence</option>
          <option value="year_asc">Sort: Year, oldest first</option>
          <option value="year_desc">Sort: Year, newest first</option>
        </select>
      </div>

      {visible.length === 0 ? (
        <p className="muted" style={{ textAlign: "center", padding: 40 }}>
          No stamps match the current filter.
        </p>
      ) : (
        <div className="grid">
          {visible.map((stamp) => {
            const headline = stampHeadline(stamp);
            const candidate = topCandidate(stamp);
            return (
              <button
                key={stamp.crop_id}
                className="card"
                onClick={() => onOpenStamp(stamp.crop_id)}
              >
                <div className="card-img">
                  <img
                    src={`${stamp.crop_image_url}?v=${imageVersion}`}
                    alt={headline.title}
                    loading="lazy"
                  />
                </div>
                <div className="card-body">
                  <div className="card-country">
                    {headline.country ?? "—"}
                    {candidate?.year ? ` · ${candidate.year}` : ""}
                  </div>
                  <div className="card-title" title={headline.title}>
                    {headline.title}
                  </div>
                  <div className="card-meta">
                    <span className="denom">
                      {candidate?.denomination ?? `p${pageByCrop.get(stamp.crop_id)} · #${stamp.crop_index}`}
                    </span>
                    {pill(stampBucket(stamp))}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {drawerStamp && (
        <StampDrawer
          stamp={drawerStamp}
          pageOrder={pageByCrop.get(drawerStamp.crop_id) ?? 0}
          imageVersion={imageVersion}
          busy={busy}
          onClose={() => onOpenStamp(null)}
          onFixCrop={() => onFixCrop(drawerStamp.crop_id)}
          onReanalyze={() => onReanalyze(drawerStamp.crop_id)}
          onGatherEvidence={() => onGatherEvidence(drawerStamp.crop_id)}
          onDelete={() => onDeleteCrop(drawerStamp.crop_id)}
        />
      )}
    </div>
  );
}

function YearRangeSlider({
  bounds,
  range,
  onChange,
}: {
  bounds: [number, number];
  range: [number, number] | null;
  onChange: (range: [number, number] | null) => void;
}) {
  const [lo, hi] = range ?? bounds;
  const isFiltering = range !== null;

  const commit = (nextLo: number, nextHi: number) => {
    if (nextLo <= bounds[0] && nextHi >= bounds[1]) {
      onChange(null); // full span = no filter (stamps without a year included)
    } else {
      onChange([nextLo, nextHi]);
    }
  };

  const percent = (year: number) =>
    ((year - bounds[0]) / (bounds[1] - bounds[0])) * 100;

  return (
    <div
      className="year-slider"
      title="Filter by identified year — a narrowed range only matches stamps with a year"
    >
      <span className={isFiltering ? "on" : ""}>{lo}</span>
      <div className="ys-track">
        <div
          className="ys-fill"
          style={{ left: `${percent(lo)}%`, width: `${percent(hi) - percent(lo)}%` }}
        />
        <input
          type="range"
          min={bounds[0]}
          max={bounds[1]}
          value={lo}
          onChange={(event) => commit(Math.min(Number(event.target.value), hi), hi)}
          aria-label="Year from"
        />
        <input
          type="range"
          min={bounds[0]}
          max={bounds[1]}
          value={hi}
          onChange={(event) => commit(lo, Math.max(Number(event.target.value), lo))}
          aria-label="Year to"
        />
      </div>
      <span className={isFiltering ? "on" : ""}>{hi}</span>
      {isFiltering && (
        <button className="ys-reset" onClick={() => onChange(null)} title="Reset year filter">
          ×
        </button>
      )}
    </div>
  );
}

function StampDrawer({
  stamp,
  pageOrder,
  imageVersion,
  busy,
  onClose,
  onFixCrop,
  onReanalyze,
  onGatherEvidence,
  onDelete,
}: {
  stamp: Stamp;
  pageOrder: number;
  imageVersion: number;
  busy: boolean;
  onClose: () => void;
  onFixCrop: () => void;
  onReanalyze: () => void;
  onGatherEvidence: () => void;
  onDelete: () => void;
}) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const headline = stampHeadline(stamp);
  const candidate = topCandidate(stamp);
  const bucket = stampBucket(stamp);
  const meta = bucketMeta(bucket);
  const observation = stamp.observation;
  const valuation = stamp.valuation;
  const rationale = (valuation.assumptions ?? []).find((item) =>
    item.startsWith("Model rationale:"),
  );
  const noRangeReason = (valuation.assumptions ?? [])
    .find((item) => item.startsWith("No value range:"))
    ?.replace("No value range:", "")
    .trim();
  const askingContext = (valuation.assumptions ?? [])
    .find((item) => item.startsWith("Asking-price context:"))
    ?.replace("Asking-price context:", "")
    .trim();
  const hasRange =
    valuation.estimated_value_low !== null && valuation.estimated_value_high !== null;
  const evidenceChecked = hasRange || noRangeReason !== undefined || stamp.evidence.length > 0;
  const catalogHints = (candidate?.variant_notes ?? []).filter((note) =>
    note.startsWith("catalog_hint"),
  );
  const identityConfidence = candidate?.match_score ?? 0;

  return (
    <>
      <div className="drawer-bg" onClick={onClose} />
      <div className="drawer">
        <button className="close" onClick={onClose}>
          ×
        </button>
        <div className="d-img">
          <img src={`${stamp.crop_image_url}?v=${imageVersion}`} alt={headline.title} />
        </div>
        <div className="d-country">
          {headline.country ?? "Unidentified"}
          {candidate?.year ? ` · ${candidate.year}` : ""}
        </div>
        <div className="d-title">{headline.title}</div>
        <div className="d-sub">
          {candidate?.denomination ? `${candidate.denomination} · ` : ""}Page {pageOrder} · stamp #
          {stamp.crop_index}
        </div>

        {bucket && (
          <div
            className="bucket-why"
            style={{
              background: `color-mix(in srgb, var(${meta.cssVar}) 9%, transparent)`,
              borderColor: `color-mix(in srgb, var(${meta.cssVar}) 30%, transparent)`,
            }}
          >
            <b style={{ color: `var(${meta.cssVar})` }}>{meta.label}</b>
            {rationale
              ? ` — ${rationale.replace("Model rationale:", "").trim()}`
              : valuation.recommended_next_action
                ? ` — next: ${valuation.recommended_next_action}`
                : ""}
          </div>
        )}

        {candidate && (
          <div className="conf">
            <div className="cl">
              <span>Identity confidence (AI prior)</span>
              <span>{identityConfidence.toFixed(2)}</span>
            </div>
            <div className="cb">
              <div style={{ width: `${identityConfidence * 100}%` }} />
            </div>
          </div>
        )}

        {candidate && (
          <div className="ai-note">
            ⓘ AI identification from the photo only — not verified against any catalog or market
            source.
          </div>
        )}

        {observation.status === "available" && (
          <div className="d-section">
            <h4>Observations</h4>
            <dl className="kv">
              <dt>Cancellation</dt>
              <dd>{(observation.cancellation_state ?? "unknown").replaceAll("_", " ")}</dd>
              {(observation.visible_text?.length ?? 0) > 0 && (
                <>
                  <dt>Visible text</dt>
                  <dd>{(observation.visible_text ?? []).join(" · ")}</dd>
                </>
              )}
              {(observation.condition_notes?.length ?? 0) > 0 && (
                <>
                  <dt>Condition</dt>
                  <dd>{(observation.condition_notes ?? []).slice(0, 4).join(" · ")}</dd>
                </>
              )}
              {(observation.unobservable_factors?.length ?? 0) > 0 && (
                <>
                  <dt>Not visible</dt>
                  <dd>{(observation.unobservable_factors ?? []).slice(0, 6).join(" · ")}</dd>
                </>
              )}
            </dl>
          </div>
        )}

        {catalogHints.length > 0 && (
          <div className="d-section">
            <h4>Catalog hint (unverified)</h4>
            {catalogHints.map((hint) => (
              <div key={hint} style={{ fontSize: 13 }}>
                {hint.replace("catalog_hint (unverified):", "").trim()}
              </div>
            ))}
          </div>
        )}

        {evidenceChecked && (
          <div className="d-section">
            <h4>Market value</h4>
            {hasRange ? (
              <div style={{ fontSize: 13 }}>
                Evidence-backed range: <b>
                  {valuation.estimated_value_low}–{valuation.estimated_value_high}{" "}
                  {valuation.currency}
                </b>{" "}
                — from realized sales; not a formal appraisal.
              </div>
            ) : (
              <div style={{ fontSize: 13 }} className="muted">
                No value range{noRangeReason ? ` — ${noRangeReason}` : "."}
              </div>
            )}
            {askingContext && (
              <div style={{ fontSize: 13, marginTop: 6 }} className="muted">
                Asking prices (weak evidence): {askingContext}
              </div>
            )}
            {candidate && (
              <div style={{ fontSize: 13, marginTop: 6 }}>
                <a
                  href={`https://www.ebay.com/sch/i.html?_nkw=${encodeURIComponent(
                    [candidate.issuer, candidate.title, candidate.year, candidate.denomination, "stamp"]
                      .filter(Boolean)
                      .join(" "),
                  )}&LH_Sold=1&LH_Complete=1`}
                  target="_blank"
                  rel="noreferrer"
                >
                  → Check realized prices: eBay sold listings for this identity
                </a>
                <span className="muted"> (sold prices are the evidence that can set a range)</span>
              </div>
            )}
          </div>
        )}

        {stamp.evidence.length > 0 && (
          <div className="d-section">
            <h4>Evidence</h4>
            {stamp.evidence.map((item) => (
              <dl className="kv" key={item.evidence_id}>
                <dt>{item.source_name}</dt>
                <dd>
                  {item.evidence_tier ?? item.source_type}
                  {typeof item.matched_fields?.listing_title === "string" &&
                    ` · ${item.matched_fields.listing_title}`}
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

        <div className="d-actions">
          <button className="btn" onClick={onFixCrop} disabled={busy}>
            ⤢ Fix crop
          </button>
          <button className="btn" onClick={onReanalyze} disabled={busy}>
            ↻ Re-analyze
          </button>
          <button
            className="btn"
            onClick={() => {
              if (
                stamp.evidence.length > 0 &&
                !window.confirm(
                  "Evidence was already gathered for this stamp. Fetch again and replace it?",
                )
              ) {
                return;
              }
              onGatherEvidence();
            }}
            disabled={busy}
            title="Search Wikidata and eBay (when configured) for this stamp's identity"
          >
            🔍 Gather evidence
          </button>
          <button className="btn danger" onClick={onDelete} disabled={busy}>
            Delete crop
          </button>
        </div>
      </div>
    </>
  );
}
