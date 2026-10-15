/**
 * Phase 41 (D120): the project's own output folder. One panel, used in Step 1 (choose it when the video starts) and Step 7
 * (change it, open it, save now). The owner ticks which components are written there; the app then copies every new
 * version of the ticked components automatically.
 *
 *   const panel = ProjectFolder.mount(container, { projectId, actions: true });
 *   await panel.save(projectId);   // Step 1, after the project exists
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
        <input type="text" class="pf-path" id="pf-path" placeholder="e.g. D:\\Videos\\Daily Beyond English\\Dinner Party"
               aria-label="Folder for this video project" />
        <button type="button" class="btn btn-ghost btn-sm" data-pf="choose">📁 Choose folder…</button>
      </div>
      <p class="helper-text">For a series, choose its shared folder. Each episode is saved automatically in its own Ep NN - Title subfolder.</p>
      <fieldset class="pf-items"><legend>Save these in the folder</legend>
        ${COMPONENTS.map(([key, label, checked]) => `
          <label class="pf-item"><input type="checkbox" value="${key}" ${checked ? "checked" : ""} /> ${label}</label>`).join("")}
      </fieldset>
      ${actions ? `<div class="pf-row">
        <button type="button" class="btn btn-primary btn-sm" data-pf="save">💾 Save settings &amp; copy now</button>
        <button type="button" class="btn btn-ghost btn-sm" data-pf="open">📂 Open folder</button>
        <button type="button" class="btn btn-ghost btn-sm" data-pf="stop">Stop saving here</button>
      </div>` : ""}
      <p class="helper-text pf-status" role="status"></p>`;
    const $ = (selector) => container.querySelector(selector);
    const status = (text) => { $(".pf-status").textContent = text || ""; };
    const settings = () => ({
      output_dir: $(".pf-path").value.trim(),
      items: [...container.querySelectorAll(".pf-items input:checked")].map((input) => input.value),
    });

    // ENH-035: an episode of a series saves into its own "Ep 02 - …" subfolder of the chosen (series) folder; a new
    // episode is offered the folder its series already uses.
    function show(view) {
      const saved = view?.settings;
      if (!saved) {
        if (view?.suggested_dir && !$(".pf-path").value) {
          $(".pf-path").value = view.suggested_dir;
          status("The folder of this series' other episodes: this episode gets its own subfolder inside it.");
        }
        return;
      }
      $(".pf-path").value = saved.output_dir || "";
      container.querySelectorAll(".pf-items input").forEach((input) => { input.checked = saved.items.includes(input.value); });
      const when = saved.last_sync_at ? new Date(saved.last_sync_at).toLocaleString() : "not yet";
      const where = view.folder && view.folder !== saved.output_dir ? ` · Files go to ${view.folder}` : "";
      status((saved.last_error ? `Last copy failed: ${saved.last_error}` : `Last copied: ${when}`) + where);
    }

    async function save(id) {
      const wanted = settings();
      if (!wanted.output_dir) return null;  // no folder: nothing is exported (optional)
      if (!wanted.items.length) throw new Error("Tick at least one thing to save in the folder");
      const view = await Api.saveProjectExport(id, wanted);
      show(view);
      const written = view.sync?.written || [];
      const where = view.folder ? ` (${view.folder})` : "";
      status(written.length ? `Saved ${written.length} file(s) in the folder${where}.`
        : `Folder ready${where}: files are added as you make them.`);
      return view;
    }

    $('[data-pf="choose"]').addEventListener("click", async () => {
      status("Choose the folder in the window that opened…");
      try {
        const { path } = await Api.chooseProjectFolder($(".pf-path").value.trim() || null);
        if (path) $(".pf-path").value = path;
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
          $(".pf-path").value = "";
          status("This project no longer saves to a folder (the files already there are kept).");
        } catch (error) {
          status(error.message);
        }
      });
    }
    if (projectId) Api.getProjectExport(projectId).then(show).catch(() => {});
    return { save, settings };
  }

  window.ProjectFolder = { mount };
})();
