/**
 * Step 4 — TTS Audio Studio. Business rules stay on the backend; this file owns only
 * UI state, serialized saves, and calls through Api (CR-05).
 *
 * "Generate All" orchestrates two separate backend steps because AudioService only mixes
 * already-synthesized lines (see app/services/audio_service.py): synthesize every line
 * sequentially, then mix. Sequential (not parallel) is deliberate — matches this task's
 * Forbidden Scope "No VRAM exhaustion without fallback" and avoids hammering the free
 * Edge TTS endpoint.
 */
(() => {
  const SAVE_DEBOUNCE_MS = 400;
  const TIMELINE_PIXELS_PER_SECOND = 16;
  const TIMELINE_MIN_CLIP_WIDTH_PX = 72;
  const TIMELINE_MAX_CLIP_WIDTH_PX = 240;

  const state = {
    projectId: null,
    project: null,
    lines: [],
    musicTracks: [],
    selectedMusic: "",
    audioJob: null,
    isGenerating: false,
    linesInFlight: new Set(),
    previewedLineIds: new Set(),
    selectedLineId: null,
    speakerSave: {}, // speakerId -> { status, timer, queued, draft }
  };

  const byId = (id) => document.getElementById(id);
  const speakerById = (id) => (state.project?.speakers || []).find((s) => s.id === id);
  const selectedLine = () => state.lines.find((line) => line.id === state.selectedLineId) || null;

  function previewState(lineId) {
    if (state.linesInFlight.has(lineId)) return { key: "synthesizing", label: "Synthesizing" };
    if (state.previewedLineIds.has(lineId)) return { key: "preview-ready", label: "Preview ready" };
    return { key: "not-previewed", label: "Not previewed" };
  }

  function timingForLine(line) {
    const index = state.lines.indexOf(line);
    const timing = state.audioJob?.timestamps?.[index];
    if (!timing || !Number.isFinite(timing.start_sec) || !Number.isFinite(timing.end_sec)) {
      return null;
    }
    return timing;
  }

  function measuredClipWidth(timing) {
    if (!timing) return null;
    const duration = timing.end_sec - timing.start_sec;
    if (!Number.isFinite(duration) || duration <= 0) return null;
    return Math.min(
      TIMELINE_MAX_CLIP_WIDTH_PX,
      Math.max(TIMELINE_MIN_CLIP_WIDTH_PX, duration * TIMELINE_PIXELS_PER_SECOND)
    );
  }

  function applyMeasuredClipWidth(clip, timing) {
    const width = measuredClipWidth(timing);
    if (width !== null) clip.style.width = `${width}px`;
  }

  function showError(message) {
    const banner = byId("error-banner");
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function showMissingProjectError() {
    const banner = byId("error-banner");
    banner.innerHTML = 'Missing project. <a href="/">← Go to Dashboard</a>';
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearError() {
    const banner = byId("error-banner");
    banner.textContent = "";
    banner.hidden = true;
  }

  function anySpeakerUnresolved() {
    return Object.values(state.speakerSave).some((s) => s.status === "saving" || s.status === "dirty" || s.queued);
  }

  function renderHeader() {
    byId("project-name").textContent = state.project.name;
    const badges = byId("project-badges");
    badges.replaceChildren();
    [state.project.cefr_level, state.project.genre].filter(Boolean).forEach((label) => {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = label;
      badges.appendChild(badge);
    });
  }

  function applyLocks() {
    byId("generate-btn").disabled = state.isGenerating || state.lines.length === 0;
    byId("music-select").disabled = state.isGenerating;
    document.querySelectorAll(".speaker-card select, .speaker-card input").forEach((el) => {
      el.disabled = state.isGenerating;
    });
    document.querySelectorAll(".preview-btn").forEach((button) => {
      button.disabled = state.isGenerating || state.linesInFlight.has(button.dataset.lineId);
    });
  }

  function setSpeakerStatus(speakerId, status, message = null) {
    const entry = state.speakerSave[speakerId];
    entry.status = status;
    const el = document.querySelector(`.speaker-save-status[data-speaker-id="${speakerId}"]`);
    if (!el) return;
    const labels = {
      saved: "",
      dirty: "Unsaved changes…",
      saving: entry.queued ? "Saving… newer changes queued" : "Saving…",
      failed: "Save failed — will retry on next change",
    };
    el.textContent = message || labels[status];
  }

  function renderSpeakers() {
    const grid = byId("speaker-grid");
    grid.replaceChildren();
    state.project.speakers.forEach((speaker) => {
      if (!state.speakerSave[speaker.id]) {
        state.speakerSave[speaker.id] = { status: "saved", timer: null, queued: false, draft: null };
      }

      const card = document.createElement("div");
      card.className = "card speaker-card";
      card.dataset.speakerId = speaker.id;
      card.tabIndex = -1;

      const nameRow = document.createElement("div");
      nameRow.className = "speaker-name";
      nameRow.textContent = speaker.name;
      const meta = document.createElement("p");
      meta.className = "speaker-meta";
      meta.textContent = `${speaker.gender} · ${speaker.accent}`;

      card.append(nameRow, meta);
      card.appendChild(buildSlider(speaker, "speed", "Speed", 0.75, 1.5, 0.05));
      card.appendChild(buildSlider(speaker, "pitch", "Pitch", -1, 1, 0.1));
      card.appendChild(buildSlider(speaker, "volume", "Volume", 0, 2, 0.1));

      const status = document.createElement("div");
      status.className = "speaker-save-status";
      status.dataset.speakerId = speaker.id;
      card.appendChild(status);

      grid.appendChild(card);
    });
  }

  function buildSlider(speaker, field, label, min, max, step) {
    const wrap = document.createElement("div");
    const fieldLabel = document.createElement("label");
    fieldLabel.className = "field-label";
    fieldLabel.textContent = label;
    const row = document.createElement("div");
    row.className = "slider-row";
    const input = document.createElement("input");
    input.type = "range";
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    input.value = String(speaker[field]);
    input.dataset.speakerId = speaker.id;
    input.dataset.field = field;
    const value = document.createElement("span");
    value.className = "slider-value";
    value.textContent = Number(speaker[field]).toFixed(2);
    input.addEventListener("input", () => {
      value.textContent = Number(input.value).toFixed(2);
    });
    row.append(input, value);
    wrap.append(fieldLabel, row);
    return wrap;
  }

  function scheduleSpeakerSave(speakerId, field, rawValue) {
    const entry = state.speakerSave[speakerId];
    // Speed/pitch/volume are the only editable speaker fields now that TTS engine
    // choice was removed (Edge TTS is the sole official engine) — all numeric.
    const value = Number(rawValue);
    entry.draft = { ...(entry.draft || {}), [field]: value };

    if (entry.timer) clearTimeout(entry.timer);
    if (entry.status === "saving") {
      entry.queued = true;
      setSpeakerStatus(speakerId, "saving");
      return;
    }
    setSpeakerStatus(speakerId, "dirty");
    entry.timer = setTimeout(() => {
      entry.timer = null;
      saveSpeaker(speakerId);
    }, SAVE_DEBOUNCE_MS);
  }

  async function saveSpeaker(speakerId) {
    const entry = state.speakerSave[speakerId];
    if (!entry.draft) return;
    if (entry.status === "saving") {
      entry.queued = true;
      return;
    }
    const payload = entry.draft;
    entry.draft = null;
    entry.queued = false;
    setSpeakerStatus(speakerId, "saving");
    try {
      const updated = await Api.updateSpeaker(state.projectId, speakerId, payload);
      state.project = updated;
      if (entry.queued) {
        setSpeakerStatus(speakerId, "dirty");
        await saveSpeaker(speakerId);
      } else {
        setSpeakerStatus(speakerId, "saved");
      }
    } catch (error) {
      console.error("Failed to save speaker settings:", error);
      entry.queued = false;
      setSpeakerStatus(speakerId, "failed");
      showError("We couldn't save that speaker's voice settings. Adjust it again to retry.");
    }
  }

  function renderLines() {
    const list = byId("line-list");
    list.replaceChildren();
    state.lines.forEach((line) => {
      const card = document.createElement("div");
      card.className = `card line-card${line.id === state.selectedLineId ? " selected" : ""}`;
      card.dataset.lineId = line.id;

      const speakerLabel = document.createElement("div");
      speakerLabel.className = "line-speaker";
      speakerLabel.textContent = speakerById(line.speaker_id)?.name || "Unknown";

      const body = document.createElement("div");
      body.className = "line-body";
      const text = document.createElement("p");
      text.className = "line-text";
      text.textContent = line.text;

      const controls = document.createElement("div");
      controls.className = "line-controls";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-ghost btn-sm preview-btn";
      button.textContent = "▶ Preview";
      button.dataset.lineId = line.id;
      const audio = document.createElement("audio");
      audio.className = "line-audio";
      audio.controls = true;
      audio.hidden = true;
      audio.dataset.lineId = line.id;

      button.addEventListener("click", () => {
        selectLine(line.id);
        previewLine(line.id, button, audio);
      });
      card.addEventListener("click", () => selectLine(line.id));
      controls.append(button, audio);
      body.append(text, controls);
      card.append(speakerLabel, body);
      list.appendChild(card);
    });
  }

  function renderTimeline() {
    const scriptLane = byId("script-timeline");
    const voiceLane = byId("voice-timeline");
    const musicLane = byId("music-timeline");
    if (!scriptLane || !voiceLane || !musicLane) return;

    scriptLane.replaceChildren();
    voiceLane.replaceChildren();
    state.lines.forEach((line, index) => {
      const speaker = speakerById(line.speaker_id);
      const speakerName = speaker?.name || "Unknown";
      const speakerIndex = Math.max(
        0,
        (state.project?.speakers || []).findIndex((candidate) => candidate.id === line.speaker_id)
      );
      const activeClass = line.id === state.selectedLineId ? " active" : "";
      const speakerClass = speakerIndex % 2 === 0 ? " speaker-a" : "";
      const timing = timingForLine(line);

      const scriptClip = document.createElement("button");
      scriptClip.type = "button";
      scriptClip.className = `timeline-clip${speakerClass}${activeClass}`;
      scriptClip.dataset.lineId = line.id;
      scriptClip.title = line.text;
      scriptClip.textContent = `${speakerName} #${index + 1}`;
      applyMeasuredClipWidth(scriptClip, timing);
      scriptLane.appendChild(scriptClip);

      const status = previewState(line.id);
      const voiceClip = document.createElement("button");
      voiceClip.type = "button";
      voiceClip.className = `timeline-clip ${status.key}${activeClass}`;
      voiceClip.dataset.lineId = line.id;
      voiceClip.dataset.previewState = status.key;
      voiceClip.title = `${speakerName}: ${status.label}`;
      voiceClip.textContent = `#${index + 1} · ${status.label}`;
      applyMeasuredClipWidth(voiceClip, timing);
      voiceLane.appendChild(voiceClip);
    });

    musicLane.replaceChildren();
    const musicClip = document.createElement("span");
    musicClip.className = state.selectedMusic
      ? "timeline-clip music-clip"
      : "timeline-clip timeline-placeholder";
    musicClip.textContent = state.selectedMusic || "No music selected";
    musicLane.appendChild(musicClip);
  }

  function renderInspector() {
    const container = byId("tts-inspector");
    if (!container) return;
    const line = selectedLine();
    if (!line) {
      container.className = "inspector-empty";
      container.textContent = "Select a script or voice clip to inspect it.";
      return;
    }

    const speaker = speakerById(line.speaker_id);
    const status = previewState(line.id);
    const title = document.createElement("h2");
    title.className = "inspector-title";
    title.textContent = `Line ${state.lines.indexOf(line) + 1}`;

    const meta = document.createElement("div");
    meta.className = "inspector-meta";
    const speakerChip = document.createElement("span");
    speakerChip.className = "speaker-chip";
    speakerChip.textContent = speaker?.name || "Unknown speaker";
    const statusBadge = document.createElement("span");
    statusBadge.className = "badge";
    statusBadge.dataset.previewStatus = "";
    statusBadge.textContent = status.label;
    meta.append(speakerChip, statusBadge);

    const copy = document.createElement("p");
    copy.className = "inspector-copy";
    copy.textContent = line.text;

    const note = document.createElement("div");
    note.className = "callout";
    note.textContent = "Preview status reflects successful synthesis in this browser session only.";

    const actions = document.createElement("div");
    actions.className = "inspector-actions";
    const listen = document.createElement("button");
    listen.type = "button";
    listen.className = "btn btn-ghost preview-btn";
    listen.dataset.inspectorAction = "listen";
    listen.dataset.lineId = line.id;
    listen.disabled = state.isGenerating || state.linesInFlight.has(line.id);
    listen.textContent = state.linesInFlight.has(line.id) ? "Synthesizing…" : "🔊 Listen";
    const settings = document.createElement("button");
    settings.type = "button";
    settings.className = "btn btn-primary";
    settings.dataset.inspectorAction = "voice-settings";
    settings.textContent = "Voice settings";
    actions.append(listen, settings);

    const audio = document.createElement("audio");
    audio.id = "inspector-audio";
    audio.className = "inspector-audio";
    audio.controls = true;
    audio.hidden = true;

    container.className = "";
    container.replaceChildren(title, meta, copy, note, actions, audio);
  }

  function updateInspectorPreviewState() {
    const line = selectedLine();
    if (!line) return;
    const status = previewState(line.id);
    const badge = byId("tts-inspector")?.querySelector("[data-preview-status]");
    if (badge) badge.textContent = status.label;
    const listen = byId("tts-inspector")?.querySelector('[data-inspector-action="listen"]');
    if (listen) {
      listen.disabled = state.isGenerating || state.linesInFlight.has(line.id);
      listen.textContent = state.linesInFlight.has(line.id) ? "Synthesizing…" : "🔊 Listen";
    }
  }

  function selectLine(lineId) {
    if (!state.lines.some((line) => line.id === lineId)) return;
    if (state.selectedLineId === lineId) return;
    state.selectedLineId = lineId;
    document.querySelectorAll("#line-list .line-card[data-line-id]").forEach((card) => {
      card.classList.toggle("selected", card.dataset.lineId === lineId);
    });
    renderTimeline();
    renderInspector();
  }

  async function previewLine(lineId, button, audio) {
    if (state.linesInFlight.has(lineId) || state.isGenerating) return;
    state.linesInFlight.add(lineId);
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "Synthesizing…";
    clearError();
    applyLocks();
    renderTimeline();
    updateInspectorPreviewState();
    try {
      await Api.previewTtsLine(state.projectId, lineId);
      audio.src = `${Api.ttsCacheUrl(state.projectId, lineId)}?t=${Date.now()}`;
      audio.hidden = false;
      await audio.play().catch(() => {});
      state.previewedLineIds.add(lineId);
    } catch (error) {
      console.error("Failed to synthesize line preview:", error);
      showError("We couldn't synthesize that line. Please try again.");
    } finally {
      state.linesInFlight.delete(lineId);
      button.disabled = state.isGenerating;
      button.textContent = originalText;
      applyLocks();
      renderTimeline();
      updateInspectorPreviewState();
    }
  }

  function handleInspectorClick(event) {
    const action = event.target.closest("[data-inspector-action]");
    if (!action || action.disabled) return;
    const line = selectedLine();
    if (!line) return;
    if (action.dataset.inspectorAction === "listen") {
      const audio = byId("inspector-audio");
      previewLine(line.id, action, audio);
      return;
    }
    if (action.dataset.inspectorAction === "voice-settings") {
      const card = [...document.querySelectorAll("#speaker-grid [data-speaker-id]")].find(
        (candidate) => candidate.dataset.speakerId === line.speaker_id
      );
      if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.focus({ preventScroll: true });
      }
    }
  }

  function handleTimelineClick(event) {
    const clip = event.target.closest("[data-line-id]");
    if (clip) selectLine(clip.dataset.lineId);
  }

  function renderMusicOptions() {
    const select = byId("music-select");
    state.musicTracks.forEach((track) => {
      const option = document.createElement("option");
      option.value = track.filename;
      option.textContent = track.filename;
      select.appendChild(option);
    });
  }

  function renderResult(job) {
    const card = byId("result-card");
    card.hidden = false;
    const cacheBust = Date.now();
    byId("result-player").src = `${Api.audioDownloadUrl(state.projectId, "mp3")}&t=${cacheBust}`;
    byId("download-mp3").href = `${Api.audioDownloadUrl(state.projectId, "mp3")}&t=${cacheBust}`;
    byId("download-wav").href = `${Api.audioDownloadUrl(state.projectId, "wav")}&t=${cacheBust}`;
    byId("download-mp3").download = `${state.projectId}.mp3`;
    byId("download-wav").download = `${state.projectId}.wav`;
  }

  async function generateAll() {
    if (state.isGenerating || state.lines.length === 0) return;
    state.isGenerating = true;
    clearError();
    applyLocks();
    updateInspectorPreviewState();
    const progress = byId("generate-progress");
    let activeLineId = null;
    try {
      for (let i = 0; i < state.lines.length; i += 1) {
        progress.textContent = `Synthesizing line ${i + 1}/${state.lines.length}…`;
        activeLineId = state.lines[i].id;
        state.linesInFlight.add(activeLineId);
        renderTimeline();
        updateInspectorPreviewState();
        await Api.previewTtsLine(state.projectId, activeLineId);
        state.linesInFlight.delete(activeLineId);
        state.previewedLineIds.add(activeLineId);
        activeLineId = null;
        renderTimeline();
        updateInspectorPreviewState();
      }
      progress.textContent = "Mixing final audio…";
      const job = await Api.generateAudio(state.projectId, state.selectedMusic);
      state.audioJob = job;
      renderResult(job);
      progress.textContent = "Done — episode ready below.";
    } catch (error) {
      console.error("Failed to generate audio:", error);
      showError("We couldn't generate the full episode. Please try again.");
      progress.textContent = "";
    } finally {
      if (activeLineId) state.linesInFlight.delete(activeLineId);
      state.isGenerating = false;
      applyLocks();
      renderTimeline();
      updateInspectorPreviewState();
    }
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.projectId = params.get("project_id");
    if (!state.projectId) {
      byId("loading-panel").hidden = true;
      showMissingProjectError();
      return;
    }
    byId("back-link").href = `/step3?project_id=${encodeURIComponent(state.projectId)}`;
    byId("next-step-link").href = `/step5?project_id=${encodeURIComponent(state.projectId)}`;

    try {
      state.project = await Api.getProject(state.projectId);
      renderHeader();
    } catch (error) {
      console.error("Failed to load project:", error);
      byId("loading-panel").hidden = true;
      showError("We couldn't load this project. Please return to the Dashboard.");
      return;
    }

    try {
      state.lines = await Api.getScript(state.projectId);
      state.selectedLineId = state.lines[0]?.id || null;
    } catch (error) {
      console.error("Failed to load script:", error);
      byId("loading-panel").hidden = true;
      showError("We couldn't load the script for this project.");
      renderTimeline();
      renderInspector();
      return;
    }

    if (state.lines.length === 0) {
      byId("loading-panel").hidden = true;
      byId("empty-state").hidden = false;
      renderTimeline();
      renderInspector();
      return;
    }

    try {
      state.musicTracks = await Api.listMusic();
    } catch (error) {
      console.error("Failed to load music library (non-fatal):", error);
      state.musicTracks = [];
    }

    try {
      const job = await Api.getAudioStatus(state.projectId);
      state.audioJob = job;
      if (job && job.status === "complete") renderResult(job);
    } catch (error) {
      state.audioJob = null;
      if (error.status !== 404) console.error("Failed to load existing audio job:", error);
    }

    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
    renderSpeakers();
    renderLines();
    renderMusicOptions();
    renderTimeline();
    renderInspector();
    applyLocks();
  }

  document.addEventListener("DOMContentLoaded", () => {
    StepNav.render("step-nav", {
      projectId: new URLSearchParams(window.location.search).get("project_id"),
      currentStep: 4,
      variant: "workflow",
    });
    KeyboardShortcuts.init({ primaryButtonId: "generate-btn" });
    byId("theme-toggle").addEventListener("click", Theme.toggle);
    WorkspaceShell.init({
      sidebar: byId("pane-sidebar"),
      resizerLeft: byId("resizer-left"),
      inspector: byId("pane-inspector"),
      resizerRight: byId("resizer-right"),
      timeline: byId("pane-timeline"),
      resizerTop: byId("resizer-top"),
      collapseBtn: byId("sidebar-collapse-btn"),
    });
    byId("tts-inspector").addEventListener("click", handleInspectorClick);
    byId("script-timeline").addEventListener("click", handleTimelineClick);
    byId("voice-timeline").addEventListener("click", handleTimelineClick);
    byId("generate-btn").addEventListener("click", generateAll);
    byId("music-select").addEventListener("change", (event) => {
      state.selectedMusic = event.target.value;
      renderTimeline();
    });
    const handleSpeakerFieldChange = (event) => {
      const field = event.target.dataset.field;
      const speakerId = event.target.dataset.speakerId;
      if (!field || !speakerId) return;
      scheduleSpeakerSave(speakerId, field, event.target.value);
    };
    // `input` covers range sliders (live drag) and modern browsers' <select>; `change` is
    // the reliable cross-browser event for <select> — both call the same handler, and a
    // slider's own `input` firing twice for the same value is harmless (scheduleSpeakerSave
    // just re-debounces).
    byId("speaker-grid").addEventListener("input", handleSpeakerFieldChange);
    byId("speaker-grid").addEventListener("change", handleSpeakerFieldChange);
    window.addEventListener("beforeunload", (event) => {
      if (state.isGenerating || anySpeakerUnresolved()) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    init();
  });
})();
