/**
 * Step 2 — AI Script Generation. UI state + validation only; all persistence
 * goes through Api.* (frontend/static/js/api.js), never fetch() directly (CR-05).
 */
(() => {
  const SPEAKER_COLORS = ["#7c3aed", "#0ea5e9", "#f59e0b", "#10b981", "#ef4444", "#ec4899"];

  const state = {
    projectId: null,
    project: null,
    lines: [],
    isGenerating: false,
    regeneratingLineId: null,
    saveStatus: "saved", // "saved" | "dirty" | "saving" | "failed"
    saveQueued: false,
    scriptLoadFailed: false,
    selectedLineId: null,
    previewingLineId: null,
    previewReadyLineId: null,
  };

  let saveIndicator = null;
  let currentAiJob = null;

  const AI_JOB_TERMINAL_MESSAGES = {
    error: "Generation failed",
    cancelled: "Generation cancelled.",
    stale: "The project changed since this job started — please try again.",
  };

  /** Render the durable-job status banner (Phase 13, Task 13.6). `job === null` hides it. */
  function renderJobStatus(job) {
    const el = document.getElementById("ai-job-status");
    if (!el) return;
    if (!job) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;

    if (job.status in AI_JOB_TERMINAL_MESSAGES) {
      const detail = job.status === "error" && job.error_message ? `: ${escapeHtml(job.error_message)}` : "";
      el.innerHTML =
        `${AI_JOB_TERMINAL_MESSAGES[job.status]}${detail} ` +
        '<button type="button" class="btn btn-primary btn-xs" id="ai-job-retry-btn">Retry</button>';
      const retryBtn = document.getElementById("ai-job-retry-btn");
      if (retryBtn) retryBtn.addEventListener("click", handleGenerate);
      return;
    }

    el.innerHTML =
      `<span class="spinner spinner-dark" aria-hidden="true"></span> Generating script — ${escapeHtml(job.stage)} ` +
      `(${job.progress}%) ` +
      '<button type="button" class="btn btn-ghost btn-xs" id="ai-job-cancel-btn">Cancel</button>';
    const cancelBtn = document.getElementById("ai-job-cancel-btn");
    if (cancelBtn) cancelBtn.addEventListener("click", () => currentAiJob && currentAiJob.cancel());
  }

  function makeScriptAiJob() {
    return AiJob.run({
      createFn: () => Api.createScriptJob(state.projectId),
      activeFn: () => Api.getActiveAiJob(state.projectId, "script"),
      getFn: (jobId) => Api.getAiJob(state.projectId, jobId),
      cancelFn: (jobId) => Api.cancelAiJob(state.projectId, jobId),
      onStateChange: renderJobStatus,
    });
  }

  /** Fire-and-forget: reload the script once the job settles, without blocking the caller. */
  function watchScriptAiJob() {
    currentAiJob.promise
      .then(async () => {
        state.lines = await Api.getScript(state.projectId);
        renderJobStatus(null);
        renderScript();
      })
      .catch((err) => {
        console.error("Script generation job did not complete:", err);
        if (!err.job) showError("We couldn't generate the script. Please try again.");
      })
      .finally(() => {
        state.isGenerating = false;
        setGenerateLoading(false);
      });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
  }

  /** Task 14.7 (local-only mode): disable the generate button and show
   * install/pull guidance when /api/ai/health reports Ollama unreachable or
   * the model missing. #generate-panel already exists in the page markup
   * (holding the intro paragraph + #generate-btn); the guidance banner is
   * injected into it via plain DOM APIs rather than a template change. A
   * failed health check itself is swallowed -- the page must stay usable
   * even if this one auxiliary check fails. */
  async function checkOllamaHealthAndGate() {
    const generatePanel = document.getElementById("generate-panel");
    const generateBtn = document.getElementById("generate-btn");
    if (!generatePanel || !generateBtn) return;

    let health;
    try {
      health = await Api.getAiHealth();
    } catch (error) {
      console.error("Could not check Ollama health:", error);
      return;
    }

    const existing = document.getElementById("ollama-guidance");
    const ready = health.ollama_reachable && health.model_present;
    generateBtn.disabled = !ready;
    if (ready) {
      if (existing) existing.remove();
      return;
    }

    const guidance = existing || document.createElement("div");
    guidance.id = "ollama-guidance";
    guidance.className = "ollama-guidance";
    guidance.setAttribute("role", "alert");
    guidance.innerHTML = health.ollama_reachable
      ? `Model <code>${escapeHtml(health.model)}</code> is not installed. Run ` +
        `<code>ollama pull ${escapeHtml(health.model)}</code>, then reload this page.`
      : `Ollama is not running. Install it from ` +
        `<a href="https://ollama.com/download" target="_blank" rel="noopener">ollama.com</a>, start it, ` +
        `run <code>ollama pull ${escapeHtml(health.model)}</code>, then reload this page.`;
    if (!existing) generatePanel.insertBefore(guidance, generateBtn);
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function showError(message) {
    const banner = document.getElementById("error-banner");
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function showMissingProjectError() {
    const banner = document.getElementById("error-banner");
    banner.innerHTML = 'Missing project. <a href="/">← Go to Dashboard</a>';
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearError() {
    const banner = document.getElementById("error-banner");
    banner.hidden = true;
    banner.textContent = "";
  }

  function setSaveStatusState(newStatus, customMessage) {
    state.saveStatus = newStatus;
    if (saveIndicator) saveIndicator.update(newStatus);
    const el = document.getElementById("save-status");
    if (!el) return;
    if (newStatus === "saving") {
      el.innerHTML = customMessage || "Saving…";
    } else if (newStatus === "saved") {
      el.innerHTML = customMessage || "Saved";
      setTimeout(() => {
        if (state.saveStatus === "saved" && el.textContent === (customMessage || "Saved")) {
          el.innerHTML = "";
        }
      }, 2000);
    } else if (newStatus === "dirty") {
      el.innerHTML = customMessage || "Unsaved changes";
    } else if (newStatus === "failed") {
      el.innerHTML =
        customMessage ||
        'Save failed — <button type="button" class="btn btn-ghost btn-xs" id="retry-save-btn" style="text-decoration:underline;padding:0 4px;font-size:12px;">Retry</button>';
      const retryBtn = document.getElementById("retry-save-btn");
      if (retryBtn) {
        retryBtn.onclick = (e) => {
          e.stopPropagation();
          autosave();
        };
      }
    }
    applyStateToDom();
  }

  function setGenerateLoading(loading) {
    const btn = document.getElementById("generate-btn");
    btn.disabled = loading;
    btn.innerHTML = loading ? '<span class="spinner"></span> Generating…' : "✨ Generate Script";
  }

  function speakerIndex(speakerId) {
    const index = state.project.speakers.findIndex((s) => s.id === speakerId);
    return index >= 0 ? index : 0;
  }

  function speakerColor(speakerId) {
    return SPEAKER_COLORS[speakerIndex(speakerId) % SPEAKER_COLORS.length];
  }

  function speakerName(speakerId) {
    const speaker = state.project.speakers.find((s) => s.id === speakerId);
    return speaker ? speaker.name : "Unknown speaker";
  }

  function renderHeader() {
    document.getElementById("project-name").textContent = state.project.name;
    const speakerCount = state.project.speakers.length;
    document.getElementById("project-badges").innerHTML = `
      <span class="badge">${escapeHtml(state.project.cefr_level)}</span>
      <span class="badge">${escapeHtml(state.project.genre)}</span>
      <span class="badge">${speakerCount} speaker${speakerCount === 1 ? "" : "s"}</span>
    `;
  }

  function lineCardHtml(line) {
    const color = speakerColor(line.speaker_id);
    const name = speakerName(line.speaker_id);
    const notes = line.language_notes || {};
    const collocations = (notes.collocations || []).join(", ") || "—";
    const idioms = (notes.idioms || []).join(", ") || "—";
    const grammar = notes.grammar_point || "—";
    const isRegenerating = state.regeneratingLineId === line.id;
    const isBusy = state.saveStatus === "saving" || state.isGenerating;
    const hasUnsaved = state.saveStatus === "dirty" || state.saveStatus === "failed";
    const regenerateDisabled = isRegenerating || isBusy || hasUnsaved;

    const isSelected = state.selectedLineId === line.id;

    return `
      <div class="card line-card${isSelected ? " selected" : ""}" data-line-id="${line.id}">
        <div class="line-header">
          <span class="speaker-chip" style="background:${hexToRgba(color, 0.15)}; border-color:${hexToRgba(color, 0.4)}; color:${color};">${escapeHtml(name)}</span>
          <button class="btn btn-ghost btn-sm" data-action="regenerate" ${regenerateDisabled ? "disabled" : ""}>
            ${isRegenerating ? '<span class="spinner spinner-dark"></span> Regenerating…' : "🔄 Regenerate this line"}
          </button>
        </div>
        <div class="line-text" data-action="edit-text">${escapeHtml(line.text)}</div>
        <details class="notes-details">
          <summary>Language notes</summary>
          <div class="notes-body">
            <div><strong>Collocations:</strong> ${escapeHtml(collocations)}</div>
            <div><strong>Idioms:</strong> ${escapeHtml(idioms)}</div>
            <div><strong>Grammar:</strong> ${escapeHtml(grammar)}</div>
          </div>
        </details>
      </div>`;
  }

  function selectedLine() {
    return state.lines.find((line) => line.id === state.selectedLineId) || null;
  }

  function renderTimeline() {
    const lane = document.getElementById("script-timeline");
    if (!lane) return;
    lane.innerHTML = state.lines
      .map((line, index) => {
        const active = line.id === state.selectedLineId ? " active" : "";
        const speakerClass = speakerIndex(line.speaker_id) % 2 === 0 ? " speaker-a" : "";
        return `<button type="button" class="timeline-clip${speakerClass}${active}" data-line-id="${line.id}" title="${escapeHtml(line.text)}">${escapeHtml(speakerName(line.speaker_id))} #${index + 1}</button>`;
      })
      .join("");
  }

  function renderInspector() {
    const container = document.getElementById("script-inspector");
    if (!container) return;
    const line = selectedLine();
    if (!line) {
      container.className = "inspector-empty";
      container.textContent = "Select a script line to inspect it.";
      return;
    }

    const notes = line.language_notes || {};
    const notesSummary = [
      notes.collocations && notes.collocations.length ? `Collocations: ${notes.collocations.join(", ")}` : null,
      notes.idioms && notes.idioms.length ? `Idioms: ${notes.idioms.join(", ")}` : null,
      notes.grammar_point ? `Grammar: ${notes.grammar_point}` : null,
    ].filter(Boolean).join(" · ") || "No language notes are available for this line.";
    const previewing = state.previewingLineId === line.id;
    const hasUnsaved = state.saveStatus === "dirty" || state.saveStatus === "failed";
    const regenerateDisabled = previewing || state.regeneratingLineId === line.id || state.saveStatus === "saving" || state.isGenerating || hasUnsaved;

    container.className = "";
    container.innerHTML = `
      <h2 class="inspector-title">Line ${state.lines.indexOf(line) + 1}</h2>
      <div class="inspector-meta"><span class="speaker-chip" style="background:${hexToRgba(speakerColor(line.speaker_id), 0.15)}; border-color:${hexToRgba(speakerColor(line.speaker_id), 0.4)}; color:${speakerColor(line.speaker_id)};">${escapeHtml(speakerName(line.speaker_id))}</span><span class="badge">Selected</span></div>
      <p class="inspector-copy">${escapeHtml(line.text)}</p>
      <div class="callout"><strong>Language notes</strong><br />${escapeHtml(notesSummary)}</div>
      <div class="inspector-actions">
        <button type="button" class="btn btn-ghost" data-inspector-action="listen" ${previewing ? "disabled" : ""}>${previewing ? '<span class="spinner spinner-dark"></span> Synthesizing…' : "🔊 Listen"}</button>
        <button type="button" class="btn btn-primary" data-inspector-action="regenerate" ${regenerateDisabled ? "disabled" : ""}>🔁 Regenerate</button>
      </div>
      <audio id="inspector-audio" class="inspector-audio" controls ${state.previewReadyLineId === line.id ? "" : "hidden"}></audio>`;
  }

  function selectLine(lineId) {
    if (!state.lines.some((line) => line.id === lineId)) return;
    if (state.selectedLineId === lineId) return;
    state.selectedLineId = lineId;
    state.previewReadyLineId = null;
    renderScript();
  }

  function renderScript() {
    const generatePanel = document.getElementById("generate-panel");
    const list = document.getElementById("script-list");
    const actions = document.getElementById("script-actions");

    if (state.scriptLoadFailed) {
      // Loading the existing script failed — never show "Generate", since a
      // real script may already exist and Generate would silently overwrite it.
      generatePanel.hidden = true;
      actions.hidden = true;
      list.innerHTML = "";
      state.selectedLineId = null;
      renderTimeline();
      renderInspector();
      return;
    }

    if (state.lines.length === 0) {
      // Keep the generate-panel hidden while a durable job is actively running
      // (Task 13.6) -- the ai-job-status banner is showing progress instead;
      // re-showing "No script yet, Generate one" underneath it would be
      // confusing and would let a second click fire during an active job.
      generatePanel.hidden = state.isGenerating;
      actions.hidden = true;
      list.innerHTML = "";
      state.selectedLineId = null;
      renderTimeline();
      renderInspector();
      return;
    }

    if (!state.lines.some((line) => line.id === state.selectedLineId)) {
      state.selectedLineId = state.lines[0].id;
    }
    generatePanel.hidden = true;
    actions.hidden = false;
    list.innerHTML = state.lines.map(lineCardHtml).join("");
    renderTimeline();
    renderInspector();
    applyStateToDom();
  }

  // Toggles the buttons' disabled states directly in the DOM (rather than a full
  // renderScript()) so an in-flight save never wipes out a textarea another line is mid-edit in.
  function applyStateToDom() {
    const isBusy = state.saveStatus === "saving" || state.isGenerating;
    const hasUnsaved = state.saveStatus === "dirty" || state.saveStatus === "failed";

    document.querySelectorAll('#script-list [data-action="regenerate"]').forEach((btn) => {
      const card = btn.closest("[data-line-id]");
      const isRegenerating = card && state.regeneratingLineId === card.dataset.lineId;
      btn.disabled = Boolean(isRegenerating) || isBusy || hasUnsaved;
    });
    const regenAllBtn = document.getElementById("regenerate-all-btn");
    if (regenAllBtn) regenAllBtn.disabled = isBusy || hasUnsaved;
    const nextBtn = document.getElementById("next-step-btn");
    if (nextBtn) nextBtn.disabled = state.saveStatus === "saving";
    const inspectorRegenerateBtn = document.querySelector('[data-inspector-action="regenerate"]');
    if (inspectorRegenerateBtn) inspectorRegenerateBtn.disabled = isBusy || hasUnsaved;
  }

  // The PUT /script response carries the server-assigned line ids (save_script always
  // reissues fresh ids — see app/services/script_service.py), which differ from whatever
  // ids state.lines/the DOM held before this save. Sync both so a later Regenerate on
  // this line targets an id that still exists in the database.
  function syncLineIdsFromServer(saved) {
    const cards = document.querySelectorAll("#script-list [data-line-id]");
    state.lines.forEach((line, index) => {
      const savedLine = saved[index];
      if (!savedLine || savedLine.id === line.id) return;
      line.id = savedLine.id;
      if (cards[index]) cards[index].dataset.lineId = savedLine.id;
    });
  }

  async function runAutosave() {
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      return;
    }
    setSaveStatusState("saving");
    clearError();
    try {
      const payload = state.lines.map((line) => ({
        speaker_id: line.speaker_id,
        text: line.text,
        language_notes: line.language_notes || { collocations: [], idioms: [], grammar_point: "" },
      }));
      const saved = await Api.saveScript(state.projectId, payload);
      syncLineIdsFromServer(saved);
      if (state.saveQueued) {
        state.saveQueued = false;
        setSaveStatusState("dirty");
        await runAutosave();
      } else {
        setSaveStatusState("saved");
      }
    } catch (err) {
      console.error("Failed to save script:", err);
      setSaveStatusState("failed");
      showError("We couldn't save your edit. Please check your connection and click Retry.");
    }
  }

  function autosave() {
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      return;
    }
    setSaveStatusState("dirty");
    runAutosave();
  }

  function startEdit(textEl) {
    const card = textEl.closest("[data-line-id]");
    const lineId = card.dataset.lineId;
    const line = state.lines.find((l) => l.id === lineId);
    if (!line) return;

    textEl.classList.add("editing");
    textEl.innerHTML = `<textarea>${escapeHtml(line.text)}</textarea>`;
    const textarea = textEl.querySelector("textarea");
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    function commit() {
      const newText = textarea.value.trim();
      textEl.classList.remove("editing");
      if (newText && newText !== line.text) {
        line.text = newText;
        renderScript();
        autosave();
      } else {
        renderScript();
      }
    }

    textarea.addEventListener("blur", commit);
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        textarea.blur();
      } else if (e.key === "Escape") {
        textarea.value = line.text;
        textarea.blur();
      }
    });
  }

  async function handleListen(lineId) {
    if (state.previewingLineId || state.isGenerating) return;
    state.previewingLineId = lineId;
    state.previewReadyLineId = null;
    clearError();
    renderInspector();
    let previewReady = false;
    try {
      await Api.previewTtsLine(state.projectId, lineId);
      state.previewingLineId = null;
      state.previewReadyLineId = lineId;
      renderInspector();
      const audio = document.getElementById("inspector-audio");
      if (audio) {
        audio.src = `${Api.ttsCacheUrl(state.projectId, lineId)}?t=${Date.now()}`;
        audio.hidden = false;
        await audio.play().catch(() => {});
      }
      previewReady = true;
    } catch (err) {
      console.error("Failed to synthesize script-line preview:", err);
      showError("We couldn't synthesize that line. Please try again.");
    } finally {
      if (!previewReady) {
        state.previewingLineId = null;
        renderInspector();
      }
    }
  }

  async function handleRegenerate(lineId) {
    if (state.regeneratingLineId || state.saveStatus !== "saved") {
      if (state.saveStatus !== "saved") {
        showError("Please save or resolve unsaved edits before regenerating a line.");
      }
      return;
    }
    state.regeneratingLineId = lineId;
    clearError();
    renderScript();

    try {
      const updated = await Api.regenerateLine(state.projectId, lineId);
      const index = state.lines.findIndex((l) => l.id === lineId);
      if (index !== -1) state.lines[index] = updated;
    } catch (err) {
      console.error("Failed to regenerate line:", err);
      showError("We couldn't regenerate this line. Please try again.");
    } finally {
      state.regeneratingLineId = null;
      renderScript();
    }
  }

  async function handleGenerate() {
    if (state.isGenerating || state.saveStatus !== "saved") {
      if (state.saveStatus !== "saved") {
        showError("Please save or resolve unsaved edits before generating a new script.");
      }
      return;
    }
    state.isGenerating = true;
    setGenerateLoading(true);
    clearError();
    document.getElementById("generate-panel").hidden = true;

    currentAiJob = makeScriptAiJob();
    await currentAiJob.start();
    watchScriptAiJob();
  }

  /** Resume-on-load (Task 13.6): reattach to an already-active job instead of
   * showing a false empty/idle state after a refresh or navigation. */
  async function resumeActiveScriptJob() {
    currentAiJob = makeScriptAiJob();
    const hasActive = await currentAiJob.resume();
    if (!hasActive) return;
    state.isGenerating = true;
    setGenerateLoading(true);
    document.getElementById("generate-panel").hidden = true;
    watchScriptAiJob();
  }

  function handleRegenerateAll() {
    if (state.isGenerating || state.saveStatus !== "saved") {
      if (state.saveStatus !== "saved") {
        showError("Please save or resolve unsaved edits before regenerating the script.");
      }
      return;
    }
    const confirmed = confirm(
      "This will overwrite the entire script with a brand new AI-generated version. Continue?"
    );
    if (confirmed) handleGenerate();
  }

  async function handleNextStep() {
    const nextBtn = document.getElementById("next-step-btn");

    if (state.saveStatus === "saving") {
      setSaveStatusState("saving", "Saving changes before proceeding…");
      if (nextBtn) nextBtn.disabled = true;
      const startTime = Date.now();
      while (state.saveStatus === "saving") {
        if (Date.now() - startTime > 10000) break; // 10s timeout
        await new Promise((r) => setTimeout(r, 50));
      }
    } else if (state.saveStatus === "dirty" || state.saveStatus === "failed" || state.saveQueued) {
      if (nextBtn) nextBtn.disabled = true;
      await runAutosave();
    }

    if (state.saveStatus === "saved") {
      window.location.href = `/step3?project_id=${encodeURIComponent(state.projectId)}`;
    } else {
      if (nextBtn) nextBtn.disabled = false;
      showError("Cannot proceed: Changes could not be saved. Please click Retry.");
    }
  }

  function handleScriptListClick(e) {
    const editTarget = e.target.closest("[data-action='edit-text']");
    if (editTarget && !editTarget.classList.contains("editing")) {
      const lineId = editTarget.closest("[data-line-id]").dataset.lineId;
      selectLine(lineId);
      const currentText = document.querySelector(`#script-list [data-line-id="${lineId}"] [data-action="edit-text"]`);
      if (currentText) startEdit(currentText);
      return;
    }
    const regenBtn = e.target.closest("[data-action='regenerate']");
    if (regenBtn && !regenBtn.disabled) {
      const card = regenBtn.closest("[data-line-id]");
      selectLine(card.dataset.lineId);
      handleRegenerate(card.dataset.lineId);
      return;
    }
    const card = e.target.closest("[data-line-id]");
    if (card) selectLine(card.dataset.lineId);
  }

  function handleInspectorClick(e) {
    const action = e.target.closest("[data-inspector-action]");
    if (!action || action.disabled) return;
    const line = selectedLine();
    if (!line) return;
    if (action.dataset.inspectorAction === "listen") handleListen(line.id);
    if (action.dataset.inspectorAction === "regenerate") handleRegenerate(line.id);
  }

  function handleTimelineClick(e) {
    const clip = e.target.closest("[data-line-id]");
    if (clip) selectLine(clip.dataset.lineId);
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.projectId = params.get("project_id");
    if (!state.projectId) {
      showMissingProjectError();
      return;
    }

    try {
      state.project = await Api.getProject(state.projectId);
    } catch (err) {
      console.error("Failed to load project:", err);
      showError("We couldn't load this project. Please go back to the Dashboard.");
      return;
    }

    renderHeader();
    checkOllamaHealthAndGate();
    document.getElementById("generate-btn").addEventListener("click", handleGenerate);
    document.getElementById("regenerate-all-btn").addEventListener("click", handleRegenerateAll);
    document.getElementById("next-step-btn").addEventListener("click", handleNextStep);
    document.getElementById("script-list").addEventListener("click", handleScriptListClick);

    try {
      state.lines = await Api.getScript(state.projectId);
      state.scriptLoadFailed = false;
    } catch (err) {
      console.error("Failed to load existing script:", err);
      state.scriptLoadFailed = true;
      showError("We couldn't load the existing script. Please try refreshing.");
    }
    await resumeActiveScriptJob();
    renderScript();
  }

  document.addEventListener("DOMContentLoaded", () => {
    StepNav.render("step-nav", { projectId: new URLSearchParams(window.location.search).get("project_id"), currentStep: 2, variant: "workflow" });
    KeyboardShortcuts.init({ primaryButtonId: "generate-btn" });
    saveIndicator = SaveIndicator.mount("save-indicator");
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    WorkspaceShell.init({
      sidebar: document.getElementById("pane-sidebar"),
      resizerLeft: document.getElementById("resizer-left"),
      inspector: document.getElementById("pane-inspector"),
      resizerRight: document.getElementById("resizer-right"),
      timeline: document.getElementById("pane-timeline"),
      resizerTop: document.getElementById("resizer-top"),
      collapseBtn: document.getElementById("sidebar-collapse-btn"),
    });
    document.getElementById("script-inspector").addEventListener("click", handleInspectorClick);
    document.getElementById("script-timeline").addEventListener("click", handleTimelineClick);
    window.addEventListener("beforeunload", (e) => {
      if (state.saveStatus !== "saved" || state.saveQueued) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
    init();
  });
})();
