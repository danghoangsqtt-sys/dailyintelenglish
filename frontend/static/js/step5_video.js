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

  // Report-UX-1: real ffmpeg render measurement (docs/operations/phase19-spike-remotion.md
  // and AudioService timing history) -- render is well under a second, so no ETA string
  // (showEta: false below) is shown, only the elapsed counter as the honest "something is
  // happening" signal.
  const VIDEO_BASELINE_SECONDS = 1;

  // Task 19.7 (D19.7-f): real finding -- no existing localStorage precedent lives in this
  // file (the card's claimed "subtitle-style picker etc." doesn't exist); following
  // theme.js's real, confirmed "die-<name>" convention instead.
  const RENDERER_STORAGE_KEY = "die-video-renderer";

  // Task 19.7.n1: owner feedback (Gate B-12 live test, 2026-09-29) -- the old one-line
  // tooltip didn't say what "Enhanced" actually adds. Single source of truth for both
  // strings, per the card's own recommendation. "About 9x" (not the card draft's "about
  // 3x" -- corrected against real measured data: Task 19.7's own live verification was
  // 70.6s Remotion vs 7.76s ffmpeg on the same b330d37f... episode, ~9.1x; Gate B-12's
  // cited 62s vs 7s is ~8.9x -- both real data points land near 9x, not 3x).
  const RENDERER_ENABLED_TOOLTIP =
    "Enhanced (Remotion): word-by-word karaoke highlight, speaker name chip, vocabulary " +
    "pop-up cards, intro title + outro CTA, chapter progress bar. Higher-quality YouTube " +
    "output. Slower render than Standard (about 9× wall time).";
  const RENDERER_DISABLED_TOOLTIP =
    "Enhanced rendering requires Node.js and Chrome Headless Shell. Not installed on this " +
    "machine — see scripts/check_dependencies.py. Standard (ffmpeg) rendering still works.";

  // Task 20.2d: caption treatment for Enhanced renders, remembered like the renderer choice.
  const CAPTION_STYLE_STORAGE_KEY = "die-caption-style";
  const CAPTION_STYLES = ["outline", "box", "shade"];
  const CAPTION_STYLE_TOOLTIPS = {
    outline: "White text with a black outline, like film and streaming subtitles. Readable on any background.",
    box: "Text on a semi-transparent dark box, like YouTube captions. The most readable on very busy images.",
    shade: "Outlined text plus a soft dark shade over the bottom of the picture.",
  };
  const CAPTION_STYLE_DISABLED_TOOLTIP =
    "Caption styles apply to Enhanced (Remotion) renders. Standard (ffmpeg) keeps its own subtitles.";

  const state = {
    projectId: null,
    project: null,
    templates: [],
    selectedTemplate: null,
    aspectRatio: "16:9",
    renderer: "ffmpeg",
    captionStyle: "outline",
    remotionConfigured: false,
    audioReady: false,
    audioJob: null,
    lines: [],
    selectedLineId: null,
    timelineError: "",
    isGenerating: false,
    avatarBusy: {},
    visuals: null,
    visualCharacters: [],
    visualScenes: [],
    visualHealth: null,
    visualSceneSelection: [],
    visualBusy: false,
    visualProgress: null,
    visualError: "",
    shotVariants: {},
  };

  const byId = (id) => document.getElementById(id);

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

  function visualGenerationAllowed() {
    return Boolean(state.visualHealth?.enabled && state.visualHealth?.venv_image_present);
  }

  function visualGenerationHint() {
    if (!state.visualHealth?.enabled) return "AI visuals generation is disabled.";
    if (!state.visualHealth?.venv_image_present) return "The local image environment is missing.";
    return "";
  }

  function visualWarning(text) {
    state.visualError = text || "";
    byId("visual-warnings").textContent = state.visualError || state.visuals?.warnings?.join(" ") || "";
  }

  function renderVisualCast() {
    const grid = byId("visual-cast-grid");
    grid.replaceChildren();
    (state.project?.speakers || []).forEach((speaker) => {
      const card = document.createElement("div");
      card.className = "card visual-cast-card";
      const label = document.createElement("label");
      const select = document.createElement("select");
      select.id = `visual-speaker-${speaker.speaker_index}`;
      label.htmlFor = select.id;
      label.textContent = speaker.name;
      const none = document.createElement("option");
      none.value = "";
      none.textContent = "— none —";
      select.append(none);
      state.visualCharacters.filter((character) => character.status === "locked").forEach((character) => {
        const option = document.createElement("option");
        option.value = character.id;
        option.textContent = character.name;
        select.append(option);
      });
      const castMember = state.visuals?.cast.find((member) => member.speaker_index === speaker.speaker_index);
      select.value = castMember?.character_id || "";
      select.disabled = state.visualBusy;
      select.addEventListener("change", async () => {
        const members = state.visuals.cast
          .filter((member) => member.speaker_index !== speaker.speaker_index)
          .map((member) => ({ speaker_index: member.speaker_index, character_id: member.character_id }));
        if (select.value) members.push({ speaker_index: speaker.speaker_index, character_id: select.value });
        members.sort((a, b) => a.speaker_index - b.speaker_index);
        state.visualBusy = true;
        grid.querySelectorAll("select").forEach((control) => { control.disabled = true; });
        try {
          state.visuals = await Api.setProjectCast(state.projectId, members);
          state.visualError = "";
          renderProjectVisuals();
        } catch (error) {
          visualWarning(error.message || "Could not save the cast.");
        } finally {
          state.visualBusy = false;
          renderProjectVisuals();
        }
      });
      card.append(label, select);
      const chosen = state.visualCharacters.find((character) => character.id === select.value);
      if (chosen?.face_url) {
        const image = document.createElement("img");
        image.className = "visual-cast-face";
        image.src = chosen.face_url;
        image.alt = `${chosen.name} face`;
        card.append(image);
      }
      grid.append(card);
    });
  }

  function renderVisualScenes() {
    const choices = byId("visual-scene-options");
    choices.replaceChildren();
    state.visualScenes.forEach((scene) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-ghost btn-sm";
      button.textContent = scene.name;
      button.setAttribute("aria-pressed", String(state.visualSceneSelection.includes(scene.id)));
      button.disabled = state.visualBusy;
      button.addEventListener("click", async () => {
        const selected = [...state.visualSceneSelection];
        if (selected.includes(scene.id)) {
          if (selected.length === 1) {
            visualWarning("Choose at least one scene.");
            return;
          }
          selected.splice(selected.indexOf(scene.id), 1);
        } else if (selected.length < 3) {
          selected.push(scene.id);
        } else {
          visualWarning("Choose up to three scenes.");
          return;
        }
        state.visualBusy = true;
        choices.querySelectorAll("button").forEach((control) => { control.disabled = true; });
        try {
          state.visuals = await Api.setProjectScenes(state.projectId, selected);
          state.visualSceneSelection = selected;
          state.visualError = "";
        } catch (error) {
          visualWarning(error.message || "Could not save scenes.");
        } finally {
          state.visualBusy = false;
          renderProjectVisuals();
        }
      });
      choices.append(button);
    });
    const order = byId("visual-scene-order");
    order.replaceChildren();
    state.visualSceneSelection.forEach((id, index) => {
      const scene = state.visualScenes.find((item) => item.id === id);
      if (!scene) return;
      const chip = document.createElement("span");
      chip.textContent = `${index + 1}. ${scene.name}`;
      order.append(chip);
    });
  }

  function renderVisualShots() {
    const root = byId("visual-shot-grid");
    root.replaceChildren();
    const shots = state.visuals?.shots || [];
    if (!shots.length) return;
    // Task 24.5a: group by each shot's own place (storyboard shots may use any library scene;
    // inserts have none), in the order shots were planned.
    const groups = [...new Map(shots.map((shot) => [shot.scene_id, { id: shot.scene_id, name: shot.scene_name }])).values()];
    groups.forEach((scene) => {
      const group = shots.filter((shot) => shot.scene_id === scene.id);
      if (!group.length) return;
      const section = document.createElement("section");
      section.className = "visual-shot-scene";
      const heading = document.createElement("h3");
      heading.textContent = scene.name;
      const grid = document.createElement("div");
      grid.className = "visual-shot-grid";
      group.forEach((shot) => {
        const card = document.createElement("article");
        card.className = "card visual-shot-card";
        const kind = document.createElement("h4");
        const who = shot.speaker_indexes.map((i) =>
          state.project.speakers.find((speaker) => speaker.speaker_index === i)?.name || `Speaker ${i + 1}`).join(" & ");
        kind.textContent = shot.kind === "insert" ? `insert · ${shot.subject || "illustration"}`
          : `${shot.kind.replace("_", " ")} · ${who}`;
        card.append(kind);
        if (shot.kind !== "insert" && (shot.action || (shot.expression && shot.expression !== "calm"))) {
          const beat = document.createElement("p");
          beat.className = "visual-shot-beat";
          beat.textContent = [shot.action, shot.expression].filter(Boolean).join(" · ");
          card.append(beat);
        }
        const variant = state.shotVariants[shot.id] || "final";
        const url = variant === "raw" ? shot.raw_url : shot.final_url;
        if (url) {
          const image = document.createElement("img");
          image.src = `${url}&seed=${shot.seed}`;
          image.alt = `${scene.name} ${shot.kind} ${variant} shot`;
          card.append(image);
        }
        if (shot.prompt_truncated) {
          const warning = document.createElement("span");
          warning.className = "visual-warning";
          warning.textContent = "⚠ description too long";
          card.append(warning);
        }
        const actions = document.createElement("div");
        actions.className = "library-actions";
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "btn btn-ghost btn-sm";
        toggle.textContent = variant === "raw" ? "Show final" : "Show raw";
        toggle.disabled = !shot.raw_url || !shot.final_url;
        toggle.addEventListener("click", () => {
          state.shotVariants[shot.id] = variant === "raw" ? "final" : "raw";
          renderVisualShots();
        });
        const regenerate = document.createElement("button");
        regenerate.type = "button";
        regenerate.className = "btn btn-ghost btn-sm";
        regenerate.textContent = "↻ Regenerate";
        regenerate.disabled = state.visualBusy || !visualGenerationAllowed();
        regenerate.title = visualGenerationHint();
        regenerate.addEventListener("click", () => startVisualJob(
          () => Api.regenerateProjectShot(state.projectId, shot.id)));
        actions.append(toggle, regenerate);
        card.append(actions);
        grid.append(card);
      });
      section.append(heading, grid);
      root.append(section);
    });
  }

  function renderProjectVisuals() {
    if (!state.visuals) return;
    renderVisualCast();
    renderVisualScenes();
    renderVisualShots();
    const button = byId("generate-shots-btn");
    button.disabled = state.visualBusy || !visualGenerationAllowed()
      || !state.visuals.cast.length || !state.visuals.scenes.length;
    button.title = visualGenerationHint() || (!state.visuals.cast.length || !state.visuals.scenes.length
      ? "Assign a cast and at least one scene first." : "");
    byId("visual-warnings").textContent = state.visualError || state.visuals.warnings.join(" ");
  }

  async function watchVisualJob(job) {
    state.visualBusy = true;
    renderProjectVisuals();
    state.visualProgress?.destroy();
    state.visualProgress = GenerationStatus.mount({
      element: byId("visual-job-progress"), baselineSec: 180, startedAtIso: job.created_at,
    });
    const cancel = byId("cancel-shots-btn");
    cancel.hidden = false;
    cancel.disabled = false;
    cancel.onclick = async () => {
      cancel.disabled = true;
      try {
        await Api.cancelImageJob(job.id);
      } catch (error) {
        cancel.disabled = false;
        visualWarning(error.message || "Could not cancel the shot job.");
      }
    };
    try {
      let current = job;
      while (!["complete", "error", "cancelled"].includes(current.status)) {
        state.visualProgress.setProgress({ stageLabel: current.stage || "Queued", progressPercent: current.progress });
        await new Promise((resolve) => setTimeout(resolve, 500));
        current = await Api.getImageJob(job.id);
      }
      state.visualProgress.setProgress({ stageLabel: current.stage, progressPercent: current.progress, done: true });
      if (current.status === "error") throw new Error(current.error || "Shot job failed.");
      state.visuals = await Api.getProjectVisuals(state.projectId);
      state.visualError = current.status === "cancelled" ? "Shot generation cancelled. Completed shots were kept." : "";
    } catch (error) {
      visualWarning(error.message || "Could not generate shots.");
    } finally {
      cancel.hidden = true;
      cancel.onclick = null;
      state.visualBusy = false;
      renderProjectVisuals();
    }
  }

  async function startVisualJob(operation) {
    if (state.visualBusy || !visualGenerationAllowed()) return;
    try {
      await watchVisualJob(await operation());
    } catch (error) {
      visualWarning(error.message || "Could not start shot generation.");
    }
  }

  async function loadProjectVisuals() {
    try {
      [state.visuals, state.visualCharacters, state.visualScenes, state.visualHealth] = await Promise.all([
        Api.getProjectVisuals(state.projectId), Api.listCharacters(), Api.listScenes(), Api.getVisualsHealth(),
      ]);
      state.visualSceneSelection = state.visuals.scenes.map((scene) => scene.id);
      renderProjectVisuals();
      if (state.visuals.active_job) watchVisualJob(state.visuals.active_job);
    } catch (error) {
      visualWarning(error.message || "Characters and scenes could not load.");
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

  function readStoredRenderer() {
    try {
      return localStorage.getItem(RENDERER_STORAGE_KEY) || "ffmpeg";
    } catch {
      return "ffmpeg"; // localStorage unavailable — default to Standard
    }
  }

  function storeRenderer(renderer) {
    try {
      localStorage.setItem(RENDERER_STORAGE_KEY, renderer);
    } catch {
      /* localStorage unavailable — the choice just won't persist across reloads */
    }
  }

  function readStoredCaptionStyle() {
    try {
      const stored = localStorage.getItem(CAPTION_STYLE_STORAGE_KEY);
      return CAPTION_STYLES.includes(stored) ? stored : "outline";
    } catch {
      return "outline"; // localStorage unavailable — default to the film-style outline
    }
  }

  function storeCaptionStyle(captionStyle) {
    try {
      localStorage.setItem(CAPTION_STYLE_STORAGE_KEY, captionStyle);
    } catch {
      /* localStorage unavailable — the choice just won't persist across reloads */
    }
  }

  function renderCaptionStyleToggle() {
    const group = byId("caption-style-group");
    if (!group) return;
    const enabled = state.renderer === "remotion" && !state.isGenerating;
    group.querySelectorAll(".chip").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.captionStyle === state.captionStyle));
      button.disabled = !enabled;
      button.title = state.renderer === "remotion" ? CAPTION_STYLE_TOOLTIPS[button.dataset.captionStyle] : CAPTION_STYLE_DISABLED_TOOLTIP;
    });
  }

  function setupCaptionStyleToggle() {
    const group = byId("caption-style-group");
    if (!group) return;
    group.querySelectorAll(".chip").forEach((button) => {
      button.addEventListener("click", () => {
        if (state.isGenerating || button.disabled) return;
        state.captionStyle = button.dataset.captionStyle;
        storeCaptionStyle(state.captionStyle);
        renderCaptionStyleToggle();
      });
    });
  }

  function renderRendererToggle() {
    renderCaptionStyleToggle();
    const group = byId("renderer-group");
    if (!group) return;
    const buttons = group.querySelectorAll(".chip");
    buttons.forEach((button) => {
      const isRemotion = button.dataset.renderer === "remotion";
      button.setAttribute("aria-pressed", String(button.dataset.renderer === state.renderer));
      if (isRemotion) {
        button.disabled = !state.remotionConfigured || state.isGenerating;
        button.title = state.remotionConfigured ? RENDERER_ENABLED_TOOLTIP : RENDERER_DISABLED_TOOLTIP;
      } else {
        button.disabled = state.isGenerating;
        button.title = "";
      }
    });
  }

  function setupRendererToggle() {
    const group = byId("renderer-group");
    if (!group) return;
    group.querySelectorAll(".chip").forEach((button) => {
      button.addEventListener("click", () => {
        if (state.isGenerating || button.disabled) return;
        state.renderer = button.dataset.renderer;
        storeRenderer(state.renderer);
        renderRendererToggle();
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
    renderRendererToggle();
    const generationStatus = GenerationStatus.mount({
      element: byId("generate-progress"),
      baselineSec: VIDEO_BASELINE_SECONDS,
      showEta: false,
    });
    const attemptedRenderer = state.renderer;
    generationStatus.setProgress({
      stageLabel: attemptedRenderer === "remotion" ? "Rendering with Remotion (Enhanced)…" : "Rendering with ffmpeg…",
    });
    try {
      const job = await Api.generateVideo(
        state.projectId,
        state.selectedTemplate,
        state.aspectRatio,
        attemptedRenderer,
        attemptedRenderer === "remotion" ? state.captionStyle : null
      );
      renderResult(job);
      // Task 19.7 (I36-a): a Remotion failure always falls back to ffmpeg rather than
      // failing the request -- surface that honestly instead of silently claiming Enhanced.
      const doneLabel =
        attemptedRenderer === "remotion" && job.fallback_used
          ? "Done (Remotion unavailable this time — used Standard instead)."
          : "Done.";
      generationStatus.setProgress({ stageLabel: doneLabel, done: true });
    } catch (error) {
      console.error("Failed to generate video:", error);
      showError("We couldn't generate the video. Please try again.");
      generationStatus.destroy();
      byId("generate-progress").textContent = "";
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
      // Task 20.2d: re-enable the renderer + caption-style chips once the render ends (they
      // were locked by the renderRendererToggle() call at the start and never unlocked).
      renderRendererToggle();
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
      const health = await Api.getVideoHealth();
      state.remotionConfigured = Boolean(health.remotion_configured);
    } catch (error) {
      console.error("Failed to load video renderer health (non-fatal, Standard still works):", error);
      state.remotionConfigured = false;
    }
    // Only honor a stored "remotion" preference when it's actually usable right now --
    // otherwise the toggle would render as checked-but-disabled, a confusing combination.
    state.renderer = state.remotionConfigured ? readStoredRenderer() : "ffmpeg";
    state.captionStyle = readStoredCaptionStyle();

    try {
      const job = await Api.getVideoStatus(state.projectId);
      if (job && job.status === "complete") renderResult(job);
    } catch (error) {
      if (error.status !== 404) console.error("Failed to load existing video job:", error);
    }

    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
    await loadProjectVisuals();
    renderAvatars();
    renderTemplates();
    renderTimeline();
    renderInspector();
    setupAspectRatioToggle();
    setupRendererToggle();
    setupCaptionStyleToggle();
    renderRendererToggle();
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
    byId("generate-shots-btn").addEventListener("click", () => startVisualJob(
      () => Api.generateProjectShots(state.projectId)));
    window.addEventListener("beforeunload", (event) => {
      if (state.isGenerating) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    init();
  });
})();
