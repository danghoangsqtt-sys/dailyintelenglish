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

  // A Remotion render takes minutes and varies a lot with the episode, so no ETA is shown (showEta: false below), only the
  // elapsed counter as the honest "something is happening" signal.
  const VIDEO_BASELINE_SECONDS = 1;

  // Phase 30 (ENH-021): what is behind the captions, remembered per browser.
  const VISUAL_MODE_STORAGE_KEY = "die-visual-mode";
  const STILL_SCENE_STORAGE_KEY = "die-still-scene";
  // Phase 44 (D123): the drawn-shot "illustrated" mode was removed with RealVisXL; talking characters is the default.
  const VISUAL_MODES = ["podcast_sprites", "podcast_still", "podcast_black"];
  // the modes that use the scene picture chosen below (talking characters: when the storyboard gives no places)
  const STILL_SCENE_MODES = ["podcast_still", "podcast_sprites"];
  const VISUAL_MODE_ENABLED_TOOLTIP = "What is behind the captions";

  // Task 20.2d: caption treatment, remembered per browser.
  const CAPTION_STYLE_STORAGE_KEY = "die-caption-style";
  const CAPTION_STYLES = ["outline", "box", "shade"];
  const CAPTION_STYLE_TOOLTIPS = {
    outline: "White text with a black outline, like film and streaming subtitles. Readable on any background.",
    box: "Text on a semi-transparent dark box, like YouTube captions. The most readable on very busy images.",
    shade: "Outlined text plus a soft dark shade over the bottom of the picture.",
  };

  const state = {
    projectId: null,
    project: null,
    captionStyle: "outline",
    visualMode: "podcast_sprites",
    stillScene: "",
    stillScenes: [],
    remotionConfigured: false,
    rendererProblem: null,
    audioReady: false,
    audioJob: null,
    lines: [],
    selectedLineId: null,
    timelineError: "",
    isGenerating: false,
    visuals: null,
    visualCharacters: [],
    visualScenes: [],
    visualHealth: null,
    visualSceneSelection: [],
    visualBusy: false,
    visualProgress: null,
    visualError: "",
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
    byId("visual-warnings").textContent = state.visualError;
  }

  // Phase 35 (Task 35.4, D89): the cast is chosen with the shared game-style selector of Step 1 (no dropdown, no avatar).
  // Phase 40 (D119): a speaker takes its character's name everywhere; say what changed and that the audio must be redone.
  async function afterRename(renamed) {
    if (!renamed?.length) return;
    state.project = await Api.getProject(state.projectId);
    const changed = renamed.reduce((total, item) => total + (item.lines_changed || 0), 0);
    const names = renamed.map((item) => `${item.old_name || "the speaker"} → ${item.new_name}`).join(", ");
    visualWarning(`Renamed ${names}${changed ? ` in ${changed} script line${changed === 1 ? "" : "s"}` : ""}. `
      + "Regenerate the audio in Step 4 so the voices say the new names, then render the video again.");
  }

  async function saveCast(speakerIndex, characterId) {
    const members = state.visuals.cast
      .filter((member) => member.speaker_index !== speakerIndex)
      .map((member) => ({ speaker_index: member.speaker_index, character_id: member.character_id }));
    if (characterId) members.push({ speaker_index: speakerIndex, character_id: characterId });
    members.sort((a, b) => a.speaker_index - b.speaker_index);
    state.visualBusy = true;
    renderProjectVisuals();
    try {
      state.visuals = await Api.setProjectCast(state.projectId, members);
      state.visualError = "";
      await afterRename(state.visuals.renamed);
    } catch (error) {
      visualWarning(error.message || "Could not save the cast.");
    } finally {
      state.visualBusy = false;
      renderProjectVisuals();
    }
  }

  function openCastSelector(speakerIndex) {
    const speakers = state.project?.speakers || [];
    CharacterSelector.open({
      slots: speakers.map((speaker) => ({
        index: speaker.speaker_index, label: `Character ${speaker.speaker_index + 1}`,
        characterId: state.visuals?.cast.find((member) => member.speaker_index === speaker.speaker_index)?.character_id || null,
      })),
      profiles: state.visualProfiles || [],
      startSlot: speakerIndex,
      onChoose: (slotIndex, profile) => saveCast(slotIndex, profile.id),
    });
  }

  function renderVisualCast() {
    const grid = byId("visual-cast-grid");
    grid.replaceChildren();
    (state.project?.speakers || []).forEach((speaker) => {
      const card = document.createElement("div");
      card.className = "card visual-cast-card";
      card.dataset.speaker = speaker.speaker_index;
      const label = document.createElement("label");
      label.textContent = speaker.name;
      const castMember = state.visuals?.cast.find((member) => member.speaker_index === speaker.speaker_index);
      const chosen = state.visualCharacters.find((character) => character.id === castMember?.character_id);
      card.append(label);
      if (chosen?.face_url) {
        const image = document.createElement("img");
        image.className = "visual-cast-face";
        image.src = chosen.face_url;
        image.alt = `${chosen.name} face`;
        card.append(image);
      }
      const name = document.createElement("div");
      name.className = "visual-cast-name";
      name.textContent = chosen ? chosen.name : "No character yet";
      card.append(name);
      const actions = document.createElement("div");
      actions.className = "visual-cast-actions";
      const change = document.createElement("button");
      change.type = "button";
      change.className = "btn btn-primary btn-sm";
      change.dataset.action = "choose-character";
      change.textContent = chosen ? "Change character" : "Choose character";
      change.disabled = state.visualBusy;
      change.addEventListener("click", () => openCastSelector(speaker.speaker_index));
      actions.append(change);
      if (castMember) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-ghost btn-sm";
        remove.dataset.action = "remove-character";
        remove.textContent = "Remove";
        remove.disabled = state.visualBusy;
        remove.addEventListener("click", () => saveCast(speaker.speaker_index, null));
        actions.append(remove);
      }
      card.append(actions);
      // Phase 33 (D80): an older project's speaker can keep another name than its character (Demo Episode "Maya" is Lina)
      if (chosen && chosen.name !== speaker.name) {
        const rename = document.createElement("button");
        rename.type = "button";
        rename.className = "btn btn-ghost btn-sm";
        rename.textContent = `Use character name (${chosen.name})`;
        rename.disabled = state.visualBusy;
        rename.addEventListener("click", async () => {
          try {
            const updated = await Api.updateSpeaker(state.projectId, speaker.id, { name: chosen.name });
            speaker.name = chosen.name;
            await afterRename(updated.renamed ? [updated.renamed] : []);
            renderProjectVisuals();
          } catch (error) {
            visualWarning(error.message || "Could not rename the speaker.");
          }
        });
        card.append(rename);
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

  async function renderActivityCoverage() {
    const line = byId("activity-coverage");
    if (!line || !state.projectId) return;
    try {
      const coverage = await Api.getActivityCoverage(state.projectId);
      if (!coverage.items.length) { line.hidden = true; return; }
      line.hidden = false;
      // Gate B-23: an insert without a library picture shows no illustration (the scene stays); say so and name the closest.
      const missing = coverage.items
        .filter((item) => item.status === "missing")
        .map((item) => {
          const name = `"${item.action || `insert ${item.position + 1}`}"`;
          const closest = (item.suggestions || []).map((value) => `"${value}"`).join(", ");
          return closest ? `${name} (closest in the library: ${closest})` : name;
        });
      const fallback = missing.length
        ? ` No illustration for ${missing.length}: ${missing.join("; ")} -- the scene stays behind the speakers.`
          + " Change the insert's action in the storyboard to a library activity to show a picture."
        : " Every insert has an illustration.";
      line.textContent = `Activity illustrations: ${coverage.matched} of ${coverage.items.length} inserts matched `
        + `(${coverage.character} character, ${coverage.generic} generic).${fallback}`;
      line.classList.toggle("is-warning", missing.length > 0);
      renderMissingIllustrations(coverage);
    } catch {
      line.hidden = true;
      byId("activity-missing").hidden = true;
    }
  }

  // Task 33.10 (D102): an insert without a library picture -- draw one on the GPU, or make it with an outside AI and drop it here.
  function renderMissingIllustrations(coverage) {
    const box = byId("activity-missing");
    const list = byId("activity-missing-list");
    const items = coverage.items.filter((item) => item.status === "missing");
    box.hidden = items.length === 0;
    list.replaceChildren();
    const draw = byId("draw-illustrations-btn");
    draw.disabled = state.visualBusy || !visualGenerationAllowed() || !coverage.to_draw;
    draw.title = visualGenerationHint() || (coverage.to_draw ? "" : "Every insert has a picture waiting for approval.");
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "card activity-missing-card";
      card.dataset.beat = item.beat_id;
      let picture;
      if (item.pending) {
        picture = document.createElement("img");
        picture.src = `${item.pending.url}?t=${Date.now()}`;
        picture.alt = `Picture waiting for approval: ${item.activity}`;
      } else {
        picture = document.createElement("div");
        picture.className = "activity-empty";
        picture.textContent = "No picture yet";
      }
      const body = document.createElement("div");
      const title = document.createElement("h4");
      title.textContent = `Insert ${item.position + 1}: ${item.action || item.place || "illustration"}`;
      const closest = document.createElement("p");
      closest.textContent = item.suggestions?.length
        ? `Closest in the library: ${item.suggestions.join(", ")} (change the insert's action in the storyboard to use one).`
        : "Nothing close in the library.";
      const prompt = document.createElement("textarea");
      prompt.readOnly = true;
      prompt.value = item.prompt || "";
      prompt.setAttribute("aria-label", `Outside-AI prompt for ${item.activity}`);
      const actions = document.createElement("div");
      actions.className = "activity-missing-actions";
      const button = (label, onClick, primary = false) => {
        const element = document.createElement("button");
        element.type = "button";
        element.className = `btn ${primary ? "btn-primary" : "btn-ghost"} btn-sm`;
        element.textContent = label;
        element.disabled = state.visualBusy;
        element.addEventListener("click", onClick);
        actions.append(element);
        return element;
      };
      if (item.pending) {
        button("Approve", () => reviewIllustration(item.pending.id, "approved"), true).dataset.action = "approve";
        button("Redraw", () => redrawIllustration(item.pending.id)).dataset.action = "redraw";
      }
      button("Copy prompt", async () => {
        try { await navigator.clipboard.writeText(prompt.value); } catch { prompt.select(); }
      });
      const file = document.createElement("input");
      file.type = "file";
      file.accept = "image/png,image/jpeg,image/webp";
      file.id = `activity-file-${item.beat_id}`;
      file.addEventListener("change", () => {
        if (file.files[0]) uploadIllustration(item, file.files[0]);
      });
      const upload = document.createElement("label");
      upload.className = "btn btn-ghost btn-sm";
      upload.htmlFor = file.id;
      upload.textContent = "Upload outside-AI picture";
      actions.append(file, upload);
      body.append(title, closest, prompt, actions);
      card.append(picture, body);
      list.append(card);
    });
  }

  async function reviewIllustration(id, reviewState) {
    try {
      await Api.reviewLibraryActivity(id, reviewState);
    } catch (error) {
      visualWarning(error.message || "Could not review the picture.");
    }
    await renderActivityCoverage();
  }

  async function redrawIllustration(id) {
    try {
      await Api.reviewLibraryActivity(id, "rejected");
    } catch (error) {
      visualWarning(error.message || "Could not reject the picture.");
      return;
    }
    await renderActivityCoverage();
    if (visualGenerationAllowed()) await startVisualJob(() => Api.drawActivityIllustrations(state.projectId));
  }

  async function uploadIllustration(item, file) {
    const form = new FormData();
    form.append("file", file);
    form.append("activity", item.activity);
    if (item.place) form.append("context_tags", item.place);
    try {
      await Api.uploadLibraryActivity(form);
    } catch (error) {
      visualWarning(error.message || "Could not upload the picture.");
    }
    await renderActivityCoverage();
  }

  function renderProjectVisuals() {
    if (!state.visuals) return;
    renderActivityCoverage();
    renderVisualCast();
    renderVisualScenes();
    byId("visual-warnings").textContent = state.visualError;
  }

  async function watchVisualJob(job) {
    state.visualBusy = true;
    renderProjectVisuals();
    state.visualProgress?.destroy();
    state.visualProgress = GenerationStatus.mount({
      element: byId("visual-job-progress"), baselineSec: 180, startedAtIso: job.created_at,
    });
    try {
      let current = job;
      while (!["complete", "error", "cancelled"].includes(current.status)) {
        state.visualProgress.setProgress({ stageLabel: current.stage || "Queued", progressPercent: current.progress });
        await new Promise((resolve) => setTimeout(resolve, 500));
        current = await Api.getImageJob(job.id);
      }
      state.visualProgress.setProgress({ stageLabel: current.stage, progressPercent: current.progress, done: true });
      if (current.status === "error") throw new Error(current.error || "The picture job failed.");
      state.visuals = await Api.getProjectVisuals(state.projectId);
      state.visualError = current.status === "cancelled" ? "Cancelled." : "";
    } catch (error) {
      visualWarning(error.message || "The pictures could not be drawn.");
    } finally {
      state.visualBusy = false;
      renderProjectVisuals();
    }
  }

  async function startVisualJob(operation) {
    if (state.visualBusy || !visualGenerationAllowed()) return;
    try {
      await watchVisualJob(await operation());
    } catch (error) {
      visualWarning(error.message || "Could not start drawing the pictures.");
    }
  }

  // Phase 33 (Task 33.7): the cast is chosen explicitly (Step 1 or here); it is never inferred from a speaker's name.
  function castOptions(characters, profiles) {
    const ready = new Map(profiles.filter((profile) => profile.readiness?.video_ready)
      .map((profile) => [profile.id, profile]));
    return characters.map((character) => {
      const profile = ready.get(character.id);
      return {
        ...character,
        video_ready: character.status === "locked" || Boolean(profile),
        face_url: character.face_url || profile?.pictures?.portrait || profile?.pictures?.base || null,
      };
    });
  }

  async function loadProjectVisuals() {
    try {
      let characters, profiles;
      [state.visuals, characters, state.visualScenes, state.visualHealth, profiles] = await Promise.all([
        Api.getProjectVisuals(state.projectId), Api.listCharacters(), Api.listScenes(), Api.getVisualsHealth(),
        Api.listProfiles("state=active"),
      ]);
      state.visualCharacters = castOptions(characters, profiles);
      state.visualProfiles = profiles;
      state.visualSceneSelection = state.visuals.scenes.map((scene) => scene.id);
      renderProjectVisuals();
    } catch (error) {
      visualWarning(error.message || "Characters and scenes could not load.");
    }
  }

  function applyLocks() {
    const button = byId("generate-btn");
    button.disabled = state.isGenerating || !state.audioReady || !state.remotionConfigured;
    button.title = state.remotionConfigured ? "" : `The video renderer is not ready: ${state.rendererProblem || "unknown"}`;
  }

  function readStoredVisualMode() {
    try {
      const stored = localStorage.getItem(VISUAL_MODE_STORAGE_KEY);
      return VISUAL_MODES.includes(stored) ? stored : "podcast_sprites";  // an old "illustrated" choice -> the default
    } catch {
      return "podcast_sprites";
    }
  }

  function readStoredStillScene() {
    try {
      return localStorage.getItem(STILL_SCENE_STORAGE_KEY) || "";
    } catch {
      return "";
    }
  }

  function remember(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* the choice just is not remembered */
    }
  }

  function renderVisualModes() {
    const group = byId("visual-mode-group");
    if (!group) return;
    group.querySelectorAll(".chip").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.visualMode === state.visualMode));
      button.disabled = state.isGenerating;
      button.title = VISUAL_MODE_ENABLED_TOOLTIP;
    });
    group.title = VISUAL_MODE_ENABLED_TOOLTIP;
    const row = byId("still-scene-row");
    if (row) row.hidden = !STILL_SCENE_MODES.includes(state.visualMode);
    const select = byId("still-scene");
    if (select) select.disabled = state.isGenerating;
  }

  function renderStillScenes() {
    const select = byId("still-scene");
    if (!select) return;
    select.replaceChildren();
    const auto = document.createElement("option");
    auto.value = "";
    auto.textContent = "Automatic (first scene with a plate)";
    select.append(auto);
    state.stillScenes.forEach((scene) => {
      const option = document.createElement("option");
      option.value = scene.id;
      option.textContent = scene.name;
      select.append(option);
    });
    select.value = state.stillScenes.some((scene) => scene.id === state.stillScene) ? state.stillScene : "";
    state.stillScene = select.value;
  }

  async function loadStillScenes() {
    try {
      const scenes = await Api.listScenes();
      state.stillScenes = scenes.filter((scene) => scene.preview_url); // only a scene with a plate can be shown
    } catch (error) {
      console.error("Failed to load the scenes for the still picture:", error);
      state.stillScenes = [];
    }
    renderStillScenes();
  }

  function setupVisualModes() {
    const group = byId("visual-mode-group");
    if (!group) return;
    group.querySelectorAll(".chip").forEach((button) => {
      button.addEventListener("click", () => {
        if (state.isGenerating || button.disabled) return;
        state.visualMode = button.dataset.visualMode;
        remember(VISUAL_MODE_STORAGE_KEY, state.visualMode);
        renderVisualModes();
      });
    });
    const select = byId("still-scene");
    if (select) {
      select.addEventListener("change", () => {
        state.stillScene = select.value;
        remember(STILL_SCENE_STORAGE_KEY, state.stillScene);
      });
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
    group.querySelectorAll(".chip").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.captionStyle === state.captionStyle));
      button.disabled = state.isGenerating;
      button.title = CAPTION_STYLE_TOOLTIPS[button.dataset.captionStyle];
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

  function renderRenderOptions() {
    renderCaptionStyleToggle();
    renderVisualModes();
    const status = byId("renderer-status");
    if (status) {
      status.hidden = state.remotionConfigured;
      status.textContent = state.remotionConfigured ? ""
        : `The video renderer is not ready on this machine: ${state.rendererProblem || "unknown"}. `
          + "Run scripts/check_dependencies.py for the details.";
    }
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

  }

  async function generateVideo() {
    if (state.isGenerating || !state.audioReady || !state.remotionConfigured) return;
    state.isGenerating = true;
    clearError();
    setGenerateLoading(true);
    renderRenderOptions();
    const generationStatus = GenerationStatus.mount({
      element: byId("generate-progress"),
      baselineSec: VIDEO_BASELINE_SECONDS,
      showEta: false,
    });
    generationStatus.setProgress({ stageLabel: "Rendering the video…" });
    try {
      const job = await Api.generateVideo(state.projectId, {
        captionStyle: state.captionStyle,
        visualMode: state.visualMode,
        stillSceneId: STILL_SCENE_MODES.includes(state.visualMode) ? state.stillScene || null : null,
      });
      renderResult(job);
      generationStatus.setProgress({ stageLabel: "Done.", done: true });
      document.dispatchEvent(new CustomEvent("video:rendered")); // the Shorts / vertical section can open now
    } catch (error) {
      console.error("Failed to generate video:", error);
      showError(error.message || "We couldn't generate the video. Please try again.");
      generationStatus.destroy();
      byId("generate-progress").textContent = "";
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
      // Task 20.2d: re-enable the caption-style and picture chips once the render ends.
      renderRenderOptions();
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

    if (!state.audioReady && state.project.presentation_mode !== "solo_explainer") {
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
      const health = await Api.getVideoHealth();
      state.remotionConfigured = Boolean(health.remotion_configured);
      state.rendererProblem = health.renderer_problem || null;
    } catch (error) {
      console.error("Failed to load the video renderer status:", error);
      state.remotionConfigured = false;
      state.rendererProblem = "its status could not be read";
    }
    state.captionStyle = readStoredCaptionStyle();
    state.visualMode = readStoredVisualMode();
    state.stillScene = readStoredStillScene();

    try {
      const job = await Api.getVideoStatus(state.projectId);
      if (job && job.status === "complete") renderResult(job);
    } catch (error) {
      if (error.status !== 404) console.error("Failed to load existing video job:", error);
    }

    if (state.project.presentation_mode === "solo_explainer") {
      byId("project-visuals-section").hidden = true;
      byId("storyboard-section").hidden = true;
      byId("solo-explainer-section").hidden = false;
      await ExplainerEditor.mount(byId("solo-explainer-section"), state.projectId,
        { style: state.project.explainer_style || "presenter", topic: state.project.topic || "" });
    } else {
      await loadProjectVisuals();
    }
    renderTimeline();
    renderInspector();
    setupCaptionStyleToggle();
    if (state.project.presentation_mode !== "solo_explainer") {
      setupVisualModes();
      await loadStillScenes();
    } else {
      byId("visual-mode-group").hidden = true;
      byId("visual-mode-hint").hidden = true;
    }
    renderRenderOptions();
    applyLocks();
    // Expose the workspace only after async options and renderer-dependent controls are ready.
    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
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
    byId("draw-illustrations-btn").addEventListener("click", () => startVisualJob(
      () => Api.drawActivityIllustrations(state.projectId)));
    window.addEventListener("beforeunload", (event) => {
      if (state.isGenerating) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    init();
  });
})();
