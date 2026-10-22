/** Phase 62 (ENH-044): the Automation page -- the night window, the queue of due episodes, Run now / Stop and the report
 *  of the last runs. The runner itself lives in the backend; this page only reads and changes its settings. */
(function () {
  const $ = (id) => document.getElementById(id);
  const STATUS = { running: "Working", waiting_review: "Waiting for review", needs_attention: "Needs your attention", error: "Error" };
  const KIND = { classic: "Conversation", presenter: "Solo", vox: "VOX", news: "Short · news", blur: "Short · blur",
    mistakes: "Short · don't say", wordday: "Short · word", top5: "Short · top 5" };
  const RUN = { running: "Running", done: "Finished", stopped: "Stopped", error: "Could not start" };
  let view = null;
  let timer = null;

  function notice(text, error = false) {
    $("auto-notice").textContent = text;
    $("auto-notice").classList.toggle("is-error", error);
  }

  function when(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderSettings(settings, startupAvailable) {
    $("auto-enabled").checked = settings.enabled;
    $("auto-start").value = settings.window_start;
    $("auto-end").value = settings.window_end;
    $("auto-days").value = settings.days_ahead;
    $("auto-max").value = settings.max_per_night;
    $("auto-awake").checked = settings.keep_awake;
    $("auto-startup").checked = settings.start_with_windows;
    $("auto-startup").disabled = !startupAvailable;
    $("auto-startup-hint").hidden = startupAvailable;
  }

  function renderStatus(status, settings) {
    const busy = Boolean(status.current);
    $("auto-dot").className = `auto-dot${busy ? " busy" : settings.enabled || status.running ? " on" : ""}`;
    $("auto-state-text").textContent = busy ? "Working" : status.running ? "Running" : settings.enabled
      ? `On · ${settings.window_start}–${settings.window_end}` : "Off";
    const current = status.current;
    $("auto-current").textContent = current
      ? `Now: ${current.series || ""} · Ep. ${current.number}: ${current.title} — ${current.step || "starting"}` : "";
    $("auto-stop").disabled = !status.running && !status.manual;
    $("auto-run-now").disabled = status.running || status.manual;
  }

  function renderQueue(queue) {
    const list = $("auto-queue");
    list.replaceChildren(...queue.map((item) => {
      const row = el("li");
      row.append(el("span", "date", item.publish_date || ""), el("span", "grow", `${item.series} · Ep. ${item.number}: ${item.title}`),
        el("span", "auto-badge", KIND[item.presentation_mode === "solo_explainer" ? item.explainer_style || "presenter" : "classic"] || "Solo"));
      if (item.project_id) {
        const link = el("a", "", "Open");
        link.href = `/step2?project_id=${encodeURIComponent(item.project_id)}`;
        row.append(link);
      }
      return row;
    }));
    $("auto-queue-empty").hidden = queue.length > 0;
  }

  function renderReport(runs) {
    $("auto-report").replaceChildren(...runs.map((run) => {
      const block = el("div", "auto-run");
      const counts = run.items.reduce((acc, item) => ({ ...acc, [item.status]: (acc[item.status] || 0) + 1 }), {});
      const summary = [`${counts.waiting_review || 0} ready`];
      if (counts.needs_attention) summary.push(`${counts.needs_attention} need attention`);
      if (counts.error) summary.push(`${counts.error} error`);
      block.append(el("h3", "", `${when(run.started_at)} · ${run.trigger === "manual" ? "Run now" : "Night"} · ${RUN[run.status] || run.status} · ${summary.join(", ")}`));
      if (run.message) block.append(el("p", "auto-hint", run.message));
      const list = el("ul", "auto-list");
      run.items.forEach((item) => {
        const row = el("li");
        row.dataset.status = item.status;
        row.append(el("span", `auto-badge ${item.status}`, STATUS[item.status] || item.status), el("span", "grow", item.title));
        if (item.step_label && item.status !== "waiting_review") row.append(el("span", "auto-hint", item.step_label));
        const link = el("a", "", item.status === "waiting_review" ? "Review" : "Open");
        link.href = item.link;
        row.append(link);
        if (item.message) row.append(el("span", "auto-message", item.message));
        list.append(row);
      });
      block.append(list);
      return block;
    }));
    $("auto-report-empty").hidden = runs.length > 0;
  }

  function render(next) {
    view = next;
    renderSettings(view.settings, view.startup_available);
    renderStatus(view.status, view.settings);
    renderQueue(view.queue);
    renderReport(view.runs);
  }

  async function load() {
    try {
      render(await Api.getAutomation());
    } catch (error) {
      notice(error.message || "Automation could not load.", true);
    }
  }

  async function refreshStatus() {
    try {
      const next = await Api.getAutomation();
      view = next;
      renderStatus(next.status, next.settings);
      renderQueue(next.queue);
      renderReport(next.runs);
    } catch {
      /* the next poll tries again */
    }
  }

  $("auto-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const patch = {
      enabled: $("auto-enabled").checked, window_start: $("auto-start").value, window_end: $("auto-end").value,
      days_ahead: Number($("auto-days").value), max_per_night: Number($("auto-max").value), keep_awake: $("auto-awake").checked,
    };
    if (!$("auto-startup").disabled) patch.start_with_windows = $("auto-startup").checked;
    try {
      render(await Api.saveAutomationSettings(patch));
      notice("Saved.");
    } catch (error) {
      notice(error.message || "Could not save.", true);
    }
  });
  $("auto-run-now").addEventListener("click", async () => {
    try {
      render(await Api.runAutomationNow());
      notice("Started: the due episodes are being made now.");
    } catch (error) {
      notice(error.message || "Could not start.", true);
    }
  });
  $("auto-stop").addEventListener("click", async () => {
    try {
      render(await Api.stopAutomation());
      notice("Stopping after the current step.");
    } catch (error) {
      notice(error.message || "Could not stop.", true);
    }
  });

  load();
  timer = setInterval(refreshStatus, 5000);
  window.addEventListener("pagehide", () => clearInterval(timer));
})();
