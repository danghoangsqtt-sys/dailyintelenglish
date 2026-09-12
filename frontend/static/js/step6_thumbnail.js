/**
 * Step 6 — Thumbnail Generator. Business rules stay on the backend; this file
 * owns only UI state, serialized saves, and calls through Api (CR-05).
 */
(() => {
  const SAVE_DEBOUNCE_MS = 400;

  const state = {
    projectId: null,
    project: null,
    templates: [],
    thumbnails: [],
    selectedTemplate: null,
    activeId: null,
    previewAspect: "16x9",
    isGenerating: false,
    favoriteInFlight: false,
    loadFailed: false,
    saveStatus: "saved", // "saved" | "dirty" | "saving" | "failed"
    saveQueued: false,
    saveTimer: null,
    draftVersion: 0,
    draft: null,
    staleConflict: false,
  };

  const byId = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));

  function activeThumbnail() {
    return state.thumbnails.find((thumbnail) => thumbnail.id === state.activeId) || null;
  }

  function hasUnresolvedEdit() {
    return state.saveStatus !== "saved" || state.saveQueued;
  }

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

  function setSaveStatus(status, message = null) {
    state.saveStatus = status;
    const statusElement = byId("save-status");
    const retryButton = byId("retry-save-btn");
    const labels = {
      saved: "Saved",
      dirty: "Unsaved changes — re-render queued",
      saving: state.saveQueued ? "Saving… newer changes queued" : "Saving and re-rendering…",
      failed: "Save failed",
    };
    statusElement.textContent = message || labels[status];
    retryButton.hidden = status !== "failed";
    retryButton.textContent = state.staleConflict ? "Reload latest" : "Retry";
    applyLocks();
    if (status === "saved") {
      setTimeout(() => {
        if (state.saveStatus === "saved") statusElement.textContent = "";
      }, 2000);
    }
  }

  function applyLocks() {
    const pendingEdit = hasUnresolvedEdit();
    const workspaceBusy = state.isGenerating || state.favoriteInFlight;
    const destructiveLock = workspaceBusy || pendingEdit || state.loadFailed;

    byId("generate-btn").disabled = destructiveLock;
    byId("variant-count").disabled = destructiveLock;
    document.querySelectorAll(".template-option, .variant-card").forEach((element) => {
      element.disabled = destructiveLock;
    });

    const editorDisabled = workspaceBusy || state.staleConflict || !activeThumbnail();
    byId("headline-input").disabled = editorDisabled;
    document.querySelectorAll("[data-color]").forEach((element) => {
      element.disabled = editorDisabled;
    });
    byId("save-btn").disabled =
      editorDisabled || state.saveStatus === "saved" || state.saveStatus === "saving";
    document.querySelectorAll(".download-link").forEach((link) => {
      link.setAttribute("aria-disabled", pendingEdit || workspaceBusy ? "true" : "false");
    });
  }

  function renderHeader() {
    byId("project-name").textContent = state.project.name;
    const badges = byId("project-badges");
    badges.replaceChildren();
    [state.project.cefr_level, state.project.genre].forEach((label) => {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = label;
      badges.appendChild(badge);
    });
  }

  function renderTemplates() {
    const gallery = byId("template-gallery");
    gallery.replaceChildren();
    state.templates.forEach((template) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "card template-option";
      button.classList.toggle("selected", template.id === state.selectedTemplate);
      button.dataset.templateId = template.id;
      button.setAttribute("aria-pressed", template.id === state.selectedTemplate ? "true" : "false");

      const image = document.createElement("img");
      image.src = template.preview_url;
      image.alt = `${template.display_name} template preview`;
      image.loading = "lazy";
      const copy = document.createElement("span");
      copy.className = "template-copy";
      const name = document.createElement("span");
      name.className = "template-name";
      name.textContent = template.display_name;
      const description = document.createElement("span");
      description.className = "template-description";
      description.textContent = template.description;
      copy.append(name, description);
      button.append(image, copy);
      button.addEventListener("click", () => {
        if (hasUnresolvedEdit() || state.isGenerating || state.favoriteInFlight) return;
        state.selectedTemplate = template.id;
        renderTemplates();
        applyLocks();
      });
      gallery.appendChild(button);
    });
    applyLocks();
  }

  function renderVariants() {
    const grid = byId("variant-grid");
    const empty = byId("variant-empty");
    grid.replaceChildren();
    empty.hidden = state.thumbnails.length > 0;
    state.thumbnails.forEach((thumbnail) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "card variant-card";
      button.classList.toggle("selected", thumbnail.is_selected);
      button.dataset.thumbnailId = thumbnail.id;
      button.setAttribute("aria-pressed", thumbnail.is_selected ? "true" : "false");

      const image = document.createElement("img");
      image.src = thumbnail.assets["16x9"].png;
      image.alt = `Variant ${thumbnail.variant_index + 1}: ${thumbnail.suggestion.headline}`;
      image.loading = "lazy";
      const copy = document.createElement("span");
      copy.className = "variant-copy";
      const headline = document.createElement("span");
      headline.className = "variant-headline";
      headline.textContent = thumbnail.suggestion.headline;
      const favorite = document.createElement("span");
      favorite.className = "favorite-badge";
      favorite.textContent = thumbnail.is_selected ? "★ Favorite" : "☆ Select";
      copy.append(headline, favorite);
      button.append(image, copy);
      button.addEventListener("click", () => selectFavorite(thumbnail.id));
      grid.appendChild(button);
    });
    applyLocks();
  }

  function updateEditorAssets(thumbnail) {
    byId("preview-image").src = thumbnail.assets[state.previewAspect].png;
    document.querySelectorAll(".aspect-btn").forEach((button) => {
      const active = button.dataset.aspect === state.previewAspect;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    ["16x9", "9x16"].forEach((aspect) => {
      ["png", "jpg"].forEach((format) => {
        const link = byId(`download-${aspect}-${format}`);
        link.href = thumbnail.assets[aspect][format];
        link.download = `thumbnail-${thumbnail.variant_index + 1}-${aspect}.${format}`;
      });
    });
  }

  function syncEditorFromActive() {
    const thumbnail = activeThumbnail();
    byId("editor-placeholder").hidden = Boolean(thumbnail);
    byId("editor-layout").hidden = !thumbnail;
    if (!thumbnail) {
      state.draft = null;
      return;
    }
    state.draft = clone(thumbnail.suggestion);
    state.staleConflict = false;
    byId("headline-input").value = state.draft.headline;
    Object.entries(state.draft.palette).forEach(([name, color]) => {
      byId(`color-${name}`).value = color;
    });
    updateEditorAssets(thumbnail);
    setSaveStatus("saved");
  }

  async function selectFavorite(thumbnailId) {
    if (state.favoriteInFlight || state.isGenerating) return;
    if (hasUnresolvedEdit()) {
      showError("Please save or resolve the current thumbnail edit before switching variants.");
      return;
    }
    const current = activeThumbnail();
    if (current && current.id === thumbnailId && current.is_selected) return;

    state.favoriteInFlight = true;
    clearError();
    applyLocks();
    try {
      const selected = await Api.selectThumbnailFavorite(state.projectId, thumbnailId);
      state.thumbnails = state.thumbnails.map((thumbnail) =>
        thumbnail.id === thumbnailId
          ? selected
          : { ...thumbnail, is_selected: false }
      );
      state.activeId = thumbnailId;
      renderVariants();
      syncEditorFromActive();
    } catch (error) {
      console.error("Failed to select thumbnail favorite:", error);
      showError("We couldn't select that favorite. Please try again.");
    } finally {
      state.favoriteInFlight = false;
      applyLocks();
    }
  }

  function setGenerateLoading(loading) {
    const button = byId("generate-btn");
    button.textContent = "";
    if (loading) {
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      button.append(spinner, document.createTextNode(" Generating…"));
    } else {
      button.textContent = state.thumbnails.length ? "✨ Regenerate thumbnails" : "✨ Generate thumbnails";
    }
    applyLocks();
  }

  async function generateThumbnails() {
    if (state.isGenerating || state.favoriteInFlight || hasUnresolvedEdit()) return;
    if (!state.selectedTemplate) {
      showError("Choose a thumbnail template before generating.");
      return;
    }
    if (state.thumbnails.length > 0) {
      const confirmed = confirm(
        "This replaces all current thumbnail variants and their favorite selection. Continue?"
      );
      if (!confirmed) return;
    }

    state.isGenerating = true;
    clearError();
    setGenerateLoading(true);
    try {
      state.thumbnails = await Api.generateThumbnails(
        state.projectId,
        state.selectedTemplate,
        Number(byId("variant-count").value)
      );
      state.activeId = null;
      state.draft = null;
      state.saveQueued = false;
      state.saveStatus = "saved";
      renderVariants();
      syncEditorFromActive();
    } catch (error) {
      console.error("Failed to generate thumbnails:", error);
      showError("We couldn't generate thumbnails. Please try again.");
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
    }
  }

  function scheduleSave() {
    if (state.staleConflict) return;
    state.draftVersion += 1;
    if (state.saveTimer) clearTimeout(state.saveTimer);
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      setSaveStatus("saving");
      return;
    }
    setSaveStatus("dirty");
    state.saveTimer = setTimeout(() => {
      state.saveTimer = null;
      runSave();
    }, SAVE_DEBOUNCE_MS);
  }

  function handleEditorInput(event) {
    if (!state.draft) return;
    if (event.target.id === "headline-input") {
      state.draft.headline = event.target.value;
    } else if (event.target.dataset.color) {
      state.draft.palette[event.target.dataset.color] = event.target.value.toUpperCase();
    } else {
      return;
    }
    scheduleSave();
  }

  async function runSave() {
    if (state.staleConflict || !state.draft || !activeThumbnail()) return;
    if (state.saveStatus === "saving") {
      state.saveQueued = true;
      setSaveStatus("saving");
      return;
    }
    if (!state.draft.headline.trim()) {
      setSaveStatus("dirty", "Headline is required before re-rendering.");
      showError("Enter a headline before saving this thumbnail.");
      return;
    }
    if (state.saveTimer) {
      clearTimeout(state.saveTimer);
      state.saveTimer = null;
    }

    const thumbnail = activeThumbnail();
    const thumbnailId = thumbnail.id;
    const sentVersion = state.draftVersion;
    const payload = {
      revision: thumbnail.revision,
      headline: state.draft.headline.trim(),
      palette: clone(state.draft.palette),
    };
    state.saveQueued = false;
    clearError();
    setSaveStatus("saving");

    try {
      const updated = await Api.editThumbnail(state.projectId, thumbnailId, payload);
      state.thumbnails = state.thumbnails.map((item) =>
        item.id === thumbnailId ? updated : item
      );
      const hasNewerDraft = state.draftVersion !== sentVersion || state.saveQueued;
      renderVariants();
      updateEditorAssets(updated);
      if (hasNewerDraft) {
        state.saveQueued = false;
        setSaveStatus("dirty");
        await runSave();
      } else {
        state.staleConflict = false;
        state.draft = clone(updated.suggestion);
        byId("headline-input").value = state.draft.headline;
        setSaveStatus("saved");
      }
    } catch (error) {
      console.error("Failed to save thumbnail edit:", error);
      state.saveQueued = false;
      if (error.status === 409) {
        state.staleConflict = true;
        setSaveStatus("failed", "This thumbnail changed elsewhere — refresh to load the latest revision.");
        showError("This thumbnail changed in another request. Refresh the page before trying again.");
      } else {
        state.staleConflict = false;
        setSaveStatus("failed");
        showError("We couldn't save and re-render this thumbnail. Please click Retry.");
      }
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
      [state.templates, state.thumbnails] = await Promise.all([
        Api.listThumbnailTemplates(),
        Api.listThumbnails(state.projectId),
      ]);
      state.selectedTemplate = state.thumbnails[0]?.template_name || state.templates[0]?.id || null;
      state.activeId = state.thumbnails.find((thumbnail) => thumbnail.is_selected)?.id || null;
    } catch (error) {
      console.error("Failed to load thumbnail workspace:", error);
      state.loadFailed = true;
      byId("loading-panel").hidden = true;
      showError("We couldn't load existing thumbnails. Refresh before generating or editing.");
      return;
    }

    byId("loading-panel").hidden = true;
    byId("workspace").hidden = false;
    renderTemplates();
    renderVariants();
    syncEditorFromActive();
    setGenerateLoading(false);
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("theme-toggle").addEventListener("click", Theme.toggle);
    byId("generate-btn").addEventListener("click", generateThumbnails);
    byId("save-btn").addEventListener("click", runSave);
    byId("retry-save-btn").addEventListener("click", () => {
      if (state.staleConflict) {
        state.saveStatus = "saved";
        state.saveQueued = false;
        window.location.reload();
      } else {
        runSave();
      }
    });
    byId("headline-input").addEventListener("input", handleEditorInput);
    document.querySelectorAll("[data-color]").forEach((input) => {
      input.addEventListener("input", handleEditorInput);
    });
    byId("aspect-toggle").addEventListener("click", (event) => {
      const button = event.target.closest("[data-aspect]");
      if (!button || !activeThumbnail()) return;
      state.previewAspect = button.dataset.aspect;
      updateEditorAssets(activeThumbnail());
    });
    byId("download-grid").addEventListener("click", (event) => {
      const link = event.target.closest(".download-link");
      if (link && link.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
        showError("Wait for the current thumbnail edit to finish before downloading.");
      }
    });
    window.addEventListener("beforeunload", (event) => {
      if (hasUnresolvedEdit()) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    init();
  });
})();
