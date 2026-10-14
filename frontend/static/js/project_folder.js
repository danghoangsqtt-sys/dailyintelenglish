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

  async function call(url, method = "GET", body) {
    const response = await fetch(url, {
      method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
    });
    const envelope = await response.json().catch(() => ({}));
    if (!response.ok || envelope.success === false) {
      const detail = Array.isArray(envelope.detail) ? envelope.detail.map((item) => item.msg).join(" ") : envelope.detail;
      throw new Error(envelope.error || detail || "Request failed");
    }
    return envelope.data;
  }

  function mount(container, { projectId = null, actions = false } = {}) {
    container.innerHTML = `
      <div class="pf-row">
        <input type="text" class="pf-path" id="pf-path" placeholder="e.g. D:\\Videos\\Daily Beyond English\\Episode 1"
               aria-label="Folder for this video project" />
        <button type="button" class="btn btn-ghost btn-sm" data-pf="choose">📁 Choose folder…</button>
      </div>
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

    function show(saved) {
      if (!saved) return;
      $(".pf-path").value = saved.output_dir || "";
      container.querySelectorAll(".pf-items input").forEach((input) => { input.checked = saved.items.includes(input.value); });
      const when = saved.last_sync_at ? new Date(saved.last_sync_at).toLocaleString() : "not yet";
      status(saved.last_error ? `Last copy failed: ${saved.last_error}` : `Last copied: ${when}`);
    }

    async function save(id) {
      const wanted = settings();
      if (!wanted.output_dir) return null;  // no folder: nothing is exported (optional)
      if (!wanted.items.length) throw new Error("Tick at least one thing to save in the folder");
      const view = await call(`/api/projects/${id}/export`, "PUT", wanted);
      show(view.settings);
      const written = view.sync?.written || [];
      status(written.length ? `Saved ${written.length} file(s) in the folder.` : "Folder ready: files are added as you make them.");
      return view;
    }

    $('[data-pf="choose"]').addEventListener("click", async () => {
      status("Choose the folder in the window that opened…");
      try {
        const { path } = await call("/api/system/choose-folder", "POST", { initial: $(".pf-path").value.trim() || null });
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
        try { await call(`/api/projects/${projectId}/export/open`, "POST"); } catch (error) { status(error.message); }
      });
      $('[data-pf="stop"]').addEventListener("click", async () => {
        try {
          await call(`/api/projects/${projectId}/export`, "DELETE");
          $(".pf-path").value = "";
          status("This project no longer saves to a folder (the files already there are kept).");
        } catch (error) {
          status(error.message);
        }
      });
    }
    if (projectId) call(`/api/projects/${projectId}/export`).then((view) => show(view.settings)).catch(() => {});
    return { save, settings };
  }

  window.ProjectFolder = { mount };
})();
