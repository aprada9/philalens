"""Local browser visualizer."""

VISUALIZER_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Philalens</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f8;
      --surface: #ffffff;
      --line: #d8dde3;
      --text: #18202a;
      --muted: #657184;
      --accent: #1f6f78;
      --accent-strong: #174f57;
      --warn: #9f4e00;
      --danger: #a23131;
      --ok: #22693b;
    }
    * { box-sizing: border-box; }
    html, body {
      height: 100%;
      overflow: hidden;
    }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    button, input, select {
      font: inherit;
    }
    button {
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      border-radius: 6px;
      min-height: 34px;
      padding: 6px 10px;
      cursor: pointer;
    }
    button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    button.primary:hover { background: var(--accent-strong); }
    button.danger {
      color: var(--danger);
      border-color: #d9a8a8;
      background: #fff8f8;
    }
    button.danger:hover { background: #fdecec; }
    button.active {
      border-color: var(--accent);
      background: #e8f4f5;
      color: var(--accent-strong);
    }
    button:disabled {
      opacity: .55;
      cursor: not-allowed;
    }
    input, select {
      border: 1px solid var(--line);
      border-radius: 6px;
      min-height: 34px;
      padding: 6px 8px;
      background: #fff;
      color: var(--text);
    }
    .shell {
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100vh;
      min-height: 0;
    }
    header {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 14px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    h1 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
      white-space: nowrap;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .toolbar input[type="file"] {
      max-width: min(360px, 38vw);
    }
    .status {
      color: var(--muted);
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    main {
      display: grid;
      grid-template-columns: 260px minmax(360px, 1fr) 360px;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    aside, .viewer, .inspector {
      min-height: 0;
      overflow: auto;
    }
    aside {
      display: grid;
      grid-template-rows: auto minmax(96px, 28%) minmax(180px, 1fr);
      border-right: 1px solid var(--line);
      background: #fbfcfd;
      overflow: hidden;
    }
    .viewer {
      padding: 14px;
    }
    .inspector {
      border-left: 1px solid var(--line);
      background: #fbfcfd;
    }
    .band {
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    .scroll-band {
      min-height: 0;
      overflow: auto;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      padding: 8px;
    }
    .metric strong {
      display: block;
      font-size: 18px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }
    .list {
      display: grid;
      gap: 6px;
    }
    .list-toolbar {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 8px;
    }
    .list-toolbar button {
      min-height: 30px;
      padding: 4px 8px;
      font-size: 12px;
    }
    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .toggle input {
      min-height: 0;
      padding: 0;
    }
    .stamp-band {
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 0;
      overflow: hidden;
    }
    .scroll-list {
      min-height: 0;
      overflow: auto;
    }
    .row {
      width: 100%;
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      text-align: left;
      gap: 8px;
      border-radius: 0;
      border-left: 0;
      border-right: 0;
    }
    .row.active {
      border-color: #bed0d5;
      background: #eaf3f4;
    }
    .stamp-row {
      display: grid;
      grid-template-columns: auto 1fr;
      align-items: stretch;
      gap: 4px;
      min-width: 0;
    }
    .stamp-select {
      display: grid;
      place-items: center;
      min-width: 34px;
      border: 1px solid var(--line);
      background: var(--surface);
    }
    .stamp-main {
      grid-template-columns: minmax(0, 1fr);
      align-items: start;
      gap: 4px;
      padding: 6px 8px;
    }
    .stamp-title {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 600;
    }
    .stamp-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 11px;
      border: 1px solid var(--line);
      color: var(--muted);
      white-space: nowrap;
    }
    .badge.warn {
      color: var(--warn);
      border-color: #e7bf8a;
      background: #fff7ed;
    }
    .badge.ok {
      color: var(--ok);
      border-color: #a7d6b5;
      background: #eefaf1;
    }
    .badge.hot {
      color: #7b2c00;
      border-color: #e6a05b;
      background: #fff0dd;
    }
    .badge.info {
      color: #315da8;
      border-color: #adc4ee;
      background: #eef4ff;
    }
    .badge.neutral {
      color: var(--muted);
      background: #f3f5f7;
    }
    .settings-panel {
      position: fixed;
      inset: 0;
      display: none;
      place-items: center;
      background: rgba(24, 32, 42, .38);
      z-index: 20;
      padding: 18px;
    }
    .settings-panel.open {
      display: grid;
    }
    .settings-dialog {
      width: min(640px, 100%);
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 20px 70px rgba(0,0,0,.22);
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .settings-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
    .cost-dashboard {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      display: grid;
      gap: 8px;
      background: #f8fafb;
    }
    .cost-dashboard h3 {
      margin: 0;
      font-size: 14px;
    }
    .cost-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .cost-metric {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      background: #fff;
    }
    .cost-metric strong {
      display: block;
      font-size: 16px;
      line-height: 1.2;
    }
    .cost-metric span,
    .cost-note {
      color: var(--muted);
      font-size: 12px;
    }
    .progress-panel {
      display: none;
      grid-template-columns: 52px 1fr;
      align-items: center;
      gap: 10px;
      padding: 8px 16px;
      border-bottom: 1px solid var(--line);
      background: #eef7f8;
    }
    .progress-panel.active {
      display: grid;
    }
    .progress-thumb {
      width: 52px;
      height: 52px;
      object-fit: contain;
      background: #111;
      border: 1px solid var(--line);
      border-radius: 4px;
    }
    .progress-copy {
      display: grid;
      gap: 5px;
      min-width: 0;
    }
    .progress-label {
      font-size: 13px;
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .progress-meter {
      width: 100%;
      height: 10px;
      accent-color: var(--accent);
    }
    .page-frame {
      position: relative;
      width: 100%;
      max-width: 1120px;
      margin: 0 auto;
      border: 1px solid var(--line);
      background: #111;
      min-height: 420px;
      display: grid;
      place-items: center;
    }
    .page-frame.adding {
      cursor: crosshair;
    }
    .page-frame img {
      display: block;
      max-width: 100%;
      max-height: calc(100vh - 140px);
      width: auto;
      height: auto;
    }
    .overlay {
      position: absolute;
      border: 2px solid rgba(31, 111, 120, .95);
      background: rgba(31, 111, 120, .12);
      cursor: pointer;
      min-height: 0;
      padding: 0;
      z-index: 2;
    }
    .coverage-mask {
      position: absolute;
      pointer-events: none;
      z-index: 1;
    }
    .coverage-mask svg {
      display: block;
      width: 100%;
      height: 100%;
    }
    .overlay.warn {
      border-color: rgba(159, 78, 0, .95);
      background: rgba(159, 78, 0, .14);
    }
    .overlay.active {
      border-color: rgba(162, 49, 49, .98);
      border-width: 4px;
      background: rgba(162, 49, 49, .2);
      box-shadow: 0 0 0 3px rgba(255,255,255,.92), 0 0 0 7px rgba(162,49,49,.28);
      z-index: 4;
    }
    .manual-crop-preview {
      position: absolute;
      border: 2px dashed rgba(255, 255, 255, .95);
      background: rgba(31, 111, 120, .2);
      box-shadow: 0 0 0 2px rgba(31,111,120,.85);
      pointer-events: none;
      z-index: 5;
    }
    .crop-editor {
      position: relative;
      width: 100%;
      height: 320px;
      min-height: 260px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: #111;
    }
    .crop-editor img {
      position: absolute;
      display: block;
      max-width: none;
      max-height: none;
      user-select: none;
      pointer-events: none;
    }
    .crop-editor-box {
      position: absolute;
      border: 3px solid rgba(162, 49, 49, .98);
      background: rgba(162, 49, 49, .14);
      box-shadow: 0 0 0 2px rgba(255,255,255,.9);
      min-height: 0;
      padding: 0;
      touch-action: none;
      transform-origin: center center;
    }
    .resize-handle {
      position: absolute;
      width: 12px;
      height: 12px;
      border: 2px solid #fff;
      background: var(--danger);
      border-radius: 50%;
      box-shadow: 0 1px 4px rgba(0,0,0,.35);
      pointer-events: auto;
    }
    .resize-handle.nw {
      left: -7px;
      top: -7px;
      cursor: nwse-resize;
    }
    .resize-handle.ne {
      right: -7px;
      top: -7px;
      cursor: nesw-resize;
    }
    .resize-handle.sw {
      left: -7px;
      bottom: -7px;
      cursor: nesw-resize;
    }
    .resize-handle.se {
      right: -7px;
      bottom: -7px;
      cursor: nwse-resize;
    }
    .rotate-handle {
      position: absolute;
      left: 50%;
      top: -42px;
      width: 18px;
      height: 18px;
      margin-left: -9px;
      border: 2px solid #fff;
      background: var(--accent);
      border-radius: 50%;
      box-shadow: 0 1px 4px rgba(0,0,0,.35);
      cursor: grab;
      pointer-events: auto;
    }
    .rotate-handle::before {
      content: "";
      position: absolute;
      left: 50%;
      top: 16px;
      width: 2px;
      height: 24px;
      margin-left: -1px;
      background: rgba(255,255,255,.9);
    }
    .rotate-handle:active {
      cursor: grabbing;
    }
    .stamp-image {
      width: 100%;
      max-height: 280px;
      object-fit: contain;
      background: #111;
      border: 1px solid var(--line);
    }
    .fields {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .field {
      display: grid;
      gap: 4px;
    }
    .field label {
      color: var(--muted);
      font-size: 12px;
    }
    .full {
      grid-column: 1 / -1;
    }
    .empty {
      display: grid;
      place-items: center;
      min-height: 260px;
      color: var(--muted);
      text-align: center;
      padding: 24px;
    }
    @media (max-width: 1050px) {
      header {
        grid-template-columns: 1fr;
      }
      main {
        grid-template-columns: 1fr;
        overflow: auto;
      }
      aside, .inspector {
        border: 0;
        border-bottom: 1px solid var(--line);
        max-height: 45vh;
      }
      .toolbar {
        flex-wrap: wrap;
      }
      .toolbar input[type="file"] {
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>Philalens</h1>
      <form id="uploadForm" class="toolbar">
        <input id="files" name="files" type="file" multiple accept=".heic,.heif,.jpg,.jpeg,.png,.tif,.tiff,.webp,image/*">
        <button class="primary" type="submit">Upload batch</button>
        <select id="collectionSelect"></select>
        <button id="redetectPage" type="button">Re-detect page</button>
        <button id="evaluateCollection" type="button">Evaluate</button>
        <button id="addCrop" type="button">Add crop</button>
        <button id="deletePage" class="danger" type="button">Remove page</button>
        <button id="jsonExport" type="button">JSON</button>
        <button id="csvExport" type="button">CSV</button>
        <button id="settingsButton" type="button">Settings</button>
      </form>
      <div id="status" class="status">Ready</div>
    </header>
    <div id="evaluationProgress" class="progress-panel" aria-live="polite">
      <img id="evaluationProgressImage" class="progress-thumb" alt="">
      <div class="progress-copy">
        <div id="evaluationProgressLabel" class="progress-label">Evaluation queued</div>
        <progress id="evaluationProgressBar" class="progress-meter" max="1" value="0"></progress>
      </div>
    </div>
    <main>
      <aside>
        <div class="band summary" id="summary"></div>
        <div class="band scroll-band">
          <div class="list" id="pageList"></div>
        </div>
        <div class="band stamp-band">
          <div class="list-toolbar">
            <label class="toggle"><input id="reviewOnly" type="checkbox"> Review only</label>
            <button id="clearStamp" type="button">Clear</button>
            <button id="selectVisible" type="button">Select visible</button>
            <button id="clearSelected" type="button">Clear selected</button>
            <button id="markReadySelected" type="button">Mark ready</button>
            <button id="evaluateSelected" type="button">Evaluate selected</button>
            <button id="deleteSelected" class="danger" type="button">Remove selected</button>
          </div>
          <div class="list scroll-list" id="stampList"></div>
        </div>
      </aside>
      <section class="viewer">
        <div id="pageFrame" class="page-frame">
          <div class="empty">Upload a batch or select a saved collection.</div>
        </div>
      </section>
      <section class="inspector">
        <div id="inspector" class="band">
          <div class="empty">No stamp selected.</div>
        </div>
      </section>
    </main>
  </div>
  <div id="settingsPanel" class="settings-panel" aria-hidden="true">
    <form id="settingsForm" class="settings-dialog">
      <h2>Settings</h2>
      <div class="field">
        <label for="visionProvider">Vision provider</label>
        <select id="visionProvider" name="visionProvider">
          <option value="none">None</option>
          <option value="openai">OpenAI</option>
        </select>
      </div>
      <div class="field">
        <label for="openaiModel">OpenAI model</label>
        <input id="openaiModel" name="openaiModel" type="text" autocomplete="off">
      </div>
      <div class="field">
        <label for="openaiDetail">Image detail</label>
        <select id="openaiDetail" name="openaiDetail">
          <option value="low">Low</option>
          <option value="high">High</option>
          <option value="auto">Auto</option>
        </select>
      </div>
      <div class="field">
        <label for="openaiKey">OpenAI API key</label>
        <input id="openaiKey" name="openaiKey" type="password" autocomplete="off" placeholder="Leave blank to keep existing key">
      </div>
      <div id="settingsKeyState" class="status"></div>
      <div id="settingsCostDashboard" class="cost-dashboard"></div>
      <div class="settings-actions">
        <button id="closeSettings" type="button">Cancel</button>
        <button class="primary" type="submit">Save settings</button>
      </div>
    </form>
  </div>
  <script>
    const state = {
      collections: [],
      collection: null,
      pageIndex: 0,
      stampIndex: null,
      selectedCropIds: new Set(),
      reviewOnly: false,
      addCropMode: false,
      drag: null
    };

    const statusEl = document.getElementById("status");
    const evaluationProgress = document.getElementById("evaluationProgress");
    const evaluationProgressImage = document.getElementById("evaluationProgressImage");
    const evaluationProgressLabel = document.getElementById("evaluationProgressLabel");
    const evaluationProgressBar = document.getElementById("evaluationProgressBar");
    const collectionSelect = document.getElementById("collectionSelect");
    const redetectPageButton = document.getElementById("redetectPage");
    const evaluateCollectionButton = document.getElementById("evaluateCollection");
    const evaluateSelectedButton = document.getElementById("evaluateSelected");
    const deleteSelectedButton = document.getElementById("deleteSelected");
    const selectVisibleButton = document.getElementById("selectVisible");
    const clearSelectedButton = document.getElementById("clearSelected");
    const markReadySelectedButton = document.getElementById("markReadySelected");
    const addCropButton = document.getElementById("addCrop");
    const deletePageButton = document.getElementById("deletePage");
    const settingsButton = document.getElementById("settingsButton");
    const settingsPanel = document.getElementById("settingsPanel");
    const settingsForm = document.getElementById("settingsForm");
    const settingsCostDashboard = document.getElementById("settingsCostDashboard");
    const reviewOnlyCheckbox = document.getElementById("reviewOnly");
    const clearStampButton = document.getElementById("clearStamp");
    const pageFrame = document.getElementById("pageFrame");
    const pageList = document.getElementById("pageList");
    const stampList = document.getElementById("stampList");
    const summary = document.getElementById("summary");
    const inspector = document.getElementById("inspector");

    function setStatus(message) {
      statusEl.textContent = message;
    }

    function showEvaluationProgress(job) {
      const current = Number(job.current || 0);
      const total = Math.max(1, Number(job.total || 0));
      evaluationProgress.classList.add("active");
      evaluationProgressBar.max = total;
      evaluationProgressBar.value = Math.min(current, total);
      const costText = evaluationCostText(job.cost_actual || job.cost_estimate);
      evaluationProgressLabel.textContent = `${job.message || "Evaluating"} (${current}/${job.total || "?"})${costText ? ` | ${costText}` : ""}`;
      if (job.current_crop_image_url) {
        evaluationProgressImage.src = job.current_crop_image_url;
        evaluationProgressImage.alt = job.current_crop_label || "Current stamp crop";
        evaluationProgressImage.style.visibility = "visible";
      } else {
        evaluationProgressImage.removeAttribute("src");
        evaluationProgressImage.alt = "";
        evaluationProgressImage.style.visibility = "hidden";
      }
    }

    function hideEvaluationProgress() {
      evaluationProgress.classList.remove("active");
      evaluationProgressImage.removeAttribute("src");
      evaluationProgressBar.value = 0;
    }

    function formatUsd(value) {
      if (typeof value !== "number" || !Number.isFinite(value)) return "unknown";
      if (value === 0) return "$0.00";
      return value < 0.01 ? `$${value.toFixed(4)}` : `$${value.toFixed(2)}`;
    }

    function evaluationCostText(costPayload) {
      if (!costPayload) return "";
      const callCount = costPayload.api_call_count ?? costPayload.billable_api_call_count;
      if (typeof callCount === "number" && callCount <= 0) return "";
      const actual = costPayload.total_cost_usd;
      if (typeof actual === "number") {
        return `API cost ${formatUsd(actual)}`;
      }
      const known = costPayload.known_total_cost_usd;
      if (typeof known === "number") {
        return `known API cost ${formatUsd(known)}`;
      }
      const estimate = costPayload.estimated_total_cost_usd;
      if (typeof estimate === "number") {
        return `est. API cost ${formatUsd(estimate)}`;
      }
      if (costPayload.billable_api_call_count > 0 || costPayload.api_call_count > 0) {
        return "API cost unknown";
      }
      return "";
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
      }
      return response.json();
    }

    async function loadCollections() {
      state.collections = await requestJson("/api/collections");
      renderCollectionSelect();
      if (!state.collection && state.collections.length) {
        await loadCollection(state.collections[0].collection_id);
      } else {
        render();
      }
    }

    async function refreshCollectionOptions() {
      state.collections = await requestJson("/api/collections");
      renderCollectionSelect();
      if (state.collection) {
        collectionSelect.value = state.collection.collection.collection_id;
      }
    }

    async function loadCollection(collectionId, resetSelection = true) {
      state.collection = await requestJson(`/api/collections/${collectionId}`);
      if (resetSelection) {
        state.pageIndex = 0;
        state.stampIndex = null;
        state.selectedCropIds.clear();
        state.addCropMode = false;
      } else {
        state.pageIndex = Math.min(state.pageIndex, Math.max(0, state.collection.pages.length - 1));
        const page = currentPage();
        if (state.stampIndex !== null) {
          state.stampIndex = Math.min(state.stampIndex, Math.max(0, (page?.stamps?.length || 1) - 1));
        }
      }
      pruneSelectedCropIds();
      collectionSelect.value = collectionId;
      render();
    }

    function renderCollectionSelect() {
      collectionSelect.innerHTML = "";
      if (!state.collections.length) {
        const option = document.createElement("option");
        option.textContent = "No collections";
        option.value = "";
        collectionSelect.appendChild(option);
        return;
      }
      for (const collection of state.collections) {
        const option = document.createElement("option");
        option.value = collection.collection_id;
        option.textContent = `${collection.created_at.slice(0, 16)} - ${collection.page_count} pages`;
        collectionSelect.appendChild(option);
      }
    }

    function render() {
      renderSummary();
      renderPages();
      renderStamps();
      renderPageFrame();
      renderInspector();
      updateControls();
    }

    function updateControls() {
      redetectPageButton.disabled = !currentPage();
      evaluateCollectionButton.disabled = !state.collection;
      evaluateSelectedButton.disabled = selectedCropIds().length === 0;
      deleteSelectedButton.disabled = selectedCropIds().length === 0;
      selectVisibleButton.disabled = visibleStampIds().length === 0;
      clearSelectedButton.disabled = selectedCropIds().length === 0;
      markReadySelectedButton.disabled = selectedCropIds().length === 0;
      addCropButton.disabled = !currentPage();
      addCropButton.classList.toggle("active", state.addCropMode);
      addCropButton.textContent = state.addCropMode ? "Adding crop" : "Add crop";
      deletePageButton.disabled = !currentPage();
      reviewOnlyCheckbox.disabled = !currentPage();
      reviewOnlyCheckbox.checked = state.reviewOnly;
      clearStampButton.disabled = currentStamp() === null;
      document.getElementById("jsonExport").disabled = !state.collection;
      document.getElementById("csvExport").disabled = !state.collection;
    }

    function currentPage() {
      return state.collection?.pages?.[state.pageIndex] || null;
    }

    function currentStamp() {
      if (state.stampIndex === null) return null;
      return currentPage()?.stamps?.[state.stampIndex] || null;
    }

    function stampNeedsReview(stamp) {
      return stamp.review_state === "needs_crop_review";
    }

    function selectedCropIds() {
      if (!state.collection) return [];
      const validIds = new Set(state.collection.pages.flatMap(page => page.stamps.map(stamp => stamp.crop_id)));
      return Array.from(state.selectedCropIds).filter(cropId => validIds.has(cropId));
    }

    function visibleStampIds() {
      const page = currentPage();
      if (!page) return [];
      return page.stamps
        .filter(stamp => !state.reviewOnly || stampNeedsReview(stamp))
        .map(stamp => stamp.crop_id);
    }

    function pruneSelectedCropIds() {
      state.selectedCropIds = new Set(selectedCropIds());
    }

    function renderSummary() {
      if (!state.collection) {
        summary.innerHTML = `<div class="metric"><strong>0</strong><span>pages</span></div><div class="metric"><strong>0</strong><span>stamps</span></div><div class="metric"><strong>0</strong><span>review</span></div>`;
        return;
      }
      const data = state.collection.collection;
      const evaluation = state.collection.latest_evaluation_summary;
      const evaluated = evaluation ? `${evaluation.evaluated_stamp_count}/${data.stamp_count}` : "0";
      const attention = evaluation?.attention_recommended_count || 0;
      summary.innerHTML = `
        <div class="metric"><strong>${data.page_count}</strong><span>pages</span></div>
        <div class="metric"><strong>${data.stamp_count}</strong><span>stamps</span></div>
        <div class="metric"><strong>${data.needs_crop_review_count}</strong><span>crop review</span></div>
        <div class="metric"><strong>${evaluated}</strong><span>evaluated</span></div>
        <div class="metric"><strong>${attention}</strong><span>attention</span></div>
      `;
    }

    function renderPages() {
      pageList.innerHTML = "";
      if (!state.collection) return;
      state.collection.pages.forEach((page, index) => {
        const button = document.createElement("button");
        button.className = `row ${index === state.pageIndex ? "active" : ""}`;
        button.innerHTML = `<span>${page.page_order}. ${page.original_filename}</span><span class="badge">${page.stamps.length}</span>`;
        button.addEventListener("click", () => {
          state.pageIndex = index;
          state.stampIndex = null;
          state.addCropMode = false;
          render();
        });
        pageList.appendChild(button);
      });
    }

    function renderStamps() {
      stampList.innerHTML = "";
      const page = currentPage();
      if (!page) return;
      const stamps = page.stamps
        .map((stamp, index) => ({ stamp, index }))
        .filter(({ stamp }) => !state.reviewOnly || stampNeedsReview(stamp));
      if (!stamps.length) {
        stampList.innerHTML = `<div class="empty">${state.reviewOnly ? "No pending review crops." : "No crops detected."}</div>`;
        return;
      }
      stamps.forEach(({ stamp, index }) => {
        const needsReview = stampNeedsReview(stamp);
        const selected = state.selectedCropIds.has(stamp.crop_id);
        const row = document.createElement("div");
        row.className = "stamp-row";
        const checkbox = document.createElement("input");
        checkbox.className = "stamp-select";
        checkbox.type = "checkbox";
        checkbox.checked = selected;
        checkbox.title = `Select stamp ${stamp.crop_index}`;
        checkbox.addEventListener("click", (event) => {
          event.stopPropagation();
          toggleCropSelection(stamp.crop_id, checkbox.checked);
        });
        const button = document.createElement("button");
        button.className = `row stamp-main ${index === state.stampIndex ? "active" : ""}`;
        button.innerHTML = `
          <span class="stamp-title">Stamp ${stamp.crop_index}</span>
          <span class="stamp-tags">
            <span class="badge ${bucketClass(stamp.valuation?.value_bucket)}">Eval: ${bucketLabel(stamp.valuation?.value_bucket)}</span>
            <span class="badge ${needsReview ? "warn" : "ok"}">Crop: ${cropLabel(stamp.review_state)}</span>
          </span>
        `;
        button.addEventListener("click", () => {
          state.stampIndex = index;
          render();
        });
        row.appendChild(checkbox);
        row.appendChild(button);
        stampList.appendChild(row);
      });
    }

    function toggleCropSelection(cropId, selected) {
      if (selected) {
        state.selectedCropIds.add(cropId);
      } else {
        state.selectedCropIds.delete(cropId);
      }
      updateControls();
    }

    function selectVisibleStamps() {
      visibleStampIds().forEach(cropId => state.selectedCropIds.add(cropId));
      renderStamps();
      updateControls();
    }

    function clearSelectedStamps() {
      state.selectedCropIds.clear();
      renderStamps();
      updateControls();
    }

    function bucketLabel(bucket) {
      if (!bucket) return "not evaluated";
      return formatBucket(bucket);
    }

    function cropLabel(reviewState) {
      if (reviewState === "needs_crop_review") return "needs review";
      if (reviewState === "unreviewed") return "ready";
      return formatBucket(reviewState);
    }

    function bucketClass(bucket) {
      if (bucket === "possibly_interesting" || bucket === "needs_expert_check") return "hot";
      if (bucket === "needs_source_matching" || bucket === "not_enough_evidence") return "info";
      if (bucket === "likely_common") return "ok";
      if (bucket === "needs_better_image") return "warn";
      return "neutral";
    }

    function renderPageFrame() {
      const page = currentPage();
      if (!page) {
        pageFrame.innerHTML = `<div class="empty">Upload a batch or select a saved collection.</div>`;
        pageFrame.classList.remove("adding");
        return;
      }
      pageFrame.classList.toggle("adding", state.addCropMode);
      pageFrame.innerHTML = `<img id="pageImage" alt="${page.original_filename}" src="${page.normalized_image_url}">`;
      const image = document.getElementById("pageImage");
      pageFrame.onclick = (event) => {
        if (state.addCropMode || state.drag) return;
        if (event.target === image || event.target === pageFrame) {
          state.stampIndex = null;
          render();
        }
      };
      pageFrame.onpointerdown = (event) => {
        if (state.addCropMode) {
          startManualCrop(event, page, image);
        }
      };
      image.addEventListener("load", () => drawOverlays(page, image));
      if (image.complete) drawOverlays(page, image);
    }

    function drawOverlays(page, image) {
      const metrics = imageMetrics(page, image);
      if (state.stampIndex === null) {
        drawCoverageMask(page, metrics);
      }
      page.stamps.forEach((stamp, index) => {
        const overlay = document.createElement("div");
        overlay.className = `overlay ${stampNeedsReview(stamp) ? "warn" : ""} ${index === state.stampIndex ? "active" : ""}`;
        overlay.setAttribute("role", "button");
        overlay.tabIndex = 0;
        applyOverlayBox(overlay, stamp.bbox_xywh, metrics, stamp.rotation_degrees || 0);
        overlay.title = `Stamp ${stamp.crop_index}`;
        if (state.addCropMode) overlay.style.pointerEvents = "none";
        overlay.addEventListener("click", (event) => {
          event.stopPropagation();
          if (state.drag) return;
          state.stampIndex = index;
          render();
        });
        pageFrame.appendChild(overlay);
      });
    }

    function drawCoverageMask(page, metrics) {
      const mask = document.createElement("div");
      mask.className = "coverage-mask";
      mask.style.left = `${metrics.left}px`;
      mask.style.top = `${metrics.top}px`;
      mask.style.width = `${page.width * metrics.scaleX}px`;
      mask.style.height = `${page.height * metrics.scaleY}px`;

      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", `0 0 ${page.width} ${page.height}`);
      svg.setAttribute("preserveAspectRatio", "none");

      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      const svgMask = document.createElementNS("http://www.w3.org/2000/svg", "mask");
      svgMask.setAttribute("id", "coverageMask");
      svgMask.setAttribute("maskUnits", "userSpaceOnUse");
      const base = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      base.setAttribute("x", "0");
      base.setAttribute("y", "0");
      base.setAttribute("width", page.width);
      base.setAttribute("height", page.height);
      base.setAttribute("fill", "white");
      svgMask.appendChild(base);
      page.stamps.forEach((stamp) => {
        const cropHole = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        cropHole.setAttribute(
          "points",
          rotatedCropCorners(stamp.bbox_xywh, stamp.rotation_degrees || 0)
            .map(([x, y]) => `${x},${y}`)
            .join(" ")
        );
        cropHole.setAttribute("fill", "black");
        svgMask.appendChild(cropHole);
      });
      defs.appendChild(svgMask);
      svg.appendChild(defs);

      const shadedArea = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      shadedArea.setAttribute("x", "0");
      shadedArea.setAttribute("y", "0");
      shadedArea.setAttribute("width", page.width);
      shadedArea.setAttribute("height", page.height);
      shadedArea.setAttribute("fill", "rgba(0,0,0,.34)");
      shadedArea.setAttribute("mask", "url(#coverageMask)");
      svg.appendChild(shadedArea);
      mask.appendChild(svg);
      pageFrame.appendChild(mask);
    }

    function imageMetrics(page, image) {
      const rect = image.getBoundingClientRect();
      const frameRect = pageFrame.getBoundingClientRect();
      return {
        left: rect.left - frameRect.left,
        top: rect.top - frameRect.top,
        scaleX: rect.width / page.width,
        scaleY: rect.height / page.height
      };
    }

    function applyOverlayBox(overlay, bbox, metrics, rotationDegrees = 0) {
      const [x, y, width, height] = bbox;
      overlay.style.left = `${metrics.left + x * metrics.scaleX}px`;
      overlay.style.top = `${metrics.top + y * metrics.scaleY}px`;
      overlay.style.width = `${width * metrics.scaleX}px`;
      overlay.style.height = `${height * metrics.scaleY}px`;
      overlay.style.transform = `rotate(${rotationDegrees}deg)`;
      overlay.style.transformOrigin = "center center";
    }

    function rotatedCropCorners(bbox, rotationDegrees) {
      const [x, y, width, height] = bbox.map(Number);
      const radians = rotationDegrees * Math.PI / 180;
      const centerX = x + width / 2;
      const centerY = y + height / 2;
      const axisX = [Math.cos(radians), Math.sin(radians)];
      const axisY = [-Math.sin(radians), Math.cos(radians)];
      return [
        [
          centerX - axisX[0] * width / 2 - axisY[0] * height / 2,
          centerY - axisX[1] * width / 2 - axisY[1] * height / 2
        ],
        [
          centerX + axisX[0] * width / 2 - axisY[0] * height / 2,
          centerY + axisX[1] * width / 2 - axisY[1] * height / 2
        ],
        [
          centerX + axisX[0] * width / 2 + axisY[0] * height / 2,
          centerY + axisX[1] * width / 2 + axisY[1] * height / 2
        ],
        [
          centerX - axisX[0] * width / 2 + axisY[0] * height / 2,
          centerY - axisX[1] * width / 2 + axisY[1] * height / 2
        ]
      ];
    }

    function startManualCrop(event, page, image) {
      if (event.button !== 0 || state.drag) return;
      if (event.target !== image && event.target !== pageFrame) return;
      event.preventDefault();
      event.stopPropagation();
      const metrics = imageMetrics(page, image);
      const startPoint = pagePointFromEvent(event, metrics, page);
      const preview = document.createElement("div");
      preview.className = "manual-crop-preview";
      pageFrame.appendChild(preview);
      state.stampIndex = null;
      state.drag = {
        type: "manual",
        pointerId: event.pointerId,
        overlay: preview,
        metrics,
        startPoint,
        nextBox: [startPoint[0], startPoint[1], 12, 12]
      };
      pageFrame.setPointerCapture(event.pointerId);
      pageFrame.addEventListener("pointermove", moveManualCrop);
      pageFrame.addEventListener("pointerup", finishManualCrop);
      pageFrame.addEventListener("pointercancel", cancelManualCrop);
      applyOverlayBox(preview, state.drag.nextBox, metrics);
    }

    function moveManualCrop(event) {
      if (!state.drag || state.drag.type !== "manual" || event.pointerId !== state.drag.pointerId) return;
      const page = currentPage();
      const point = pagePointFromEvent(event, state.drag.metrics, page);
      state.drag.nextBox = boxFromPoints(state.drag.startPoint, point, page);
      applyOverlayBox(state.drag.overlay, state.drag.nextBox, state.drag.metrics);
    }

    async function finishManualCrop(event) {
      if (!state.drag || state.drag.type !== "manual" || event.pointerId !== state.drag.pointerId) return;
      const box = state.drag.nextBox;
      cleanupManualCrop(event);
      if (box[2] < 18 || box[3] < 18) {
        setStatus("Manual crop was too small");
        return;
      }
      await createManualCrop(box);
    }

    function cancelManualCrop(event) {
      if (!state.drag || state.drag.type !== "manual" || event.pointerId !== state.drag.pointerId) return;
      cleanupManualCrop(event);
    }

    function cleanupManualCrop(event) {
      const drag = state.drag;
      if (!drag) return;
      drag.overlay.remove();
      pageFrame.releasePointerCapture(event.pointerId);
      pageFrame.removeEventListener("pointermove", moveManualCrop);
      pageFrame.removeEventListener("pointerup", finishManualCrop);
      pageFrame.removeEventListener("pointercancel", cancelManualCrop);
      state.drag = null;
    }

    function pagePointFromEvent(event, metrics, page) {
      const frameRect = pageFrame.getBoundingClientRect();
      const x = (event.clientX - frameRect.left - metrics.left) / metrics.scaleX;
      const y = (event.clientY - frameRect.top - metrics.top) / metrics.scaleY;
      return [
        Math.max(0, Math.min(page.width, Math.round(x))),
        Math.max(0, Math.min(page.height, Math.round(y)))
      ];
    }

    function boxFromPoints(start, end, page) {
      const x = Math.min(start[0], end[0]);
      const y = Math.min(start[1], end[1]);
      const width = Math.abs(end[0] - start[0]);
      const height = Math.abs(end[1] - start[1]);
      return clampBox([x, y, width, height], page.width, page.height);
    }

    function startResize(event, stampIndex, handle, metrics, overlay) {
      event.preventDefault();
      event.stopPropagation();
      state.stampIndex = stampIndex;
      const stamp = currentPage().stamps[stampIndex];
      state.drag = {
        type: "resize",
        pointerId: event.pointerId,
        stampIndex,
        handle,
        overlay,
        metrics,
        rotationDegrees: stamp.rotation_degrees || 0,
        startX: event.clientX,
        startY: event.clientY,
        startBox: [...stamp.bbox_xywh],
        nextBox: [...stamp.bbox_xywh]
      };
      overlay.setPointerCapture(event.pointerId);
      overlay.addEventListener("pointermove", resizeCrop);
      overlay.addEventListener("pointerup", finishResize);
      overlay.addEventListener("pointercancel", cancelResize);
    }

    function resizeCrop(event) {
      if (!state.drag || state.drag.type !== "resize" || event.pointerId !== state.drag.pointerId) return;
      const page = currentPage();
      const dx = Math.round((event.clientX - state.drag.startX) / state.drag.metrics.scaleX);
      const dy = Math.round((event.clientY - state.drag.startY) / state.drag.metrics.scaleY);
      state.drag.nextBox = resizedBox(state.drag.startBox, state.drag.handle, dx, dy, page.width, page.height);
      applyOverlayBox(state.drag.overlay, state.drag.nextBox, state.drag.metrics, state.drag.rotationDegrees);
      updateBboxInputs(state.drag.nextBox);
    }

    async function finishResize(event) {
      if (!state.drag || state.drag.type !== "resize" || event.pointerId !== state.drag.pointerId) return;
      const drag = state.drag;
      const stamp = currentPage().stamps[drag.stampIndex];
      cleanupResize(event);
      await saveCropBbox(stamp, drag.nextBox);
    }

    function cancelResize(event) {
      if (!state.drag || state.drag.type !== "resize" || event.pointerId !== state.drag.pointerId) return;
      applyOverlayBox(
        state.drag.overlay,
        state.drag.startBox,
        state.drag.metrics,
        state.drag.rotationDegrees
      );
      cleanupResize(event);
    }

    function cleanupResize(event) {
      const drag = state.drag;
      if (!drag) return;
      drag.overlay.releasePointerCapture(event.pointerId);
      drag.overlay.removeEventListener("pointermove", resizeCrop);
      drag.overlay.removeEventListener("pointerup", finishResize);
      drag.overlay.removeEventListener("pointercancel", cancelResize);
      state.drag = null;
    }

    function startRotate(event, stampIndex, metrics, overlay) {
      event.preventDefault();
      event.stopPropagation();
      state.stampIndex = stampIndex;
      const stamp = currentPage().stamps[stampIndex];
      const center = overlayCenter(overlay);
      state.drag = {
        type: "rotate",
        pointerId: event.pointerId,
        stampIndex,
        overlay,
        metrics,
        center,
        startPointerAngle: pointerAngle(event, center),
        startRotation: stamp.rotation_degrees || 0,
        nextRotation: stamp.rotation_degrees || 0
      };
      overlay.setPointerCapture(event.pointerId);
      overlay.addEventListener("pointermove", rotateCrop);
      overlay.addEventListener("pointerup", finishRotate);
      overlay.addEventListener("pointercancel", cancelRotate);
    }

    function rotateCrop(event) {
      if (!state.drag || state.drag.type !== "rotate" || event.pointerId !== state.drag.pointerId) return;
      const stamp = currentPage().stamps[state.drag.stampIndex];
      const pointerDelta = pointerAngle(event, state.drag.center) - state.drag.startPointerAngle;
      state.drag.nextRotation = normalizeRotation(state.drag.startRotation + pointerDelta);
      applyOverlayBox(state.drag.overlay, stamp.bbox_xywh, state.drag.metrics, state.drag.nextRotation);
      updateRotationReadout(state.drag.nextRotation);
    }

    async function finishRotate(event) {
      if (!state.drag || state.drag.type !== "rotate" || event.pointerId !== state.drag.pointerId) return;
      const drag = state.drag;
      const stamp = currentPage().stamps[drag.stampIndex];
      cleanupRotate(event);
      await saveCropBbox(stamp, stamp.bbox_xywh, drag.nextRotation);
    }

    function cancelRotate(event) {
      if (!state.drag || state.drag.type !== "rotate" || event.pointerId !== state.drag.pointerId) return;
      const stamp = currentPage().stamps[state.drag.stampIndex];
      applyOverlayBox(state.drag.overlay, stamp.bbox_xywh, state.drag.metrics, stamp.rotation_degrees || 0);
      updateRotationReadout(stamp.rotation_degrees || 0);
      cleanupRotate(event);
    }

    function cleanupRotate(event) {
      const drag = state.drag;
      if (!drag) return;
      drag.overlay.releasePointerCapture(event.pointerId);
      drag.overlay.removeEventListener("pointermove", rotateCrop);
      drag.overlay.removeEventListener("pointerup", finishRotate);
      drag.overlay.removeEventListener("pointercancel", cancelRotate);
      state.drag = null;
    }

    function overlayCenter(overlay) {
      const rect = overlay.getBoundingClientRect();
      return {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2
      };
    }

    function pointerAngle(event, center) {
      return Math.atan2(event.clientY - center.y, event.clientX - center.x) * 180 / Math.PI;
    }

    function normalizeRotation(rotationDegrees) {
      let rotation = (Number(rotationDegrees) + 180) % 360;
      if (rotation < 0) rotation += 360;
      return Math.round((rotation - 180) * 10) / 10;
    }

    function formatRotation(rotationDegrees) {
      const rotation = normalizeRotation(rotationDegrees);
      return `${rotation.toFixed(1)}deg`;
    }

    function updateRotationReadout(rotationDegrees) {
      const readout = document.getElementById("rotationReadout");
      if (readout) readout.textContent = `Rotation ${formatRotation(rotationDegrees)}`;
    }

    function resizedBox(startBox, handle, dx, dy, pageWidth, pageHeight) {
      let [x, y, width, height] = startBox;
      if (handle.includes("w")) {
        x += dx;
        width -= dx;
      }
      if (handle.includes("e")) {
        width += dx;
      }
      if (handle.includes("n")) {
        y += dy;
        height -= dy;
      }
      if (handle.includes("s")) {
        height += dy;
      }
      return clampBox([x, y, width, height], pageWidth, pageHeight);
    }

    function clampBox(box, pageWidth, pageHeight) {
      let [x, y, width, height] = box.map(Number);
      const minSize = 12;
      width = Math.max(minSize, width);
      height = Math.max(minSize, height);
      x = Math.max(0, Math.min(pageWidth - minSize, x));
      y = Math.max(0, Math.min(pageHeight - minSize, y));
      width = Math.min(width, pageWidth - x);
      height = Math.min(height, pageHeight - y);
      return [Math.round(x), Math.round(y), Math.round(width), Math.round(height)];
    }

    function updateBboxInputs(bbox) {
      const ids = ["bboxX", "bboxY", "bboxW", "bboxH"];
      ids.forEach((id, index) => {
        const input = document.getElementById(id);
        if (input) input.value = bbox[index];
      });
    }

    function renderInspector() {
      const stamp = currentStamp();
      if (!stamp) {
        inspector.innerHTML = `<div class="empty">No stamp selected.</div>`;
        return;
      }
      const [x, y, width, height] = stamp.bbox_xywh;
      inspector.innerHTML = `
        <div class="list">
          <div id="cropEditor" class="crop-editor">
            <img id="cropEditorImage" alt="${currentPage().original_filename}" src="${currentPage().normalized_image_url}">
            <div id="cropEditorBox" class="crop-editor-box"></div>
          </div>
          <img class="stamp-image" alt="Stamp ${stamp.crop_index}" src="${stamp.crop_image_url}?v=${Date.now()}">
          <div><span class="badge ${stamp.review_state === "needs_crop_review" ? "warn" : "ok"}">${stamp.review_state}</span></div>
          <div class="status">Confidence ${Math.round(stamp.segmentation_confidence * 100)}%</div>
          <div id="rotationReadout" class="status">Rotation ${formatRotation(stamp.rotation_degrees || 0)}</div>
          <div class="status">${stamp.warnings.length ? stamp.warnings.join(", ") : "No crop warnings"}</div>
          <button id="deleteCrop" class="danger" type="button">Remove crop</button>
          <form id="bboxForm" class="fields">
            <div class="field"><label for="bboxX">X</label><input id="bboxX" name="x" type="number" min="0" value="${x}"></div>
            <div class="field"><label for="bboxY">Y</label><input id="bboxY" name="y" type="number" min="0" value="${y}"></div>
            <div class="field"><label for="bboxW">W</label><input id="bboxW" name="width" type="number" min="1" value="${width}"></div>
            <div class="field"><label for="bboxH">H</label><input id="bboxH" name="height" type="number" min="1" value="${height}"></div>
            <button class="primary full" type="submit">Save crop box</button>
          </form>
          <div class="field full">
            <label>Description</label>
            <div>${stamp.description}</div>
          </div>
          <div class="field full">
            <label>Observation</label>
            <div>${formatObservation(stamp.observation)}</div>
          </div>
          <div class="field full">
            <label>Valuation</label>
            <div>${formatValuation(stamp.valuation)}</div>
          </div>
        </div>
      `;
      document.getElementById("bboxForm").addEventListener("submit", saveCropBox);
      document.getElementById("deleteCrop").addEventListener("click", deleteCurrentCrop);
      setupCropEditor();
    }

    function formatObservation(observation) {
      if (!observation || observation.status !== "available") return "Not started";
      const hints = [
        observation.issuer_hint,
        observation.denomination_hint,
        observation.design_subject,
      ].filter(Boolean).join("; ");
      const warnings = observation.image_quality_warnings?.length
        ? `; warnings: ${observation.image_quality_warnings.join(", ")}`
        : "";
      return `${hints || "Observation recorded"}${warnings}`;
    }

    function formatValuation(valuation) {
      if (!valuation || valuation.status !== "available") return valuation?.status || "not_available";
      const bucket = formatBucket(valuation.value_bucket || "not_enough_evidence");
      const action = valuation.recommended_next_action || "No action recorded";
      return `${bucket}; ${action}`;
    }

    function formatBucket(bucket) {
      return String(bucket).replaceAll("_", " ");
    }

    function setupCropEditor() {
      const page = currentPage();
      const stamp = currentStamp();
      const editor = document.getElementById("cropEditor");
      const image = document.getElementById("cropEditorImage");
      const box = document.getElementById("cropEditorBox");
      if (!page || !stamp || !editor || !image || !box) return;

      const render = () => {
        const metrics = cropEditorMetrics(page, stamp, editor, image);
        applyOverlayBox(box, stamp.bbox_xywh, metrics, stamp.rotation_degrees || 0);
        box.innerHTML = "";
        for (const handle of ["nw", "ne", "sw", "se"]) {
          const node = document.createElement("span");
          node.className = `resize-handle ${handle}`;
          node.title = `Resize ${handle.toUpperCase()}`;
          node.addEventListener("pointerdown", (event) => startResize(event, state.stampIndex, handle, metrics, box));
          box.appendChild(node);
        }
        const rotate = document.createElement("span");
        rotate.className = "rotate-handle";
        rotate.title = "Drag to rotate crop";
        rotate.addEventListener("pointerdown", (event) => startRotate(event, state.stampIndex, metrics, box));
        box.appendChild(rotate);
      };

      image.addEventListener("load", render);
      if (image.complete) render();
    }

    function cropEditorMetrics(page, stamp, editor, image) {
      const [x, y, width, height] = stamp.bbox_xywh;
      const padding = Math.max(120, Math.round(Math.max(width, height) * 1.15));
      const context = clampContextBox(
        [x - padding, y - padding, width + padding * 2, height + padding * 2],
        page.width,
        page.height
      );
      const editorWidth = Math.max(1, editor.clientWidth);
      const editorHeight = Math.max(1, editor.clientHeight);
      const scale = Math.min((editorWidth - 18) / context[2], (editorHeight - 18) / context[3]);
      const contentWidth = context[2] * scale;
      const contentHeight = context[3] * scale;
      const left = (editorWidth - contentWidth) / 2 - context[0] * scale;
      const top = (editorHeight - contentHeight) / 2 - context[1] * scale;

      image.style.width = `${page.width * scale}px`;
      image.style.height = `${page.height * scale}px`;
      image.style.left = `${left}px`;
      image.style.top = `${top}px`;

      return { left, top, scaleX: scale, scaleY: scale };
    }

    function clampContextBox(box, pageWidth, pageHeight) {
      let [x, y, width, height] = box.map(Number);
      x = Math.max(0, Math.min(pageWidth - 1, x));
      y = Math.max(0, Math.min(pageHeight - 1, y));
      width = Math.min(width, pageWidth - x);
      height = Math.min(height, pageHeight - y);
      return [x, y, Math.max(1, width), Math.max(1, height)];
    }

    async function saveCropBox(event) {
      event.preventDefault();
      const stamp = currentStamp();
      const form = new FormData(event.currentTarget);
      const bbox = [
        Number(form.get("x")),
        Number(form.get("y")),
        Number(form.get("width")),
        Number(form.get("height"))
      ];
      await saveCropBbox(stamp, bbox);
    }

    async function saveCropBbox(stamp, bbox, rotationDegrees = undefined) {
      setStatus("Saving crop box...");
      const payload = { bbox_xywh: bbox };
      if (rotationDegrees !== undefined) {
        payload.rotation_degrees = rotationDegrees;
      }
      await requestJson(`/api/crops/${stamp.crop_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      await loadCollection(state.collection.collection.collection_id, false);
      setStatus("Crop box saved");
    }

    async function createManualCrop(bbox) {
      const page = currentPage();
      if (!page) return;
      try {
        setStatus("Creating manual crop...");
        state.collection = await requestJson(`/api/pages/${page.page_id}/crops`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bbox_xywh: bbox, rotation_degrees: 0 })
        });
        state.addCropMode = false;
        state.reviewOnly = false;
        state.stampIndex = Math.max(0, (currentPage()?.stamps?.length || 1) - 1);
        await refreshCollectionOptions();
        render();
        setStatus("Manual crop created");
      } catch (error) {
        setStatus(error.message);
      }
    }

    async function deleteCurrentCrop() {
      const stamp = currentStamp();
      if (!stamp) return;
      if (!confirm(`Remove crop for Stamp ${stamp.crop_index}?`)) return;
      try {
        setStatus("Removing crop...");
        state.collection = await requestJson(`/api/crops/${stamp.crop_id}`, { method: "DELETE" });
        state.selectedCropIds.delete(stamp.crop_id);
        state.stampIndex = null;
        state.addCropMode = false;
        await refreshCollectionOptions();
        render();
        setStatus("Crop removed");
      } catch (error) {
        setStatus(error.message);
      }
    }

    async function deleteSelectedCrops() {
      const cropIds = selectedCropIds();
      if (!cropIds.length) return;
      if (!confirm(`Remove ${cropIds.length} selected crop${cropIds.length === 1 ? "" : "s"}?`)) return;
      try {
        setStatus(`Removing ${cropIds.length} selected crop${cropIds.length === 1 ? "" : "s"}...`);
        state.collection = await requestJson("/api/crops/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ crop_ids: cropIds })
        });
        cropIds.forEach(cropId => state.selectedCropIds.delete(cropId));
        state.stampIndex = null;
        state.addCropMode = false;
        await refreshCollectionOptions();
        render();
        setStatus("Selected crops removed");
      } catch (error) {
        setStatus(error.message);
      }
    }

    async function markSelectedCropsReady() {
      const cropIds = selectedCropIds();
      if (!cropIds.length) return;
      try {
        setStatus(`Marking ${cropIds.length} selected crop${cropIds.length === 1 ? "" : "s"} ready...`);
        state.collection = await requestJson("/api/crops/mark-ready", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ crop_ids: cropIds })
        });
        pruneSelectedCropIds();
        render();
        setStatus("Selected crops marked ready");
      } catch (error) {
        setStatus(error.message);
      }
    }

    async function deleteCurrentPage() {
      const page = currentPage();
      if (!page) return;
      if (!confirm(`Remove page ${page.original_filename}?`)) return;
      try {
        setStatus("Removing page...");
        state.collection = await requestJson(`/api/pages/${page.page_id}`, { method: "DELETE" });
        state.pageIndex = Math.min(state.pageIndex, Math.max(0, state.collection.pages.length - 1));
        state.stampIndex = null;
        pruneSelectedCropIds();
        state.addCropMode = false;
        await refreshCollectionOptions();
        render();
        setStatus("Page removed");
      } catch (error) {
        setStatus(error.message);
      }
    }

    async function evaluateSelectedCrops() {
      if (!state.collection) return;
      const cropIds = selectedCropIds();
      if (!cropIds.length) return;
      await startEvaluation(cropIds);
    }

    async function startEvaluation(cropIds = null) {
      if (!state.collection) return;
      const collectionId = state.collection.collection.collection_id;
      const countLabel = cropIds?.length
        ? `${cropIds.length} selected stamp${cropIds.length === 1 ? "" : "s"}`
        : "collection";
      try {
        const costEstimate = await estimateEvaluationCost(collectionId, cropIds);
        const costText = evaluationCostText(costEstimate);
        setStatus(`Evaluating ${countLabel}${costText ? ` (${costText})` : ""}...`);
        showEvaluationProgress({
          status: "queued",
          current: 0,
          total: cropIds?.length || 0,
          message: "Queued evaluation",
          cost_estimate: costEstimate
        });
        const job = await requestJson(`/api/collections/${collectionId}/evaluate/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ crop_ids: cropIds || [] })
        });
        await pollEvaluationJob(job.job_id, collectionId);
      } catch (error) {
        hideEvaluationProgress();
        setStatus(error.message);
      }
    }

    async function pollEvaluationJob(jobId, collectionId) {
      while (true) {
        const job = await requestJson(`/api/evaluation-jobs/${jobId}`);
        showEvaluationProgress(job);
        if (job.status === "completed") {
          state.collection = await requestJson(`/api/collections/${collectionId}`);
          await refreshCollectionOptions();
          pruneSelectedCropIds();
          render();
          setStatus(job.message || "Evaluation complete");
          setTimeout(hideEvaluationProgress, 1200);
          return;
        }
        if (job.status === "failed") {
          hideEvaluationProgress();
          throw new Error(job.error || job.message || "Evaluation failed");
        }
        await sleep(500);
      }
    }

    function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function estimateEvaluationCost(collectionId, cropIds = null) {
      return requestJson(`/api/collections/${collectionId}/evaluation-cost-estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ crop_ids: cropIds || [] })
      });
    }

    function renderSettingsCostDashboard(dashboard) {
      if (!dashboard) {
        settingsCostDashboard.innerHTML = `<h3>API cost</h3><div class="cost-note">No cost data recorded yet.</div>`;
        return;
      }
      const latest = dashboard.latest_run;
      const latestCost = latest
        ? formatUsd(
            typeof latest.actual_cost_usd === "number"
              ? latest.actual_cost_usd
              : latest.estimated_cost_usd
          )
        : "none";
      settingsCostDashboard.innerHTML = `
        <h3>API cost</h3>
        <div class="cost-grid">
          <div class="cost-metric"><strong>${formatUsd(dashboard.total_actual_cost_usd)}</strong><span>recorded spend</span></div>
          <div class="cost-metric"><strong>${dashboard.api_call_count || 0}</strong><span>API calls</span></div>
          <div class="cost-metric"><strong>${dashboard.total_tokens || 0}</strong><span>tokens</span></div>
          <div class="cost-metric"><strong>${dashboard.evaluation_run_count || 0}</strong><span>runs</span></div>
          <div class="cost-metric"><strong>${latestCost}</strong><span>latest run</span></div>
          <div class="cost-metric"><strong>${dashboard.unknown_cost_call_count || 0}</strong><span>unknown cost calls</span></div>
        </div>
        <div class="cost-note">${dashboard.pricing_note || ""}</div>
      `;
    }

    async function openSettings() {
      try {
        const settings = await requestJson("/api/settings");
        document.getElementById("visionProvider").value = settings.vision_provider || "none";
        document.getElementById("openaiModel").value = settings.openai_vision_model || "gpt-4.1-mini";
        document.getElementById("openaiDetail").value = settings.openai_vision_detail || "high";
        document.getElementById("openaiKey").value = "";
        document.getElementById("settingsKeyState").textContent = settings.openai_api_key_set
          ? "OpenAI key is saved locally. Leave blank to keep it."
          : "No OpenAI key saved.";
        renderSettingsCostDashboard(settings.cost_dashboard);
        settingsPanel.classList.add("open");
        settingsPanel.setAttribute("aria-hidden", "false");
      } catch (error) {
        setStatus(error.message);
      }
    }

    function closeSettings() {
      settingsPanel.classList.remove("open");
      settingsPanel.setAttribute("aria-hidden", "true");
    }

    async function saveSettings(event) {
      event.preventDefault();
      const payload = {
        vision_provider: document.getElementById("visionProvider").value,
        openai_vision_model: document.getElementById("openaiModel").value,
        openai_vision_detail: document.getElementById("openaiDetail").value,
      };
      const key = document.getElementById("openaiKey").value.trim();
      if (key) payload.openai_api_key = key;
      try {
        await requestJson("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        closeSettings();
        setStatus("Settings saved");
      } catch (error) {
        setStatus(error.message);
      }
    }

    document.getElementById("uploadForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const files = document.getElementById("files").files;
      if (!files.length) return;
      const data = new FormData();
      Array.from(files).forEach(file => data.append("files", file));
      setStatus(`Uploading ${files.length} files...`);
      const collection = await requestJson("/api/collections", {
        method: "POST",
        body: data
      });
      setStatus("Upload complete");
      state.addCropMode = false;
      state.selectedCropIds.clear();
      await loadCollections();
      await loadCollection(collection.collection.collection_id);
    });

    collectionSelect.addEventListener("change", async () => {
      if (collectionSelect.value) {
        await loadCollection(collectionSelect.value);
      }
    });

    reviewOnlyCheckbox.addEventListener("change", () => {
      state.reviewOnly = reviewOnlyCheckbox.checked;
      const stamp = currentStamp();
      if (state.reviewOnly && stamp && !stampNeedsReview(stamp)) {
        state.stampIndex = null;
      }
      render();
    });

    clearStampButton.addEventListener("click", () => {
      state.stampIndex = null;
      render();
    });

    addCropButton.addEventListener("click", () => {
      if (!currentPage()) return;
      state.addCropMode = !state.addCropMode;
      state.stampIndex = null;
      render();
      setStatus(state.addCropMode ? "Drag on the page to create a crop" : "Manual crop cancelled");
    });

    redetectPageButton.addEventListener("click", async () => {
      const page = currentPage();
      if (!page) return;
      setStatus("Re-detecting page...");
      state.collection = await requestJson(`/api/pages/${page.page_id}/redetect`, { method: "POST" });
      state.stampIndex = null;
      pruneSelectedCropIds();
      state.addCropMode = false;
      render();
      setStatus(`Detected ${currentPage()?.stamps?.length || 0} stamps`);
    });

    evaluateCollectionButton.addEventListener("click", async () => {
      if (!state.collection) return;
      await startEvaluation();
    });

    selectVisibleButton.addEventListener("click", selectVisibleStamps);
    clearSelectedButton.addEventListener("click", clearSelectedStamps);
    markReadySelectedButton.addEventListener("click", markSelectedCropsReady);
    evaluateSelectedButton.addEventListener("click", evaluateSelectedCrops);
    deleteSelectedButton.addEventListener("click", deleteSelectedCrops);
    deletePageButton.addEventListener("click", deleteCurrentPage);
    settingsButton.addEventListener("click", openSettings);
    document.getElementById("closeSettings").addEventListener("click", closeSettings);
    settingsPanel.addEventListener("click", (event) => {
      if (event.target === settingsPanel) closeSettings();
    });
    settingsForm.addEventListener("submit", saveSettings);

    document.getElementById("jsonExport").addEventListener("click", () => {
      if (!state.collection) return;
      window.location.href = `/api/collections/${state.collection.collection.collection_id}/export.json`;
    });

    document.getElementById("csvExport").addEventListener("click", () => {
      if (!state.collection) return;
      window.location.href = `/api/collections/${state.collection.collection.collection_id}/export.csv`;
    });

    loadCollections().catch(error => setStatus(error.message));
  </script>
</body>
</html>
"""
