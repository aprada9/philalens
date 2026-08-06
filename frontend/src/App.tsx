import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api";
import EvaluationPanel from "./components/EvaluationPanel";
import Inspector from "./components/Inspector";
import PageViewer from "./components/PageViewer";
import SettingsDialog from "./components/SettingsDialog";
import StampList from "./components/StampList";
import type { BBox, CollectionExport, CollectionInfo, EvaluationJob, Stamp } from "./types";

export type StampFilter =
  | { kind: "all" }
  | { kind: "pending_review" }
  | { kind: "bucket"; bucket: string };

export default function App() {
  const [collections, setCollections] = useState<CollectionInfo[]>([]);
  const [exp, setExp] = useState<CollectionExport | null>(null);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [selectedCropId, setSelectedCropId] = useState<string | null>(null);
  const [checkedCropIds, setCheckedCropIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<StampFilter>({ kind: "all" });
  const [drawMode, setDrawMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [imageVersion, setImageVersion] = useState(1);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const pages = exp?.pages ?? [];
  const currentPage = pages.find((page) => page.page_id === selectedPageId) ?? pages[0] ?? null;
  const allStamps = useMemo(() => pages.flatMap((page) => page.stamps), [pages]);
  const selectedStamp: Stamp | null =
    allStamps.find((stamp) => stamp.crop_id === selectedCropId) ?? null;
  const selectedStampPage =
    pages.find((page) => page.stamps.some((s) => s.crop_id === selectedCropId)) ?? null;

  const applyExport = useCallback((next: CollectionExport, bumpImages = false) => {
    setExp(next);
    const cropIds = new Set(next.pages.flatMap((page) => page.stamps.map((s) => s.crop_id)));
    setSelectedCropId((current) => (current && cropIds.has(current) ? current : null));
    setCheckedCropIds(
      (current) => new Set(Array.from(current).filter((id) => cropIds.has(id))),
    );
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
      setError(String(exc instanceof Error ? exc.message : exc));
    }
  }, []);

  const loadCollection = useCallback(
    async (collectionId: string) => {
      setBusy(true);
      setError(null);
      try {
        applyExport(await api.getCollection(collectionId));
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      } finally {
        setBusy(false);
      }
    },
    [applyExport],
  );

  useEffect(() => {
    void (async () => {
      try {
        const list = await api.listCollections();
        setCollections(list);
        if (list.length > 0) {
          applyExport(await api.getCollection(list[0].collection_id));
        }
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      }
    })();
  }, [applyExport]);

  const mutate = useCallback(
    async (action: () => Promise<CollectionExport>, bumpImages = false) => {
      setBusy(true);
      setError(null);
      try {
        applyExport(await action(), bumpImages);
        await refreshCollections();
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      } finally {
        setBusy(false);
      }
    },
    [applyExport, refreshCollections],
  );

  const handleUpload = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      void mutate(() => api.uploadCollection(files), true);
    },
    [mutate],
  );

  const handleCropCommit = useCallback(
    async (cropId: string, bbox: BBox, rotationDegrees: number) => {
      if (!exp) return;
      setBusy(true);
      setError(null);
      try {
        await api.updateCrop(cropId, bbox, rotationDegrees);
        applyExport(await api.getCollection(exp.collection.collection_id), true);
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      } finally {
        setBusy(false);
      }
    },
    [exp, applyExport],
  );

  const handleManualCrop = useCallback(
    (bbox: BBox) => {
      if (!currentPage) return;
      setDrawMode(false);
      void mutate(() => api.createManualCrop(currentPage.page_id, bbox), true);
    },
    [currentPage, mutate],
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
      const list = await api.listCollections();
      setCollections(list);
      if (list.length > 0) applyExport(await api.getCollection(list[0].collection_id));
    } catch (exc) {
      setError(String(exc instanceof Error ? exc.message : exc));
    } finally {
      setBusy(false);
    }
  }, [exp, applyExport]);

  const startJobPolling = useCallback(
    (startedJob: EvaluationJob) => {
      setJob(startedJob);
      const poll = async () => {
        try {
          const latest = await api.getEvaluationJob(startedJob.job_id);
          setJob(latest);
          if (latest.status === "completed" || latest.status === "failed") {
            if (exp) applyExport(await api.getCollection(exp.collection.collection_id));
            await refreshCollections();
            return;
          }
          window.setTimeout(() => void poll(), 700);
        } catch (exc) {
          setError(String(exc instanceof Error ? exc.message : exc));
        }
      };
      window.setTimeout(() => void poll(), 700);
    },
    [exp, applyExport, refreshCollections],
  );

  const handleEvaluate = useCallback(
    async (cropIds?: string[]) => {
      if (!exp) return;
      setError(null);
      try {
        startJobPolling(await api.startEvaluation(exp.collection.collection_id, cropIds));
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      }
    },
    [exp, startJobPolling],
  );

  const handleResumeRun = useCallback(
    async (runId: string) => {
      setError(null);
      try {
        startJobPolling(await api.resumeEvaluationRun(runId));
      } catch (exc) {
        setError(String(exc instanceof Error ? exc.message : exc));
      }
    },
    [startJobPolling],
  );

  const toggleChecked = useCallback((cropId: string) => {
    setCheckedCropIds((current) => {
      const next = new Set(current);
      if (next.has(cropId)) next.delete(cropId);
      else next.add(cropId);
      return next;
    });
  }, []);

  const jobRunning = job !== null && (job.status === "queued" || job.status === "running");

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">Philalens</span>
        <select
          value={exp?.collection.collection_id ?? ""}
          onChange={(event) => void loadCollection(event.target.value)}
          disabled={collections.length === 0}
        >
          {collections.length === 0 && <option value="">No collections yet</option>}
          {collections.map((collection) => (
            <option key={collection.collection_id} value={collection.collection_id}>
              {(collection.title ?? collection.collection_id) +
                ` — ${collection.page_count}p / ${collection.stamp_count} stamps`}
            </option>
          ))}
        </select>
        <button onClick={() => fileInputRef.current?.click()} disabled={busy}>
          Upload pages
        </button>
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
        <span className="spacer" />
        {exp && (
          <>
            <a href={`/api/collections/${exp.collection.collection_id}/export.json`}>
              <button>Export JSON</button>
            </a>
            <a href={`/api/collections/${exp.collection.collection_id}/export.csv`}>
              <button>Export CSV</button>
            </a>
            <button className="danger" onClick={() => void handleDeleteCollection()} disabled={busy}>
              Delete collection
            </button>
          </>
        )}
        <button onClick={() => setSettingsOpen(true)}>Settings</button>
      </header>

      {error && (
        <div className="error-bar">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {exp && (
        <EvaluationPanel
          exp={exp}
          job={job}
          jobRunning={jobRunning}
          checkedCount={checkedCropIds.size}
          busy={busy}
          onEvaluateAll={() => void handleEvaluate()}
          onEvaluateChecked={() => void handleEvaluate(Array.from(checkedCropIds))}
          onResumeRun={(runId) => void handleResumeRun(runId)}
          onBucketClick={(bucket) => setFilter({ kind: "bucket", bucket })}
        />
      )}

      {exp === null ? (
        <div className="empty-state">
          <p>Upload album page photos to start a collection.</p>
          <button className="primary" onClick={() => fileInputRef.current?.click()}>
            Upload pages
          </button>
        </div>
      ) : (
        <div className="layout">
          <aside className="sidebar">
            <h3>Pages</h3>
            <div className="page-list">
              {pages.map((page) => (
                <button
                  key={page.page_id}
                  className={`page-row ${page.page_id === currentPage?.page_id ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedPageId(page.page_id);
                    setSelectedCropId(null);
                  }}
                >
                  <span>#{page.page_order}</span>
                  <span className="meta">
                    {page.original_filename} · {page.stamps.length} stamps
                  </span>
                </button>
              ))}
            </div>
            <StampList
              stamps={allStamps}
              pages={pages}
              selectedCropId={selectedCropId}
              checkedCropIds={checkedCropIds}
              filter={filter}
              imageVersion={imageVersion}
              busy={busy || jobRunning}
              onFilterChange={setFilter}
              onSelect={(stamp) => {
                setSelectedCropId(stamp.crop_id);
                const owner = pages.find((page) =>
                  page.stamps.some((s) => s.crop_id === stamp.crop_id),
                );
                if (owner) setSelectedPageId(owner.page_id);
              }}
              onToggleCheck={toggleChecked}
              onCheckMany={(ids, checked) =>
                setCheckedCropIds((current) => {
                  const next = new Set(current);
                  for (const id of ids) {
                    if (checked) next.add(id);
                    else next.delete(id);
                  }
                  return next;
                })
              }
              onDeleteChecked={() =>
                void mutate(() => api.deleteCrops(Array.from(checkedCropIds)), true)
              }
              onMarkReadyChecked={() =>
                void mutate(() => api.markCropsReady(Array.from(checkedCropIds)))
              }
              onEvaluateChecked={() => void handleEvaluate(Array.from(checkedCropIds))}
            />
          </aside>

          <section className="viewer">
            <div className="viewer-toolbar">
              <button
                className={drawMode ? "active" : ""}
                onClick={() => setDrawMode((mode) => !mode)}
                disabled={!currentPage || busy}
              >
                {drawMode ? "Drawing… (drag on page)" : "Add missing stamp"}
              </button>
              <button
                onClick={() =>
                  currentPage && void mutate(() => api.redetectPage(currentPage.page_id), true)
                }
                disabled={!currentPage || busy}
              >
                Re-detect page
              </button>
              <button
                className="danger"
                onClick={() => {
                  if (!currentPage) return;
                  if (!window.confirm(`Delete page "${currentPage.original_filename}"?`)) return;
                  void mutate(() => api.deletePage(currentPage.page_id));
                }}
                disabled={!currentPage || busy}
              >
                Delete page
              </button>
              <span className="hint">
                {selectedCropId
                  ? "Selected stamp is highlighted. Resize/rotate in the inspector."
                  : "No selection: shaded areas are not covered by any crop — look for missed stamps."}
              </span>
            </div>
            <div className="viewer-canvas">
              {currentPage && (
                <PageViewer
                  page={currentPage}
                  selectedCropId={selectedCropId}
                  drawMode={drawMode}
                  onSelect={setSelectedCropId}
                  onDrawComplete={handleManualCrop}
                />
              )}
            </div>
          </section>

          <aside className="inspector">
            <h3>Stamp inspector</h3>
            {selectedStamp && selectedStampPage ? (
              <Inspector
                key={selectedStamp.crop_id}
                page={selectedStampPage}
                stamp={selectedStamp}
                imageVersion={imageVersion}
                busy={busy || jobRunning}
                onCommit={(bbox, rotation) =>
                  void handleCropCommit(selectedStamp.crop_id, bbox, rotation)
                }
                onDelete={() => void mutate(() => api.deleteCrop(selectedStamp.crop_id), true)}
                onMarkReady={() =>
                  void mutate(() => api.markCropsReady([selectedStamp.crop_id]))
                }
                onEvaluate={() => void handleEvaluate([selectedStamp.crop_id])}
              />
            ) : (
              <p className="empty">
                Select a stamp from the list or click a box on the page to inspect and edit it.
              </p>
            )}
          </aside>
        </div>
      )}

      {settingsOpen && <SettingsDialog onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
