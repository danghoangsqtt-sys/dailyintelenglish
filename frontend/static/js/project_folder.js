/**
 * Topic-level project output settings, shared by Step 1 and Step 7.
 * New projects use Topic / Series / video folders; existing legacy settings stay in place
 * until the owner changes the folder or selects the hierarchical layout.
 */
(() => {
  const COMPONENTS = [
    ["video", "Video (YouTube) + subtitles", true],
    ["video_vertical", "Vertical video (TikTok)", false],
    ["thumbnail", "Thumbnail", true],
    ["youtube", "YouTube texts (titles, description, tags, pinned comment)", true],
    ["shorts", "Shorts / TikTok clips with covers and captions", false],
    ["audio", "Audio (MP3)", false],
    ["script", "Script", false],
    ["learning", "Learning pack (transcript, vocabulary, idioms…)", false],
  ];

  function mount(container, { projectId = null, actions = false } = {}) {
    container.innerHTML = `
      <div class="pf-row">
        <input type="text" class="pf-path" data-pf="path" placeholder="e.g. D:\\Videos\\Daily Beyond English"
               aria-label="Parent folder for this Topic" />
        <button type="button" class="btn btn-ghost btn-sm" data-pf="choose">📁 Choose folder…</button>
      </div>
      <label class="pf-layout-label" for="pf-layout">Folder organization</label>
      <select class="pf-layout" data-pf="layout" id="pf-layout">
        <option value="topic_hierarchy">Organize under Topic / Series / video</option>
        <option value="legacy">Use this folder directly for this project</option>
      </select>
      <p class="helper-text pf-hint">Choose a parent folder. The app creates a Topic folder, then Series and video folders when available.</p>
      <p class="helper-text pf-preview" data-pf="preview" aria-live="polite"></p>
      <fieldset class="pf-items"><legend>Save these in the folder</legend>
        ${COMPONENTS.map(([key, label, checked]) => `
          <label class="pf-item"><input type="checkbox" value="${key}" ${checked ? "checked" : ""} /> ${label}</label>`).join("")}
      </fieldset>
      ${actions ? `<div class="pf-row">
        <button type="button" class="btn btn-primary btn-sm" data-pf="save">💾 Save settings &amp; copy now</button>
        <button type="button" class="btn btn-ghost btn-sm" data-pf="open">📂 Open video folder</button>
        <button type="button" class="btn btn-ghost btn-sm" data-pf="stop">Stop saving here</button>
      </div>` : ""}
      <p class="helper-text pf-status" role="status"></p>`;

    const $ = (selector) => container.querySelector(selector);
    const pathInput = $('[data-pf="path"]');
    const layoutInput = $('[data-pf="layout"]');
    const status = (text) => { $(".pf-status").textContent = text || ""; };
    let originalDir = "";
    let originalMode = "topic_hierarchy";
    let previewRequest = 0;
    let saving = false;

    const settings = () => ({
      output_dir: pathInput.value.trim(),
      layout_mode: layoutInput.value,
      items: [...container.querySelectorAll(".pf-items input:checked")].map((input) => input.value),
    });

    async function refreshPreview() {
      const wanted = settings();
      const preview = $('[data-pf="preview"]');
      if (!wanted.output_dir) {
        preview.textContent = "Choose a parent folder to preview this project's destination.";
        return;
      }
      if (!projectId) {
        preview.textContent = wanted.layout_mode === "topic_hierarchy"
          ? `Destination: ${wanted.output_dir} / Topic / Series / video`
          : `Destination: ${wanted.output_dir}`;
        return;
      }
      const requestId = ++previewRequest;
      try {
        const result = await Api.previewProjectExport(projectId, wanted);
        if (requestId === previewRequest) preview.textContent = `Video folder: ${result.folder}`;
      } catch (error) {
        if (requestId === previewRequest) preview.textContent = `Folder preview unavailable: ${error.message}`;
      }
    }

    function show(view) {
      const saved = view?.settings;
      const root = saved?.output_dir || view?.suggested_dir || "";
      if (root) pathInput.value = root;
      layoutInput.value = saved?.layout_mode || view?.layout_mode || "topic_hierarchy";
      if (saved) {
        originalDir = saved.output_dir || "";
        originalMode = saved.layout_mode || "legacy";
        container.querySelectorAll(".pf-items input").forEach((input) => {
          input.checked = saved.items.includes(input.value);
        });
        const when = saved.last_sync_at ? new Date(saved.last_sync_at).toLocaleString() : "not yet";
        status(saved.last_error ? `Last copy failed: ${saved.last_error}` : `Last copied: ${when}`);
      } else if (view?.suggested_dir) {
        originalDir = "";
        originalMode = "topic_hierarchy";
        status("Using the saved parent folder for this Topic. Save to start exporting this project.");
      }
      refreshPreview();
    }

    async function save(id) {
      const wanted = settings();
      if (!wanted.output_dir) return null;
      if (!wanted.items.length) throw new Error("Tick at least one thing to save in the folder");
      if (saving) return null;
      saving = true;
      try {
        const view = await Api.saveProjectExport(id, wanted);
        show(view);
        const written = view.sync?.written || [];
        status(written.length ? `Saved ${written.length} file(s) in ${view.folder}.`
          : `Folder ready at ${view.folder}; selected files will be added as they are made.`);
        return view;
      } finally {
        saving = false;
      }
    }

    pathInput.addEventListener("input", () => {
      if (originalMode === "legacy" && pathInput.value.trim() !== originalDir) {
        layoutInput.value = "topic_hierarchy";
        $(".pf-hint").textContent = "Changing this project's save location opts it into Topic / Series / video folders. Files in its old folder stay there.";
      }
      refreshPreview();
    });
    layoutInput.addEventListener("change", refreshPreview);

    $('[data-pf="choose"]').addEventListener("click", async () => {
      status("Choose the parent folder in the window that opened…");
      try {
        const { path } = await Api.chooseProjectFolder(pathInput.value.trim() || null);
        if (path) {
          pathInput.value = path;
          pathInput.dispatchEvent(new Event("input", { bubbles: true }));
        }
        status(path ? "" : "No folder chosen: you can also type the path.");
      } catch (error) {
        status(error.message);
      }
    });

    if (actions) {
      $('[data-pf="save"]').addEventListener("click", async () => {
        try { await save(projectId); } catch (error) { status(error.message); }
      });
      $('[data-pf="open"]').addEventListener("click", async () => {
        try { await Api.openProjectExport(projectId); } catch (error) { status(error.message); }
      });
      $('[data-pf="stop"]').addEventListener("click", async () => {
        try {
          await Api.stopProjectExport(projectId);
          pathInput.value = "";
          layoutInput.value = "topic_hierarchy";
          originalDir = "";
          originalMode = "topic_hierarchy";
          status("This project no longer exports automatically. Files already saved are kept.");
          refreshPreview();
        } catch (error) { status(error.message); }
      });
    }
    if (projectId) Api.getProjectExport(projectId).then(show).catch(() => {});
    else refreshPreview();
    return { save, settings };
  }

  window.ProjectFolder = { mount };
})();
