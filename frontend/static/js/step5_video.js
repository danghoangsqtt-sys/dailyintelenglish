/**
 * Step 5 — Video Studio. Business rules stay on the backend; this file owns only UI
 * state and calls through Api (CR-05). Speakers can upload/remove a portrait image
 * (Task 1.7c) but nothing consumes it yet — no lip-sync controls, since LivePortrait
 * integration itself is still deferred (see task-1.7.md / task-1.7c.md).
 */
(() => {
  const state = {
    projectId: null,
    project: null,
    templates: [],
    selectedTemplate: null,
    aspectRatio: "16:9",
    audioReady: false,
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
      // `[hidden]` rule, so an unconditional `.btn { display: inline-flex }` (an
      // author rule, which always beats the UA `[hidden]` rule regardless of
      // specificity) would keep it visibly showing. Only append it when needed.
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
        group.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
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
      const audioStatus = await Api.getAudioStatus(state.projectId);
      state.audioReady = audioStatus.status === "complete";
    } catch (error) {
      state.audioReady = false; // 404 (no audio yet) is expected, not an error to surface
    }

    if (!state.audioReady) {
      byId("loading-panel").hidden = true;
      byId("empty-state").hidden = false;
      return;
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
    setupAspectRatioToggle();
    applyLocks();
  }

  document.addEventListener("DOMContentLoaded", () => {
    StepNav.render("step-nav", { projectId: new URLSearchParams(window.location.search).get("project_id"), currentStep: 5 });
    KeyboardShortcuts.init({ primaryButtonId: "generate-btn" });
    byId("theme-toggle").addEventListener("click", Theme.toggle);
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
