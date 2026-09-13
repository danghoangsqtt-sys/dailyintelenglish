/**
 * Step 5 — Video Studio. Business rules stay on the backend; this file owns only UI
 * state and calls through Api (CR-05). Only the fixed background-template path is built
 * here — no avatar/lips-sync controls, since that backend path doesn't exist yet (see
 * task-1.7.md: Level 3 needs a real user decision on avatar image sourcing).
 */
(() => {
  const state = {
    projectId: null,
    project: null,
    templates: [],
    selectedTemplate: null,
    audioReady: false,
    isGenerating: false,
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
    if (state.isGenerating || !state.audioReady || !state.selectedTemplate) return;
    state.isGenerating = true;
    clearError();
    setGenerateLoading(true);
    byId("generate-progress").textContent = "Rendering with ffmpeg…";
    try {
      const job = await Api.generateVideo(state.projectId, state.selectedTemplate);
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
    renderTemplates();
    applyLocks();
  }

  document.addEventListener("DOMContentLoaded", () => {
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
