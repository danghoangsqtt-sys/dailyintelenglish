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
  const ENGINE_OPTIONS = [
    { value: "omnivoice", label: "OmniVoice (falls back to Edge TTS)" },
    { value: "edge_tts", label: "Edge TTS" },
  ];

  const state = {
    projectId: null,
    project: null,
    lines: [],
    musicTracks: [],
    selectedMusic: "",
    isGenerating: false,
    linesInFlight: new Set(),
    speakerSave: {}, // speakerId -> { status, timer, queued, draft }
  };

  const byId = (id) => document.getElementById(id);
  const speakerById = (id) => (state.project?.speakers || []).find((s) => s.id === id);

  function showError(message) {
    const banner = byId("error-banner");
    banner.textContent = message;
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

      const nameRow = document.createElement("div");
      nameRow.className = "speaker-name";
      nameRow.textContent = speaker.name;
      const meta = document.createElement("p");
      meta.className = "speaker-meta";
      meta.textContent = `${speaker.gender} · ${speaker.accent}`;

      const engineLabel = document.createElement("label");
      engineLabel.className = "field-label";
      engineLabel.textContent = "TTS engine";
      const engineSelect = document.createElement("select");
      engineSelect.dataset.speakerId = speaker.id;
      engineSelect.dataset.field = "tts_engine";
      ENGINE_OPTIONS.forEach((option) => {
        const opt = document.createElement("option");
        opt.value = option.value;
        opt.textContent = option.label;
        opt.selected = option.value === speaker.tts_engine;
        engineSelect.appendChild(opt);
      });

      card.append(nameRow, meta, engineLabel, engineSelect);
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
    const value = field === "tts_engine" ? rawValue : Number(rawValue);
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
      card.className = "card line-card";

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

      button.addEventListener("click", () => previewLine(line.id, button, audio));
      controls.append(button, audio);
      body.append(text, controls);
      card.append(speakerLabel, body);
      list.appendChild(card);
    });
  }

  async function previewLine(lineId, button, audio) {
    if (state.linesInFlight.has(lineId) || state.isGenerating) return;
    state.linesInFlight.add(lineId);
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "Synthesizing…";
    clearError();
    try {
      await Api.previewTtsLine(state.projectId, lineId);
      audio.src = `${Api.ttsCacheUrl(state.projectId, lineId)}?t=${Date.now()}`;
      audio.hidden = false;
      await audio.play().catch(() => {});
    } catch (error) {
      console.error("Failed to synthesize line preview:", error);
      showError("We couldn't synthesize that line. Please try again.");
    } finally {
      state.linesInFlight.delete(lineId);
      button.disabled = state.isGenerating;
      button.textContent = originalText;
    }
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
    const progress = byId("generate-progress");
    try {
      for (let i = 0; i < state.lines.length; i += 1) {
        progress.textContent = `Synthesizing line ${i + 1}/${state.lines.length}…`;
        await Api.previewTtsLine(state.projectId, state.lines[i].id);
      }
      progress.textContent = "Mixing final audio…";
      const job = await Api.generateAudio(state.projectId, state.selectedMusic);
      renderResult(job);
      progress.textContent = "Done — episode ready below.";
    } catch (error) {
      console.error("Failed to generate audio:", error);
      showError("We couldn't generate the full episode. Please try again.");
      progress.textContent = "";
    } finally {
      state.isGenerating = false;
      applyLocks();
    }
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.projectId = params.get("project_id");
    if (!state.projectId) {
      byId("loading-panel").hidden = true;
      showError("Missing project. Please start from the Dashboard.");
      return;
    }
    byId("back-link").href = `/step3?project_id=${encodeURIComponent(state.projectId)}`;

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
    } catch (error) {
      console.error("Failed to load script:", error);
      byId("loading-panel").hidden = true;
      showError("We couldn't load the script for this project.");
      return;
    }

    if (state.lines.length === 0) {
      byId("loading-panel").hidden = true;
      byId("empty-state").hidden = false;
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
      if (job && job.status === "complete") renderResult(job);
    } catch (error) {
      if (error.status !== 404) console.error("Failed to load existing audio job:", error);
    }

    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
    renderSpeakers();
    renderLines();
    renderMusicOptions();
    applyLocks();
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("theme-toggle").addEventListener("click", Theme.toggle);
    byId("generate-btn").addEventListener("click", generateAll);
    byId("music-select").addEventListener("change", (event) => {
      state.selectedMusic = event.target.value;
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
