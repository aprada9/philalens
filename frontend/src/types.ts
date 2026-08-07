export type BBox = [number, number, number, number];

export interface CollectionInfo {
  collection_id: string;
  created_at: string;
  title: string | null;
  page_count: number;
  stamp_count: number;
  needs_crop_review_count: number;
}

export interface ObservationPayload {
  status: string;
  note?: string;
  observation_id?: string;
  visible_text?: string[];
  issuer_hint?: string | null;
  denomination_hint?: string | null;
  date_hint?: string | null;
  design_subject?: string | null;
  color_hints?: string[];
  cancellation_state?: string | null;
  condition_notes?: string[];
  image_quality_warnings?: string[];
  unobservable_factors?: string[];
  confidence?: number;
  model_metadata?: Record<string, unknown>;
}

export interface CandidatePayload {
  candidate_id: string;
  source_name: string;
  catalog_id: string | null;
  issuer: string | null;
  title: string | null;
  year: number | null;
  denomination: string | null;
  variant_notes: string[];
  match_score: number;
  rank: number;
  contradiction_warnings: string[];
}

export interface EvidencePayload {
  evidence_id: string;
  source_name: string;
  source_type: string;
  source_url: string | null;
  price_low: number | null;
  price_high: number | null;
  price: number | null;
  currency: string | null;
  evidence_tier: string | null;
  confidence: number;
  retrieved_at?: string | null;
  matched_fields?: Record<string, unknown>;
  license_notes?: string | null;
}

export interface ValuationPayload {
  status: string;
  note?: string;
  estimated_value_low: number | null;
  estimated_value_high: number | null;
  currency: string;
  confidence: number;
  value_bucket?: string;
  assumptions?: string[];
  uncertainty_warnings?: string[];
  recommended_next_action?: string | null;
}

export interface Stamp {
  crop_id: string;
  crop_index: number;
  bbox_xywh: BBox;
  rotation_degrees: number;
  crop_image_url: string;
  segmentation_confidence: number;
  review_state: string;
  warnings: string[];
  description: string;
  evaluation_run_id: string | null;
  observation: ObservationPayload;
  identification: { status: string; candidates: CandidatePayload[] };
  evidence: EvidencePayload[];
  valuation: ValuationPayload;
}

export interface Page {
  page_id: string;
  page_order: number;
  original_filename: string;
  image_format: string;
  width: number;
  height: number;
  quality_warnings: string[];
  notes: string[];
  normalized_image_url: string;
  stamps: Stamp[];
}

export interface EvaluationRun {
  run_id: string;
  collection_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  pipeline_version: string;
  vision_model: string | null;
  enabled_sources: string[];
  settings: Record<string, unknown>;
  warnings: string[];
  errors: string[];
}

export interface EvaluationSummary {
  run_id: string;
  status: string;
  evaluated_stamp_count: number;
  unevaluated_stamp_count: number;
  crop_review_remaining: number;
  attention_recommended_count: number;
  value_bucket_counts: Record<string, number>;
  warnings: string[];
  errors: string[];
}

export interface CollectionExport {
  collection: CollectionInfo;
  evaluation_runs: EvaluationRun[];
  latest_evaluation_run_id: string | null;
  latest_evaluation_summary: EvaluationSummary | null;
  pages: Page[];
}

export interface EvaluationJob {
  job_id: string;
  collection_id: string;
  job_type?: string;
  status: string;
  current: number;
  total: number;
  current_crop_id: string | null;
  current_crop_label: string | null;
  current_crop_image_url: string | null;
  message: string;
  error: string | null;
  cost_estimate: CostEstimate | null;
  cost_actual: Record<string, unknown> | null;
  run_id?: string;
  resumed_run_id?: string;
}

export interface CostEstimate {
  provider: string;
  model?: string | null;
  currency: string;
  estimate_available: boolean;
  crop_count: number;
  billable_api_call_count: number;
  skipped_crop_review_count: number;
  estimated_total_cost_usd: number | null;
  note?: string;
}

export interface AppSettings {
  vision_provider: string;
  openai_api_key_set: boolean;
  openai_vision_model: string;
  openai_vision_detail: string;
  market_sources: Record<string, string>;
}
