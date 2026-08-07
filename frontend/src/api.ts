import type {
  AppSettings,
  BBox,
  CollectionExport,
  CollectionInfo,
  CostEstimate,
  EvaluationJob,
  Stamp,
} from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // keep the status text
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function listCollections(): Promise<CollectionInfo[]> {
  return request("/api/collections");
}

export function getCollection(collectionId: string): Promise<CollectionExport> {
  return request(`/api/collections/${collectionId}`);
}

export function uploadCollection(files: FileList | File[]): Promise<CollectionExport> {
  const form = new FormData();
  for (const file of Array.from(files)) form.append("files", file);
  return request("/api/collections", { method: "POST", body: form });
}

export function deleteCollection(collectionId: string): Promise<{ deleted: string }> {
  return request(`/api/collections/${collectionId}`, { method: "DELETE" });
}

export function updateCrop(
  cropId: string,
  bbox: BBox,
  rotationDegrees?: number,
): Promise<{ crop: Stamp }> {
  return request(
    `/api/crops/${cropId}`,
    jsonInit("PATCH", {
      bbox_xywh: bbox,
      ...(rotationDegrees === undefined ? {} : { rotation_degrees: rotationDegrees }),
    }),
  );
}

export function deleteCrop(cropId: string): Promise<CollectionExport> {
  return request(`/api/crops/${cropId}`, { method: "DELETE" });
}

export function deleteCrops(cropIds: string[]): Promise<CollectionExport> {
  return request("/api/crops/delete", jsonInit("POST", { crop_ids: cropIds }));
}

export function markCropsReady(cropIds: string[]): Promise<CollectionExport> {
  return request("/api/crops/mark-ready", jsonInit("POST", { crop_ids: cropIds }));
}

export function createManualCrop(
  pageId: string,
  bbox: BBox,
  rotationDegrees = 0,
): Promise<CollectionExport> {
  return request(
    `/api/pages/${pageId}/crops`,
    jsonInit("POST", { bbox_xywh: bbox, rotation_degrees: rotationDegrees }),
  );
}

export function redetectPage(pageId: string): Promise<CollectionExport> {
  return request(`/api/pages/${pageId}/redetect`, { method: "POST" });
}

export function deletePage(pageId: string): Promise<CollectionExport> {
  return request(`/api/pages/${pageId}`, { method: "DELETE" });
}

export function estimateEvaluationCost(
  collectionId: string,
  cropIds?: string[],
): Promise<CostEstimate> {
  return request(
    `/api/collections/${collectionId}/evaluation-cost-estimate`,
    jsonInit("POST", { crop_ids: cropIds ?? [] }),
  );
}

export function startEvaluation(
  collectionId: string,
  cropIds?: string[],
): Promise<EvaluationJob> {
  return request(
    `/api/collections/${collectionId}/evaluate/start`,
    jsonInit("POST", { crop_ids: cropIds ?? [] }),
  );
}

export function getEvaluationJob(jobId: string): Promise<EvaluationJob> {
  return request(`/api/evaluation-jobs/${jobId}`);
}

export function resumeEvaluationRun(runId: string): Promise<EvaluationJob> {
  return request(`/api/evaluation-runs/${runId}/resume`, { method: "POST" });
}

export function gatherCropEvidence(cropId: string): Promise<CollectionExport> {
  return request(`/api/crops/${cropId}/evidence`, { method: "POST" });
}

export function startEvidenceGathering(
  collectionId: string,
  cropIds?: string[],
): Promise<EvaluationJob> {
  return request(
    `/api/collections/${collectionId}/evidence/start`,
    jsonInit("POST", { crop_ids: cropIds ?? [] }),
  );
}

export function getSettings(): Promise<AppSettings> {
  return request("/api/settings");
}

export function updateSettings(update: {
  vision_provider: string;
  openai_api_key?: string;
  openai_vision_model: string;
  openai_vision_detail: string;
  ebay_app_id?: string;
  ebay_cert_id?: string;
}): Promise<AppSettings> {
  return request("/api/settings", jsonInit("POST", update));
}
