/**
 * Step 7 — YouTube Package. Read-only display of AI-generated titles,
 * description, tags, and estimated chapters, plus a confirm-gated
 * Regenerate. No inline editing in this slice — see task-1.9.md.
 */
(() => {
  const VARIANT_LABELS = { click_worthy: "Click-worthy", educational: "Educational", seo: "SEO" };
  const VARIANT_ORDER = ["click_worthy", "educational", "seo"];

  const state = {
    projectId: null,
    project: null,
    package: null,
    packageLoadFailed: false,
    isGenerating: false,
    videoReady: false,
    thumbnailReady: false,
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
    banner.hidden = true;
    banner.textContent = "";
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

  function renderTitles() {
    const grid = byId("title-grid");
    grid.replaceChildren();
    const byVariant = Object.fromEntries(state.package.titles.map((title) => [title.variant, title.text]));
    VARIANT_ORDER.forEach((variant) => {
      const card = document.createElement("div");
      card.className = "title-card";
      const label = document.createElement("span");
      label.className = "title-variant-label";
      label.textContent = VARIANT_LABELS[variant] || variant;
      const text = document.createElement("p");
      text.className = "title-text";
      text.id = `title-text-${variant}`;
      text.textContent = byVariant[variant] || "";
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.className = "btn btn-ghost copy-btn";
      copyButton.dataset.copyTarget = `title-text-${variant}`;
      copyButton.textContent = "📋 Copy";
      card.append(label, text, copyButton);
      grid.appendChild(card);
    });
  }

  function renderTags() {
    const list = byId("tags-list");
    list.replaceChildren();
    state.package.tags.forEach((tag) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.textContent = tag;
      list.appendChild(chip);
    });
    byId("tags-text").textContent = state.package.tags.join(", ");
  }

  function render() {
    const generatePanel = byId("generate-panel");
    const contentWrap = byId("content-wrap");

    if (state.packageLoadFailed) {
      generatePanel.hidden = true;
      contentWrap.hidden = true;
      return;
    }

    if (!state.package) {
      generatePanel.hidden = false;
      contentWrap.hidden = true;
      return;
    }

    generatePanel.hidden = true;
    contentWrap.hidden = false;
    renderTitles();
    byId("description-text").textContent = state.package.description;
    byId("chapters-text").textContent = state.package.chapters_text;
    // Default to "Estimated" unless the backend explicitly says otherwise — never claim
    // "Measured" on a false-y/missing value (safer default than assuming precision).
    byId("chapters-estimate-note").textContent = state.package.chapters_estimated === false
      ? "✅ Measured from the final generated audio."
      : "⏱ Estimated from script length and reading speed — generate the audio in Step 4 for real measured timestamps.";
    renderTags();
    renderExportStatus();
  }

  function renderExportStatus() {
    const note = byId("export-status-note");
    const link = byId("export-zip-link");
    const canExport = state.videoReady && state.thumbnailReady;
    link.href = canExport ? Api.youtubeExportUrl(state.projectId) : "#";
    link.setAttribute("aria-disabled", canExport ? "false" : "true");
    if (canExport) {
      note.textContent = "Ready — includes the final video, thumbnail, subtitles, and metadata.";
    } else {
      const missing = [];
      if (!state.videoReady) missing.push("a generated video (Step 5)");
      if (!state.thumbnailReady) missing.push("a selected favorite thumbnail (Step 6)");
      note.textContent = `Not ready yet — still needs: ${missing.join(" and ")}.`;
    }
  }

  function setGenerateLoading(loading) {
    const button = byId("generate-btn");
    button.disabled = loading;
    button.textContent = loading ? "Generating…" : "✨ Generate YouTube Package";
    byId("regenerate-btn").disabled = loading;
  }

  async function handleGenerate() {
    if (state.isGenerating) return;
    state.isGenerating = true;
    clearError();
    setGenerateLoading(true);
    try {
      state.package = await Api.generateYoutubePackage(state.projectId);
      render();
    } catch (error) {
      console.error("Failed to generate YouTube package:", error);
      showError("We couldn't generate the YouTube package. Please try again.");
    } finally {
      state.isGenerating = false;
      setGenerateLoading(false);
    }
  }

  function handleRegenerate() {
    if (state.isGenerating) return;
    const confirmed = confirm(
      "This will overwrite the current titles, description, tags, and chapters with a brand new AI-generated version. Continue?"
    );
    if (confirmed) handleGenerate();
  }

  function handleCopyClick(event) {
    const button = event.target.closest("[data-copy-target]");
    if (!button) return;
    const target = byId(button.dataset.copyTarget);
    if (!target) return;
    navigator.clipboard.writeText(target.textContent).then(
      () => {
        const original = button.textContent;
        button.textContent = "✅ Copied";
        setTimeout(() => {
          button.textContent = original;
        }, 1500);
      },
      () => showError("Couldn't copy to clipboard — please select and copy the text manually.")
    );
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    state.projectId = params.get("project_id");
    if (!state.projectId) {
      showError("Missing project. Please start from the Dashboard.");
      return;
    }

    try {
      state.project = await Api.getProject(state.projectId);
      renderHeader();
    } catch (error) {
      console.error("Failed to load project:", error);
      showError("We couldn't load this project. Please go back to the Dashboard.");
      return;
    }

    try {
      state.package = await Api.getYoutubePackage(state.projectId);
      state.packageLoadFailed = false;
    } catch (error) {
      console.error("Failed to load existing YouTube package:", error);
      state.packageLoadFailed = true;
      showError("We couldn't load the existing YouTube package. Please try refreshing.");
    }

    try {
      const videoStatus = await Api.getVideoStatus(state.projectId);
      state.videoReady = videoStatus.status === "complete";
    } catch (error) {
      state.videoReady = false; // 404 (no video yet) is expected, not an error to surface
    }

    try {
      const thumbnails = await Api.listThumbnails(state.projectId);
      state.thumbnailReady = thumbnails.some((thumbnail) => thumbnail.is_selected);
    } catch (error) {
      state.thumbnailReady = false;
    }

    render();
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("theme-toggle").addEventListener("click", Theme.toggle);
    byId("generate-btn").addEventListener("click", handleGenerate);
    byId("regenerate-btn").addEventListener("click", handleRegenerate);
    document.body.addEventListener("click", handleCopyClick);
    init();
  });
})();
