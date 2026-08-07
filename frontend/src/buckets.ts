import type { Stamp } from "./types";

export interface BucketMeta {
  label: string;
  cssVar: string;
  attention: boolean;
  /* lower = shown first when sorting by attention */
  rank: number;
}

export const BUCKETS: Record<string, BucketMeta> = {
  investigate: { label: "Investigate", cssVar: "--bucket-investigate", attention: true, rank: 0 },
  possibly_interesting: {
    label: "Interesting",
    cssVar: "--bucket-interesting",
    attention: true,
    rank: 1,
  },
  needs_expert_check: {
    label: "Expert check",
    cssVar: "--bucket-interesting",
    attention: true,
    rank: 2,
  },
  needs_source_matching: {
    label: "Needs sources",
    cssVar: "--bucket-none",
    attention: false,
    rank: 3,
  },
  not_enough_evidence: {
    label: "No evidence",
    cssVar: "--bucket-none",
    attention: false,
    rank: 4,
  },
  likely_common: { label: "Common", cssVar: "--bucket-common", attention: false, rank: 5 },
  identified_low_value: {
    label: "Low value",
    cssVar: "--bucket-common",
    attention: false,
    rank: 6,
  },
  needs_better_image: {
    label: "Fix crop",
    cssVar: "--bucket-fixcrop",
    attention: false,
    rank: 7,
  },
};

export function bucketMeta(bucket: string | undefined | null): BucketMeta {
  if (bucket && bucket in BUCKETS) return BUCKETS[bucket];
  return {
    label: (bucket ?? "unknown").replaceAll("_", " "),
    cssVar: "--bucket-none",
    attention: false,
    rank: 9,
  };
}

export function stampBucket(stamp: Stamp): string | null {
  return stamp.valuation.value_bucket ?? null;
}

export function topCandidate(stamp: Stamp) {
  const candidates = stamp.identification.candidates;
  if (candidates.length === 0) return null;
  return candidates.reduce((best, candidate) =>
    candidate.rank < best.rank ? candidate : best,
  );
}

export function stampHeadline(stamp: Stamp): { country: string | null; title: string } {
  const candidate = topCandidate(stamp);
  if (candidate) {
    return {
      country: candidate.issuer,
      title: candidate.title ?? candidate.issuer ?? "Unidentified",
    };
  }
  if (stamp.observation.status === "available" && stamp.observation.issuer_hint) {
    return { country: stamp.observation.issuer_hint, title: stamp.description };
  }
  return { country: null, title: stamp.description || "Not analyzed yet" };
}
