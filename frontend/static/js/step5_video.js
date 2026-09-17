/**
 * Step 5 — Video Studio. Business rules stay on the backend; this file owns only UI
 * state and calls through Api (CR-05). Speakers can upload/remove a portrait image
 * (Task 1.7c) but nothing consumes it yet — no lip-sync controls, since LivePortrait
 * integration itself is still deferred (see task-1.7.md / task-1.7c.md).
 */
(() => {
  const TIMELINE_PIXELS_PER_SECOND = 16;
  const TIMELINE_MIN_CLIP_WIDTH_PX = 72;
  const TIMELINE_MAX_CLIP_WIDTH_PX = 240;

  const state = {
    projectId: null,
    project: null,
    templates: [],
    selectedTemplate: null,
    aspectRatio: "16:9",
    audioReady: false,
    audioJob: null,
    lines: [],
    selectedLineId: null,
    timelineError: "",
    isGenerating: false,
    avatarBusy: {},
  };

  const byId = (id) => document.getElementById(id);

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

  function speakerById(speakerId) {
    return (state.project?.speakers || []).find((speaker) => speaker.id === speakerId);
  }

  function selectedLine() {
    return state.lines.find((line) => line.id === state.selectedLineId) || null;
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

  function formatTime(seconds) {
    const wholeSeconds = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(wholeSeconds / 60);
    const remainingSeconds = String(wholeSeconds % 60).padStart(2, "0");
    return `${minutes}:${remainingSeconds}`;
  }

  function formatTiming(timing) {
    return `${formatTime(timing.start_sec)} – ${formatTime(timing.end_sec)}`;
  }

  function renderTimeline() {
    const scriptLane = byId("script-timeline");
    const voiceLane = byId("voice-timeline");
    const musicLane = byId("music-timeline");
    if (!scriptLane || !voiceLane || !musicLane) return;

    // Every lane is rebuilt from current state. Clearing all three first prevents
    // passive clips (especially Music) from accumulating across line selections.
    scriptLane.replaceChildren();
    voiceLane.replaceChildren();
    musicLane.replaceChildren();

    state.lines.forEach((line, index) => {
      const speaker = speakerById(line.speaker_id);
      const speakerName = speaker?.name || "Unknown speaker";
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

      const voiceClip = document.createElement("button");
      voiceClip.type = "button";
      voiceClip.className = `timeline-clip synced${activeClass}`;
      voiceClip.dataset.lineId = line.id;
      voiceClip.title = timing
        ? `${speakerName}: Synced · ${formatTiming(timing)}`
        : `${speakerName}: Synced · Timing unavailable`;
      voiceClip.textContent = `#${index + 1} · Synced`;
      applyMeasuredClipWidth(voiceClip, timing);
      voiceLane.appendChild(voiceClip);
    });

    if (state.lines.length === 0) {
      const message = state.timelineError || "No script lines available";
      [scriptLane, voiceLane].forEach((lane) => {
        const placeholder = document.createElement("span");
        placeholder.className = "timeline-clip timeline-placeholder";
        placeholder.textContent = message;
        lane.appendChild(placeholder);
      });
    }

    const music = state.audioJob?.background_music || "";
    const musicClip = document.createElement("span");
    musicClip.className = music
      ? "timeline-clip music-clip"
      : "timeline-clip timeline-placeholder";
    musicClip.textContent = music || "No music selected";
    musicLane.appendChild(musicClip);

    const timelineStatus = byId("timeline-status");
    if (timelineStatus) {
      timelineStatus.textContent = state.timelineError || "Measured audio timing";
    }
  }

  function renderInspector() {
    const container = byId("video-inspector");
    if (!container) return;
    const line = selectedLine();
    if (!line) {
      container.className = "inspector-empty";
      container.textContent = state.timelineError || "Select a script or voice clip to inspect its timing.";
      return;
    }

    const speaker = speakerById(line.speaker_id);
    const timing = timingForLine(line);
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
    statusBadge.textContent = "Synced";
    meta.append(speakerChip, statusBadge);

    const copy = document.createElement("p");
    copy.className = "inspector-copy";
    copy.textContent = line.text;

    const timingNote = document.createElement("div");
    timingNote.className = "callout";
    timingNote.dataset.timing = "";
    timingNote.textContent = timing
      ? `Measured audio timing: ${formatTiming(timing)}`
      : "Measured audio timing unavailable for this line.";

    container.className = "";
    container.replaceChildren(title, meta, copy, timingNote);
  }

  function selectLine(lineId) {
    if (!state.lines.some((line) => line.id === lineId)) return;
    if (state.selectedLineId === lineId) return;
    state.selectedLineId = lineId;
    renderTimeline();
    renderInspector();
  }

  function handleTimelineClick(event) {
    const clip = event.target.closest("[data-line-id]");
    if (clip) selectLine(clip.dataset.lineId);
  }

  function renderAvatars() {
    const grid = byId("avatar-grid");
    grid.replaceChildren();
    (state.project.speakers || []).forEach((speaker) => {
      const card = document.createElement("div");
      card.className = "card avatar-card";

      const preview = speaker.avatar_image_path
        ? Object.assign(document.createElement("img"), {
            className: "avatar-preview",
            src: `${speaker.avatar_image_path}?t=${Date.now()}`,
            alt: `${speaker.name}'s avatar`,
          })
        : Object.assign(document.createElement("div"), {
            className: "avatar-placeholder",
            textContent: "No image",
          });

      const name = document.createElement("div");
      name.className = "avatar-name";
      name.textContent = speaker.name;

      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = "image/png,image/jpeg";
      fileInput.id = `avatar-file-${speaker.id}`;

      const uploadLabel = document.createElement("label");
      uploadLabel.className = "btn btn-ghost btn-sm";
      uploadLabel.htmlFor = fileInput.id;
      uploadLabel.textContent = speaker.avatar_image_path ? "Replace" : "Upload";

      const status = document.createElement("div");
      status.className = "avatar-status";

      const busy = Boolean(state.avatarBusy[speaker.id]);
      fileInput.disabled = busy;
      status.textContent = busy ? "Saving…" : "";

      fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (file) uploadAvatar(speaker.id, file);
      });

      const actions = document.createElement("div");
      actions.className = "avatar-actions";
      actions.append(uploadLabel, fileInput);

      // Not `.hidden` on a `.btn`-classed element: this app's stylesheet has no
      // `[hidden]` rule, so `.btn { display: inline-flex }` would keep it visible.
      if (speaker.avatar_image_path) {
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "btn btn-ghost btn-sm";
        removeButton.textContent = "Remove";
        removeButton.disabled = busy;
        removeButton.addEventListener("click", () => removeAvatar(speaker.id));
        actions.append(removeButton);
      }

      card.append(preview, name, actions, status);
      grid.appendChild(card);
    });
  }

  async function uploadAvatar(speakerId, file) {
    state.avatarBusy[speakerId] = true;
    renderAvatars();
    try {
      state.project = await Api.uploadSpeakerAvatar(state.projectId, speakerId, file);
    } catch (error) {
      console.error("Failed to upload avatar:", error);
      showError("We couldn't upload that image. Please try a PNG or JPEG under 8 MB.");
    } finally {
      delete state.avatarBusy[speakerId];
      renderAvatars();
    }
  }

  async function removeAvatar(speakerId) {
    state.avatarBusy[speakerId] = true;
    renderAvatars();
    try {
      state.project = await Api.deleteSpeakerAvatar(state.projectId, speakerId);
    } catch (error) {
      console.error("Failed to remove avatar:", error);
      showError("We couldn't remove that image. Please try again.");
    } finally {
      delete state.avatarBusy[speakerId];
      renderAvatars();
    }
  }

  function renderTemplates() {
    const grid = byId("template-grid");
    grid.replaceChildren();
    state.templates.forEach((template) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "card template-option";
      button.classList.toggle("selected", template.id === state.selectedTemplate);
      button.dataset.templateId = template.id;
      const image = document.createElement("img");
      image.src = template.preview_url;
      image.alt = `${template.display_name} background preview`;
      image.loading = "lazy";
      const name = document.createElement("span");
      name.className = "template-name";
      name.textContent = template.display_name;
      button.append(image, name);
      button.addEventListener("click", () => {
        if (state.isGenerating) return;
        state.selectedTemplate = template.id;
        renderTemplates();
      });
      grid.appendChild(button);
    });
  }

  function applyLocks() {
    byId("generate-btn").disabled = state.isGenerating || !state.audioReady || !state.selectedTemplate;
    document.querySelectorAll(".template-option").forEach((button) => {
      button.disabled = state.isGenerating;
    });
    document.querySelectorAll("#aspect-ratio-group .chip").forEach((button) => {
      button.disabled = state.isGenerating;
    });
  }

  function setupAspectRatioToggle() {
    const group = byId("aspect-ratio-group");
    group.querySelectorAll(".chip").forEach((button) => {
      button.addEventListener("click", () => {
        if (state.isGenerating) return;
        state.aspectRatio = button.dataset.aspectRatio;
        group.querySelectorAll(".chip").forEach((candidate) => {
          candidate.setAttribute("aria-pressed", String(candidate === button));
        });
      });
    });
  }

  function setGenerateLoading(loading) {
    const button = byId("generate-btn");
    button.textContent = "";
    if (loading) {
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      button.append(spinner, document.createTextNode(" Rendering…"));
    } else {
      button.textContent = "🎬 Generate video";
    }
    applyLocks();
  }

  function renderResult(job) {
    byId("result-card").hidden = false;
    byId("no-result-yet").hidden = true;
    const cacheBust = Date.now();
    byId("result-player").src = `${Api.videoDownloadUrl(state.projectId, "mp4")}&t=${cacheBust}`;
    byId("download-mp4").href = `${Api.videoDownloadUrl(state.projectId, "mp4")}&t=${cacheBust}`;
    byId("download-srt").href = `${Api.videoDownloadUrl(state.projectId, "srt")}&t=${cacheBust}`;
    byId("download-mp4").download = `${state.projectId}.mp4`;
    byId("download-srt").download = `${state.projectId}.srt`;

    const verticalLink = byId("download-mp4-vertical");
    if (job.mp4_path_vertical) {
      verticalLink.href = `${Api.videoDownloadUrl(state.projectId, "mp4_vertical")}&t=${cacheBust}`;
      verticalLink.download = `${state.projectId}_vertical.mp4`;
      verticalLink.hidden = false;
    } else {
      verticalLink.hidden = true;
    }
  }

  async function generateVideo() {
    if (state.isGenerating || !state.audioReady || !state.selectedTemplate) return;
    state.isGenerating = true;
    clearError();
    setGenerateLoading(true);
    byId("generate-progress").textContent = "Rendering with ffmpeg…";
    try {
      const job = await Api.generateVideo(state.projectId, state.selectedTemplate, state.aspectRatio);
      renderResult(job);
      byId("generate-progress").textContent = "Done.";
    } catch (error) {
      console.error("Failed to generate video:", error);
      showError("We couldn't generate the video. Please try again.");
      byId("generate-progress").textContent = "";
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
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
    const backHref = `/step4?project_id=${encodeURIComponent(state.projectId)}`;
    byId("back-link").href = backHref;
    byId("empty-state-link").href = backHref;

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
      state.audioJob = await Api.getAudioStatus(state.projectId);
      state.audioReady = state.audioJob.status === "complete";
    } catch (error) {
      state.audioJob = null;
      state.audioReady = false; // 404 (no audio yet) is expected, not an error to surface
    }

    if (!state.audioReady) {
      byId("loading-panel").hidden = true;
      byId("empty-state").hidden = false;
      renderTimeline();
      renderInspector();
      return;
    }

    try {
      state.lines = await Api.getScript(state.projectId);
      state.selectedLineId = state.lines[0]?.id || null;
    } catch (error) {
      console.error("Failed to load script for the video timeline (non-fatal):", error);
      state.lines = [];
      state.selectedLineId = null;
      state.timelineError = "Script unavailable — video tools are still ready";
    }

    try {
      state.templates = await Api.listVideoTemplates();
      state.selectedTemplate = state.templates[0]?.id || null;
    } catch (error) {
      console.error("Failed to load video templates:", error);
      byId("loading-panel").hidden = true;
      showError("We couldn't load the background templates. Please refresh.");
      return;
    }

    try {
      const job = await Api.getVideoStatus(state.projectId);
      if (job && job.status === "complete") renderResult(job);
    } catch (error) {
      if (error.status !== 404) console.error("Failed to load existing video job:", error);
    }

    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
    renderAvatars();
    renderTemplates();
    renderTimeline();
    renderInspector();
    setupAspectRatioToggle();
    applyLocks();
  }

  document.addEventListener("DOMContentLoaded", () => {
    StepNav.render("step-nav", {
      projectId: new URLSearchParams(window.location.search).get("project_id"),
      currentStep: 5,
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
    byId("script-timeline").addEventListener("click", handleTimelineClick);
    byId("voice-timeline").addEventListener("click", handleTimelineClick);
    byId("generate-btn").addEventListener("click", generateVideo);
    window.addEventListener("beforeunload", (event) => {
      if (state.isGenerating) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    init();
  });
})();
