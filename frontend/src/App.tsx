import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import SettingsDialog from "./components/SettingsDialog";
import TopBar, { type ViewName } from "./components/TopBar";
import CurateView from "./views/CurateView";
import OverviewView from "./views/OverviewView";
import StampsView from "./views/StampsView";
import type { BBox, CollectionExport, CollectionInfo, EvaluationJob, Page } from "./types";

function initialTheme(): "light" | "dark" {
  const saved = localStorage.getItem("philalens-theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [exp, setExp] = useState<CollectionExport | null>(null);
  const [view, setView] = useState<ViewName>("overview");
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [selectedCropId, setSelectedCropId] = useState<string | null>(null);
  const [drawerCropId, setDrawerCropId] = useState<string | null>(null);
  const [bucketFilter, setBucketFilter] = useState<string | null>(null);
  const [drawMode, setDrawMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [imageVersion, setImageVersion] = useState(1);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("philalens-theme", theme);
  }, [theme]);

  const reportError = useCallback((exc: unknown) => {
    setError(String(exc instanceof Error ? exc.message : exc));
  }, []);

  const applyExport = useCallback((next: CollectionExport, bumpImages = false) => {
    setExp(next);
    const cropIds = new Set(next.pages.flatMap((page) => page.stamps.map((s) => s.crop_id)));
    setSelectedCropId((current) => (current && cropIds.has(current) ? current : null));
    setDrawerCropId((current) => (current && cropIds.has(current) ? current : null));
    setSelectedPageId((current) =>
      current && next.pages.some((page) => page.page_id === current)
        ? current
        : (next.pages[0]?.page_id ?? null),
    );
    if (bumpImages) setImageVersion((version) => version + 1);
  }, []);

  const refreshCollections = useCallback(async () => {
    try {
      setCollections(await api.listCollections());
    } catch (exc) {
      reportError(exc);
    }
  }, [reportError]);

  const loadCollection = useCallback(
    async (collectionId: string) => {
      setBusy(true);
      setError(null);
      try {
        applyExport(await api.getCollection(collectionId));
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyExport, reportError],
  );


  // Local page-state update for hot review-queue actions: the server
  // confirms the change with a light response and the client mirrors it,
  // instead of refetching the multi-megabyte collection export per action.
  const applyLocalPages = useCallback((updatePages: (pages: Page[]) => Page[]) => {
    setExp((prev) => {
      if (!prev) return prev;
      const pages = updatePages(prev.pages);
      const stamps = pages.flatMap((page) => page.stamps);
      return {
        ...prev,
        pages,
        collection: {
          ...prev.collection,
          stamp_count: stamps.length,
          needs_crop_review_count: stamps.filter(
            (stamp) => stamp.review_state === "needs_crop_review",
          ).length,
        },
      };
    });
  }, []);

  const handleMarkReady = useCallback(
    async (cropIds: string[]) => {
      setBusy(true);
      setError(null);
      try {
        await api.markCropsReady(cropIds);
        const ids = new Set(cropIds);
        applyLocalPages((pages) =>
          pages.map((page) => ({
            ...page,
            stamps: page.stamps.map((stamp) =>
              ids.has(stamp.crop_id)
                ? { ...stamp, review_state: "unreviewed", warnings: [] }
                : stamp,
            ),
          })),
        );
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyLocalPages, reportError],
  );

  const handleDeleteCrop = useCallback(
    async (cropId: string) => {
      setBusy(true);
      setError(null);
      try {
        await api.deleteCrop(cropId);
        setDrawerCropId((current) => (current === cropId ? null : current));
        setSelectedCropId((current) => (current === cropId ? null : current));
        applyLocalPages((pages) =>
          pages.map((page) => ({
            ...page,
            stamps: page.stamps.filter((stamp) => stamp.crop_id !== cropId),
          })),
        );
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyLocalPages, reportError],
  );

  // One busy cycle for a grid-triage page apply: delete the marked crops,
  // accept the rest, mirror both locally.
  const handleGridApply = useCallback(
    async (deleteIds: string[], keepIds: string[]) => {
      setBusy(true);
      setError(null);
      try {
        if (deleteIds.length > 0) await api.deleteCrops(deleteIds);
        if (keepIds.length > 0) await api.markCropsReady(keepIds);
        const gone = new Set(deleteIds);
        const ready = new Set(keepIds);
        setDrawerCropId((current) => (current && gone.has(current) ? null : current));
        setSelectedCropId((current) => (current && gone.has(current) ? null : current));
        applyLocalPages((pages) =>
          pages.map((page) => ({
            ...page,
            stamps: page.stamps
              .filter((stamp) => !gone.has(stamp.crop_id))
              .map((stamp) =>
                ready.has(stamp.crop_id)
                  ? { ...stamp, review_state: "unreviewed", warnings: [] }
                  : stamp,
              ),
          })),
        );
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyLocalPages, reportError],
  );

  const mutate = useCallback(
    async (action: () => Promise<CollectionExport>, bumpImages = false) => {
      setBusy(true);
      setError(null);
      try {
        applyExport(await action(), bumpImages);
        await refreshCollections();
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyExport, refreshCollections, reportError],
  );

  // Uploads are chunked client-side so any number of pages can be selected
  // at once (each request stays small and page detection runs per chunk).
  // Pages already in the collection are skipped server-side by filename, so
  // a failed upload is resumed by simply re-selecting the same files.
  const UPLOAD_CHUNK_SIZE = 20;

  const handleUpload = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const allFiles = Array.from(files);
      void (async () => {
        setBusy(true);
        setError(null);
        setNotice(null);
        let collectionId = exp?.collection.collection_id ?? null;
        let added = 0;
        let skippedCount = 0;
        let latest: CollectionExport | null = null;
        let processed = 0;
        try {
          for (let start = 0; start < allFiles.length; start += UPLOAD_CHUNK_SIZE) {
            const chunk = allFiles.slice(start, start + UPLOAD_CHUNK_SIZE);
            setNotice(
              `Uploading and detecting stamps… ${processed}/${allFiles.length} pages done`,
            );
            if (collectionId === null) {
              latest = await api.uploadCollection(chunk);
              collectionId = latest.collection.collection_id;
              added += latest.pages.length;
            } else {
              latest = await api.addPagesToCollection(collectionId, chunk);
              added += latest.added_page_count ?? 0;
              skippedCount += (latest.skipped_duplicate_filenames ?? []).length;
            }
            processed += chunk.length;
            applyExport(latest);
          }
          if (latest) applyExport(latest, true);
          await refreshCollections();
          setNotice(
            `Added ${added} pages` +
              (skippedCount > 0 ? `; skipped ${skippedCount} already uploaded` : ""),
          );
        } catch (exc) {
          reportError(exc);
          setNotice(
            `Upload interrupted after ${added} new pages — everything ingested so far is ` +
              "saved. Re-select the same files to continue; already-uploaded pages are " +
              "skipped automatically.",
          );
          if (latest) applyExport(latest, true);
          await refreshCollections();
        } finally {
          setBusy(false);
        }
      })();
    },
    [exp, applyExport, refreshCollections, reportError],
  );

  const handleCropCommit = useCallback(
    async (cropId: string, bbox: BBox, rotationDegrees: number) => {
      setBusy(true);
      setError(null);
      try {
        const { crop } = await api.updateCrop(cropId, bbox, rotationDegrees);
        applyLocalPages((pages) =>
          pages.map((page) => ({
            ...page,
            stamps: page.stamps.map((stamp) =>
              stamp.crop_id === cropId
                ? {
                    ...stamp,
                    bbox_xywh: crop.bbox_xywh,
                    rotation_degrees: crop.rotation_degrees,
                    segmentation_confidence: crop.segmentation_confidence,
                    review_state: crop.review_state,
                    warnings: crop.warnings,
                  }
                : stamp,
            ),
          })),
        );
        setImageVersion((version) => version + 1);
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyLocalPages, reportError],
  );

  const handleDeleteCollection = useCallback(async () => {
    if (!exp) return;
    const title = exp.collection.title ?? exp.collection.collection_id;
    if (!window.confirm(`Delete collection "${title}" and all its data?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteCollection(exp.collection.collection_id);
      setExp(null);
      setSelectedCropId(null);
      setSelectedPageId(null);
      setDrawerCropId(null);
      const list = await api.listCollections();
      setCollections(list);
      if (list.length > 0) applyExport(await api.getCollection(list[0].collection_id));
    } catch (exc) {
      reportError(exc);
    } finally {
      setBusy(false);
    }
  }, [exp, applyExport, reportError]);

  const startJobPolling = useCallback(
    (startedJob: EvaluationJob) => {
      setJob(startedJob);
      const poll = async () => {
        try {
          const latest = await api.getEvaluationJob(startedJob.job_id);
          setJob(latest);
          if (
            latest.status === "completed" ||
            latest.status === "failed" ||
            latest.status === "cancelled"
          ) {
            applyExport(await api.getCollection(latest.collection_id));
            await refreshCollections();
            return;
          }
          window.setTimeout(() => void poll(), 700);
        } catch (exc) {
          reportError(exc);
        }
      };
      window.setTimeout(() => void poll(), 700);
    },
    [applyExport, refreshCollections, reportError],
  );

  useEffect(() => {
    void (async () => {
      try {
        const list = await api.listCollections();
        setCollections(list);
        if (list.length > 0) applyExport(await api.getCollection(list[0].collection_id));
        // Re-attach to a run that survived a page reload: the backend keeps
        // job progress server-side, the browser only forgot the job id.
        const { jobs } = await api.listActiveEvaluationJobs();
        if (jobs.length > 0) startJobPolling(jobs[jobs.length - 1]);
      } catch (exc) {
        reportError(exc);
      }
    })();
  }, [applyExport, reportError, startJobPolling]);

  const handleEvaluate = useCallback(
    async (cropIds?: string[]) => {
      if (!exp) return;
      setError(null);
      try {
        // Confirm with a cost estimate for anything beyond a single-stamp
        // re-analyze.
        if (!cropIds || cropIds.length !== 1) {
          const estimate = await api.estimateEvaluationCost(
            exp.collection.collection_id,
            cropIds && cropIds.length > 0 ? cropIds : undefined,
          );
          if (estimate.provider !== "none") {
            const costLabel =
              estimate.estimated_total_cost_usd !== null
                ? `~$${estimate.estimated_total_cost_usd.toFixed(2)}`
                : "an unknown amount";
            const skipped =
              estimate.skipped_crop_review_count > 0
                ? ` ${estimate.skipped_crop_review_count} crops pending review will be skipped.`
                : "";
            if (
              !window.confirm(
                `This run will make ${estimate.billable_api_call_count} AI calls, costing ${costLabel}.${skipped}\n\nStart the run?`,
              )
            ) {
              return;
            }
          }
        }
        startJobPolling(await api.startEvaluation(exp.collection.collection_id, cropIds));
      } catch (exc) {
        reportError(exc);
      }
    },
    [exp, startJobPolling, reportError],
  );

  const handleGatherEvidence = useCallback(
    (cropId: string) => {
      void mutate(() => api.gatherCropEvidence(cropId));
    },
    [mutate],
  );

  const handleSetValuation = useCallback(
    (
      cropId: string,
      update: {
        estimated_value_low: number;
        estimated_value_high: number;
        currency: string;
        note?: string;
      },
    ) => {
      void mutate(() => api.setOwnerValuation(cropId, update));
    },
    [mutate],
  );

  const handleReplaceImage = useCallback(
    async (cropId: string, file: File) => {
      setBusy(true);
      setError(null);
      try {
        const { crop } = await api.replaceCropImage(cropId, file);
        applyLocalPages((pages) =>
          pages.map((page) => ({
            ...page,
            stamps: page.stamps.map((stamp) =>
              stamp.crop_id === cropId
                ? { ...stamp, review_state: crop.review_state, warnings: crop.warnings }
                : stamp,
            ),
          })),
        );
        setImageVersion((version) => version + 1);
        setNotice(
          "Photo replaced. Hit Re-analyze on this stamp to refresh its identification "
            + "from the better image.",
        );
      } catch (exc) {
        reportError(exc);
      } finally {
        setBusy(false);
      }
    },
    [applyLocalPages, reportError],
  );

  const handleGatherEvidenceAll = useCallback(async () => {
    if (!exp) return;
    setError(null);
    try {
      startJobPolling(await api.startEvidenceGathering(exp.collection.collection_id));
    } catch (exc) {
      reportError(exc);
    }
  }, [exp, startJobPolling, reportError]);

  const handleResumeRun = useCallback(
    async (runId: string) => {
      setError(null);
      try {
        startJobPolling(await api.resumeEvaluationRun(runId));
      } catch (exc) {
        reportError(exc);
      }
    },
    [startJobPolling, reportError],
  );

  const handleCancelJob = useCallback(async () => {
    if (!job) return;
    setError(null);
    try {
      setJob(await api.cancelEvaluationJob(job.job_id));
    } catch (exc) {
      reportError(exc);
    }
  }, [job, reportError]);

  const openBucket = useCallback((bucket: string | null) => {
    setBucketFilter(bucket);
    setDrawerCropId(null);
    setView("stamps");
  }, []);

  const openStamp = useCallback((cropId: string | null) => {
    setDrawerCropId(cropId);
    if (cropId) setView("stamps");
  }, []);

  const fixCrop = useCallback(
    (cropId: string) => {
      if (!exp) return;
      const owner = exp.pages.find((page) =>
        page.stamps.some((stamp) => stamp.crop_id === cropId),
      );
      setDrawerCropId(null);
      if (owner) setSelectedPageId(owner.page_id);
      setSelectedCropId(cropId);
      setView("curate");
    },
    [exp],
  );

  const jobRunning = job !== null && (job.status === "queued" || job.status === "running");
  const anyBusy = busy || jobRunning;
  const needsReviewCount = exp?.collection.needs_crop_review_count ?? 0;

  return (
    <div className="app">
      <TopBar
        collections={collections}
        exp={exp}
        view={view}
        job={job}
        jobRunning={jobRunning}
        theme={theme}
        busy={anyBusy}
        onCancelJob={() => void handleCancelJob()}
        needsReviewCount={needsReviewCount}
        stampCount={exp?.collection.stamp_count ?? 0}
        onViewChange={setView}
        onSelectCollection={(collectionId) => void loadCollection(collectionId)}
        onUploadClick={() => fileInputRef.current?.click()}
        onToggleTheme={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
        onSettingsClick={() => setSettingsOpen(true)}
      />
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.heic,.heif"
        style={{ display: "none" }}
        onChange={(event) => {
          handleUpload(event.target.files);
          event.target.value = "";
        }}
      />

      {error && (
        <div className="error-bar">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      {notice && (
        <div className="notice-bar">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)}>×</button>
        </div>
      )}

      {exp === null ? (
        <div className="empty-state">
          <p>Upload album page photos to start a collection.</p>
          <button className="btn primary" onClick={() => fileInputRef.current?.click()}>
            Upload pages
          </button>
        </div>
      ) : (
        <main className="view">
          {view === "overview" && (
            <OverviewView
              exp={exp}
              busy={anyBusy}
              imageVersion={imageVersion}
              onStartQueue={() => {
                setSelectedCropId(null);
                setView("curate");
              }}
              onEvaluate={(cropIds) => void handleEvaluate(cropIds)}
              onResumeRun={(runId) => void handleResumeRun(runId)}
              onOpenBucket={openBucket}
              onOpenStamp={(cropId) => openStamp(cropId)}
              onGatherEvidenceAll={() => void handleGatherEvidenceAll()}
              onDeleteCollection={() => void handleDeleteCollection()}
            />
          )}
          {view === "curate" && (
            <CurateView
              exp={exp}
              imageVersion={imageVersion}
              busy={anyBusy}
              selectedPageId={selectedPageId}
              selectedCropId={selectedCropId}
              drawMode={drawMode}
              onSelectPage={setSelectedPageId}
              onSelectCrop={setSelectedCropId}
              onToggleDraw={() => setDrawMode((mode) => !mode)}
              onDrawComplete={(bbox) => {
                const page = exp.pages.find((p) => p.page_id === selectedPageId) ?? exp.pages[0];
                if (!page) return;
                setDrawMode(false);
                void mutate(() => api.createManualCrop(page.page_id, bbox), true);
              }}
              onRedetect={(pageId) => void mutate(() => api.redetectPage(pageId), true)}
              onDeletePage={(pageId) => void mutate(() => api.deletePage(pageId))}
              onCropCommit={(cropId, bbox, rotation) =>
                void handleCropCommit(cropId, bbox, rotation)
              }
              onDeleteCrop={(cropId) => void handleDeleteCrop(cropId)}
              onMarkReady={(cropId) => void handleMarkReady([cropId])}
              onMarkReadyMany={(cropIds) => void handleMarkReady(cropIds)}
              onGridApply={(deleteIds, keepIds) => void handleGridApply(deleteIds, keepIds)}
              onEvaluateCrop={(cropId) => void handleEvaluate([cropId])}
            />
          )}
          {view === "stamps" && (
            <StampsView
              exp={exp}
              imageVersion={imageVersion}
              busy={anyBusy}
              bucketFilter={bucketFilter}
              drawerCropId={drawerCropId}
              onBucketFilter={setBucketFilter}
              onOpenStamp={openStamp}
              onFixCrop={fixCrop}
              onReanalyze={(cropId) => void handleEvaluate([cropId])}
              onGatherEvidence={handleGatherEvidence}
              onSetValuation={handleSetValuation}
              onReplaceImage={(cropId, file) => void handleReplaceImage(cropId, file)}
              onDeleteCrop={(cropId) => void handleDeleteCrop(cropId)}
            />
          )}
        </main>
      )}

      {settingsOpen && <SettingsDialog onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
