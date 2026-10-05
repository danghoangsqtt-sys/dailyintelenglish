/**
 * Task 22.3 (D45): Step 4 "AI background music" card. The AI suggests a brief, the owner edits it,
 * 3 short previews are made, the owner uses one, and the full-length track is added to the Music
 * Library and selected in the episode's "Background music" dropdown (owned by step4_tts.js).
 */
(() => {
  const POLL_MS = 1500;
  const state = { projectId: null, view: null, options: null, busy: false, jobId: null };
  const byId = (id) => document.getElementById(id);

  function status(text, isError = false) {
    const element = byId("music-ai-status");
    element.textContent = text;
    element.style.color = isError ? "var(--danger)" : "";
  }

  function lengthSeconds() {
    return Math.round(Number(byId("music-ai-minutes").value || 0) * 60 + Number(byId("music-ai-seconds").value || 0));
  }

  function setLength(seconds) {
    byId("music-ai-minutes").value = Math.floor(seconds / 60);
    byId("music-ai-seconds").value = seconds % 60;
  }

  function formatSeconds(seconds) {
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  }

  function available() {
    return Boolean(state.options && state.options.available);
  }

  function applyBusy() {
    const busy = state.busy;
    ["music-ai-style", "music-ai-brief", "music-ai-minutes", "music-ai-seconds", "music-ai-suggest"].forEach((id) => {
      byId(id).disabled = busy;
    });
    byId("music-ai-make-previews").disabled = busy || !available();
    byId("music-ai-cancel").hidden = !(busy && state.jobId);
    document.querySelectorAll("#music-ai-previews [data-action='use']").forEach((button) => {
      button.disabled = busy || !available();
    });
  }

  function fillForm(view) {
    if (view.style) byId("music-ai-style").value = view.style;
    byId("music-ai-brief").value = view.brief || "";
    setLength(view.duration_s || view.default_duration_s);
  }

  function renderPreviews(view) {
    const list = byId("music-ai-previews");
    list.replaceChildren();
    view.previews.forEach((preview, index) => {
      const row = document.createElement("div");
      row.className = `music-ai-preview${preview.seed === view.picked_seed ? " is-picked" : ""}`;
      row.dataset.seed = preview.seed;
      const label = document.createElement("span");
      label.className = "music-ai-preview-label";
      label.textContent = `Preview ${index + 1}`;
      const player = document.createElement("audio");
      player.controls = true;
      player.preload = "none";
      player.src = preview.url;
      player.setAttribute("aria-label", `Music preview ${index + 1}`);
      const use = document.createElement("button");
      use.type = "button";
      use.className = "btn btn-primary btn-sm";
      use.dataset.action = "use";
      use.textContent = preview.seed === view.picked_seed ? "Used ✓" : "Use this";
      row.append(label, player, use);
      list.append(row);
    });
    applyBusy();
  }

  async function selectInDropdown(filename) {
    const select = byId("music-select");
    if (!select || !filename) return;
    if (![...select.options].some((option) => option.value === filename)) {
      select.append(new Option(filename, filename));
    }
    select.value = filename;
    select.dispatchEvent(new Event("change", { bubbles: true })); // step4_tts.js keeps its own state
  }

  function describeAttached(view) {
    if (view.track_filename && view.track_exists) {
      return `Attached: ${view.track_filename} (${formatSeconds(view.duration_s)}).`;
    }
    if (view.track_filename) return `The attached track ${view.track_filename} is no longer in the Music Library.`;
    return "";
  }

  function render(view) {
    state.view = view;
    renderPreviews(view);
    const attached = describeAttached(view);
    if (!state.busy) {
      if (attached) status(attached);
      else if (view.previews.length) status("Listen to the previews, then use the one you like.");
      else if (view.saved) status("Make 3 previews to hear this brief.");
      else status("Suggest a brief from the script, or choose a style and mood yourself.");
    }
  }

  async function reload() {
    const view = await Api.getProjectMusic(state.projectId);
    render(view);
    return view;
  }

  function jobLabel(job) {
    if (job.status === "pending") return "Queued — waiting for the GPU…";
    if (job.cancel_requested) return "Cancelling…";
    return `${job.stage || "Starting"}… ${job.progress || 0}%`;
  }

  function track(job) {
    state.busy = true;
    state.jobId = job.id;
    applyBusy();
    status(jobLabel(job));
    setTimeout(poll, POLL_MS);
  }

  async function poll() {
    if (!state.jobId) return;
    let job;
    try {
      job = await Api.getMusicJob(state.jobId);
    } catch (error) {
      console.error("Failed to read music job:", error);
      setTimeout(poll, POLL_MS * 2);
      return;
    }
    if (job.status === "pending" || job.status === "running") {
      status(jobLabel(job));
      setTimeout(poll, POLL_MS);
      return;
    }
    state.jobId = null;
    state.busy = false;
    applyBusy();
    let view;
    try {
      view = await reload();
    } catch (error) {
      console.error("Failed to reload project music:", error);
    }
    if (job.status === "error") {
      status(`Music generation failed: ${job.error || "unknown error"}`, true);
    } else if (job.status === "cancelled") {
      status("Cancelled.");
    } else if (job.kind === "music_previews" && JSON.parse(job.result_json || "{}").stale) {
      status("The brief changed while the previews were made — make new previews.");
    } else if (job.kind === "music_track" && view && view.track_exists) {
      await selectInDropdown(view.track_filename);
      status(`${describeAttached(view)} It is selected as this episode's background music.`);
    }
  }

  async function saveForm() {
    const body = {
      style: byId("music-ai-style").value,
      brief: byId("music-ai-brief").value,
      duration_s: lengthSeconds(),
    };
    const { min_duration_s: min, max_duration_s: max } = state.options;
    if (!Number.isFinite(body.duration_s) || body.duration_s < min || body.duration_s > max) {
      throw new Error(`Choose a length between ${formatSeconds(min)} and ${formatSeconds(max)}.`);
    }
    return Api.saveProjectMusic(state.projectId, body);
  }

  async function suggest() {
    if (state.busy) return;
    state.busy = true;
    applyBusy();
    status("Asking the AI for a brief…");
    try {
      const view = await Api.proposeProjectMusic(state.projectId);
      fillForm(view);
      state.busy = false;
      render(view);
      const proposal = view.proposal || {};
      if (proposal.path === "rule") {
        status(`The AI was unavailable, so a brief was chosen from the genre (${proposal.reason || "no reason"}). Edit it if you like.`);
      } else {
        status("Suggested by the AI. Edit it if you like, then make 3 previews.");
      }
    } catch (error) {
      console.error("Failed to suggest a music brief:", error);
      state.busy = false;
      status(`We couldn't suggest a brief: ${error.message}`, true);
    } finally {
      applyBusy();
    }
  }

  async function makePreviews() {
    if (state.busy) return;
    state.busy = true;
    applyBusy();
    status("Saving the brief…");
    try {
      render(await saveForm());
      track(await Api.makeMusicPreviews(state.projectId));
    } catch (error) {
      console.error("Failed to start music previews:", error);
      state.busy = false;
      applyBusy();
      status(error.message, true);
    }
  }

  async function useSeed(seed) {
    if (state.busy) return;
    state.busy = true;
    applyBusy();
    status("Saving the length…");
    try {
      // A new length alone keeps the previews; a changed style or mood would make them stale.
      const view = await saveForm();
      if (!view.previews.some((preview) => preview.seed === seed)) {
        state.busy = false;
        render(view);
        status("The style or mood changed, so these previews are gone — make new previews.", true);
        return;
      }
      track(await Api.makeFullMusic(state.projectId, seed));
    } catch (error) {
      console.error("Failed to start the full-length track:", error);
      state.busy = false;
      applyBusy();
      status(error.message, true);
    }
  }

  async function cancel() {
    if (!state.jobId) return;
    byId("music-ai-cancel").disabled = true;
    try {
      await Api.cancelMusicJob(state.jobId);
    } catch (error) {
      console.error("Failed to cancel the music job:", error);
    } finally {
      byId("music-ai-cancel").disabled = false;
    }
  }

  async function load() {
    state.projectId = new URLSearchParams(window.location.search).get("project_id");
    if (!state.projectId || !byId("music-ai-card")) return;
    byId("music-ai-suggest").addEventListener("click", suggest);
    byId("music-ai-make-previews").addEventListener("click", makePreviews);
    byId("music-ai-cancel").addEventListener("click", cancel);
    byId("music-ai-previews").addEventListener("click", (event) => {
      const button = event.target.closest("[data-action='use']");
      if (button) useSeed(Number(button.closest("[data-seed]").dataset.seed));
    });
    try {
      state.options = await Api.getMusicOptions();
      byId("music-ai-style").replaceChildren(...state.options.styles.map((style) => new Option(style.label, style.id)));
      if (!state.options.available) {
        const note = byId("music-ai-unavailable");
        note.textContent = `Making AI music is unavailable: ${state.options.unavailable_reason}`;
        note.hidden = false;
      }
      const view = await Api.getProjectMusic(state.projectId);
      fillForm(view);
      render(view);
      if (view.track_exists && !byId("music-select").value) await selectInDropdown(view.track_filename);
      const running = view.full_job || view.preview_job;
      if (running) track(running);
    } catch (error) {
      console.error("Failed to load AI music:", error);
      status("AI music could not be loaded. The music dropdown below still works.", true);
    }
    applyBusy();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const workspace = byId("workspace");
    // Only once the workspace is shown: step4_tts.js fills the music dropdown first, and a project
    // with no script never reaches this card.
    if (!workspace || !workspace.hidden) {
      load();
      return;
    }
    const observer = new MutationObserver(() => {
      if (!workspace.hidden) {
        observer.disconnect();
        load();
      }
    });
    observer.observe(workspace, { attributes: true, attributeFilter: ["hidden"] });
  });
})();
