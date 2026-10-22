/** Phase 67 (ENH-049): the review studio on the Automation page -- the 14-day schedule strip, the grid of made videos
 *  and the right panel that plays the selected video with its YouTube texts, thumbnails, script and details, to approve
 *  it in place. The settings, queue and run log stay in automation.js (the drawer below). */
(function () {
  const $ = (id) => document.getElementById(id);
  const STATE = { planned: "Planned", in_progress: "In progress", making: "Being made", waiting_review: "Waiting for review",
    needs_attention: "Needs attention", changes: "Needs changes", approved: "Approved", published: "Published" };
  const studio = { board: { days: [], videos: [] }, filter: "waiting_review", selected: null, tab: "youtube", cache: {} };

  const el = (tag, props = {}, children = []) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children.filter(Boolean));
    return node;
  };
  const dot = (state) => el("span", { className: `state-dot st-${state}` });
  const KPIS = [["due", "Due in 14 days", "#5B8DEF"], ["making", "Being made", "#E0A100"], ["waiting_review", "Waiting for review", "#1F9D57"],
    ["needs_attention", "Needs attention", "#E8483B"], ["published", "Published", "#3B4A44"]];
  const matches = (card, filter) => filter === "all" || card.state === filter || (filter === "needs_attention" && card.state === "changes");
  const minutes = (seconds) => seconds ? `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}` : "";
  const dayLabel = (iso, index) => index === 0 ? "Today" : index === 1 ? "Tomorrow"
    : new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
  const notice = (text, error = false) => { $("studio-notice").textContent = text; $("studio-notice").classList.toggle("is-error", error); };

  function thumb(card, className = "") {
    return card.thumbnail_url ? el("img", { src: card.thumbnail_url, alt: "", className, loading: "lazy" }) : el("span", { className: `ph ${className}` });
  }

  function renderKpis() {
    const days = studio.board.days, all = days.flatMap((day) => day.items);
    const count = (key) => key === "due" ? all.length : studio.board.videos.filter((card) => matches(card, key)).length
      + (key === "making" ? all.filter((card) => card.state === "making" && !card.project_id).length : 0);
    $("studio-kpis").replaceChildren(...KPIS.map(([key, label, colour]) => {
      const tile = el("button", { type: "button", className: "kpi" }, [el("b", { textContent: String(count(key)) }), el("span", { textContent: label })]);
      tile.style.setProperty("--kpi", colour);
      tile.dataset.kpi = key;
      tile.setAttribute("aria-pressed", String(key === studio.filter));
      tile.addEventListener("click", () => {
        if (key === "due") { $("studio-strip").scrollIntoView({ behavior: "smooth", block: "center" }); return; }
        studio.filter = key === "making" ? "all" : key;
        renderGrid();
        renderKpis();
      });
      return tile;
    }));
  }

  function renderStrip() {
    $("studio-strip").replaceChildren(...studio.board.days.map((day, index) => {
      const date = new Date(`${day.date}T00:00:00`);
      const weekday = index === 0 ? "Today" : index === 1 ? "Tomorrow" : date.toLocaleDateString(undefined, { weekday: "short" });
      return el("div", { className: `strip-day${index === 0 ? " today" : ""}` }, [
        el("h3", {}, [el("span", { className: "num", textContent: String(date.getDate()) }), el("span", { className: "wd", textContent: weekday }),
          day.items.length ? el("span", { className: "cnt", textContent: String(day.items.length) }) : null]),
        ...(day.items.length ? day.items.map((card) => {
          const chip = el("button", { type: "button", className: `strip-chip st-${card.state}`, title: `${card.series} · ${card.title} — ${STATE[card.state] || card.state}` },
            [thumb(card), el("span", { textContent: card.title })]);
          chip.dataset.state = card.state;
          chip.addEventListener("click", () => select(card.episode_id));
          return chip;
        }) : [el("div", { className: "empty", textContent: "—" })]),
      ]);
    }));
  }

  function renderGrid() {
    const shown = studio.board.videos.filter((card) => matches(card, studio.filter));
    $("studio-grid").replaceChildren(...shown.map((card) => {
      const button = el("button", { type: "button", className: `video-card st-${card.state}` }, [
        el("div", { className: "thumb" }, [card.thumbnail_url ? el("img", { src: card.thumbnail_url, alt: "", loading: "lazy" })
          : el("span", { className: "ph", textContent: card.has_video ? "▶" : STATE[card.state] || "" }),
          el("span", { className: "badge", textContent: STATE[card.state] || card.state }),
          card.duration ? el("span", { className: "dur", textContent: minutes(card.duration) }) : null,
          card.has_video ? el("span", { className: "play", ariaHidden: "true" }) : null]),
        el("div", { className: "meta" }, [el("b", { textContent: card.title }),
          el("span", { className: "kind-chip", textContent: card.kind }),
          el("small", { textContent: [card.publish_date, card.series].filter(Boolean).join(" · ") }),
          card.message ? el("small", { textContent: `⚠ ${card.step ? `${card.step}: ` : ""}${card.message}` }) : null]),
      ]);
      button.dataset.episode = card.episode_id;
      button.setAttribute("aria-selected", String(card.episode_id === studio.selected));
      button.addEventListener("click", () => select(card.episode_id));
      return button;
    }));
    $("studio-grid-empty").hidden = shown.length > 0;
    document.querySelectorAll("#studio-filters [data-filter]").forEach((chip) => {
      const count = studio.board.videos.filter((card) => chip.dataset.filter === "all" || card.state === chip.dataset.filter
        || (chip.dataset.filter === "needs_attention" && card.state === "changes")).length;
      chip.setAttribute("aria-pressed", String(chip.dataset.filter === studio.filter));
      chip.dataset.count = String(count);
      if (!chip.dataset.label) chip.dataset.label = chip.textContent.trim();
      chip.replaceChildren(document.createTextNode(chip.dataset.label), el("span", { className: "n", textContent: String(count) }));
    });
  }

  function card() {
    return studio.board.videos.find((item) => item.episode_id === studio.selected)
      || studio.board.days.flatMap((day) => day.items).find((item) => item.episode_id === studio.selected);
  }

  async function panelData(projectId) {
    if (!studio.cache[projectId]) {
      const [youtube, thumbnails, script] = await Promise.all([
        Api.getYoutubePackage(projectId).catch(() => null), Api.listThumbnails(projectId).catch(() => []), Api.getScript(projectId).catch(() => [])]);
      studio.cache[projectId] = { youtube, thumbnails: Array.isArray(thumbnails) ? thumbnails : [], script };
    }
    return studio.cache[projectId];
  }

  function copyBlock(label, text) {
    const button = el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Copy" });
    button.addEventListener("click", () => navigator.clipboard?.writeText(text).then(() => notice(`${label} copied.`), () => notice("Clipboard unavailable", true)));
    return el("section", { className: "copy-block" }, [el("header", {}, [el("span", { textContent: label }), button]), el("pre", { textContent: text })]);
  }

  async function renderBody() {
    const current = card();
    const body = $("review-body");
    document.querySelectorAll("[data-review-tab]").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.reviewTab === studio.tab)));
    if (!current) return;
    if (studio.tab === "details") {
      body.replaceChildren(
        el("p", { textContent: `${current.series} · Ep. ${current.number} · ${current.kind}` }),
        el("p", { textContent: `Publishing date: ${current.publish_date || "—"} · ${STATE[current.state] || current.state}` }),
        current.message ? el("p", { textContent: `Automation: ${current.step ? `${current.step} — ` : ""}${current.message}` }) : null,
        current.review_note ? el("p", { textContent: `Your note: ${current.review_note}` }) : null,
        current.video_url ? el("p", {}, [el("a", { href: current.video_url, target: "_blank", rel: "noopener", textContent: "On YouTube" })]) : null,
      );
      return;
    }
    if (!current.project_id) { body.replaceChildren(el("p", { className: "auto-hint", textContent: "Not made yet: Automation makes it before its date." })); return; }
    body.replaceChildren(el("p", { className: "auto-hint", textContent: "Loading…" }));
    const data = await panelData(current.project_id);
    if (card() !== current) return;
    if (studio.tab === "youtube") {
      const yt = data.youtube;
      body.replaceChildren(...(yt ? [
        ...(yt.titles || []).map((title, i) => copyBlock(`Title ${i + 1}${title.variant ? ` · ${title.variant}` : ""}`, title.text)),
        copyBlock("Description", yt.description || ""),
        copyBlock("Tags", (yt.tags || []).join(", ")),
        yt.hashtags_text ? copyBlock("Hashtags", yt.hashtags_text) : null,
        ...((yt.pinned_comments || []).map((comment, i) => copyBlock(`Pinned comment ${i + 1}`, typeof comment === "string" ? comment : comment.text || ""))),
      ].filter(Boolean) : [el("p", { className: "auto-hint", textContent: "No YouTube package yet." })]));
    } else if (studio.tab === "thumbnail") {
      body.replaceChildren(data.thumbnails.length ? el("div", { className: "thumb-row" }, data.thumbnails.map((item) => el("img", {
        src: item.assets?.["16x9"]?.jpg || item.assets?.["16x9"]?.png || "", alt: item.suggestion?.headline || "", className: item.is_selected ? "chosen" : "" })))
        : el("p", { className: "auto-hint", textContent: "No thumbnail yet." }));
    } else {
      body.replaceChildren(...(data.script.length ? data.script.map((line) => el("p", { textContent: line.text })) : [el("p", { className: "auto-hint", textContent: "No script yet." })]));
    }
  }

  function renderPanel() {
    const current = card();
    $("review-empty").hidden = Boolean(current);
    $("review-content").hidden = !current;
    if (!current) return;
    const video = $("review-video");
    video.className = `review-video${current.vertical ? " vertical" : ""}`;
    const src = current.has_video && current.project_id ? `/api/projects/${encodeURIComponent(current.project_id)}/video/download?format=mp4` : "";
    const playing = video.querySelector("video");
    if (!src) video.replaceChildren(el("div", { className: "review-empty", textContent: current.project_id ? "The video is not rendered yet." : "Not made yet." }));
    else if (!playing || playing.dataset.src !== src) {
      const player = el("video", { controls: true, preload: "metadata", src, poster: current.thumbnail_url || "" });
      player.dataset.src = src;
      video.replaceChildren(player);
    }
    $("review-title").textContent = current.title;
    $("review-meta").replaceChildren(dot(current.state), document.createTextNode(`${STATE[current.state] || current.state} · ${current.kind} · ${current.publish_date || ""}`));
    $("review-open").href = current.project_id ? `/step7?project_id=${encodeURIComponent(current.project_id)}` : "/channel";
    $("review-download").href = src || "#";
    $("review-download").hidden = !src;
    $("review-link").value = current.video_url || "";
    $("review-approve").disabled = !current.project_id || current.state === "approved" || current.state === "published";
    renderBody();
  }

  function select(episodeId) {
    studio.selected = episodeId;
    notice("");
    renderGrid();
    renderPanel();
  }

  async function refresh() {
    try {
      studio.board = await Api.getAutomationBoard();
      renderStrip();
      renderGrid();
      renderKpis();
      if (studio.selected) {
        const current = card();
        $("review-meta").replaceChildren(...(current ? [dot(current.state), document.createTextNode(`${STATE[current.state] || current.state} · ${current.kind} · ${current.publish_date || ""}`)] : []));
      }
      const next = $("studio-next");
      const view = await Api.getAutomation().catch(() => null);
      if (view) {
        const s = view.settings, current = view.status.current;
        next.textContent = current ? `Running: ${current.title} — ${current.step || "starting"}`
          : view.status.running ? "Running now."
          : s.enabled ? `Makes the due videos every night ${s.window_start}–${s.window_end}, at most ${s.max_per_night} a night.`
          : "Automatic production is off — switch it on to make videos at night.";
        $("studio-switch").checked = Boolean(s.enabled);
      }
    } catch { /* the next refresh tries again */ }
  }

  async function review(patch, done) {
    const current = card();
    if (!current) return;
    try {
      await Api.updateChannelEpisode(current.episode_id, patch);
      notice(done);
      await refresh();
      renderPanel();
    } catch (error) { notice(error.message || "Could not save.", true); }
  }

  document.querySelectorAll("#studio-filters [data-filter]").forEach((chip) => chip.addEventListener("click", () => { studio.filter = chip.dataset.filter; renderGrid(); renderKpis(); }));
  // the studio bar: the on/off switch saves through the settings form (automation.js), the drawer holds the settings
  $("studio-switch").addEventListener("change", () => {
    $("auto-enabled").checked = $("studio-switch").checked;
    $("auto-form").requestSubmit();
    setTimeout(refresh, 600);
  });
  const drawer = (open) => {
    $("settings-drawer").classList.toggle("open", open);
    $("settings-drawer").setAttribute("aria-hidden", String(!open));
    $("settings-backdrop").hidden = !open;
    $("open-settings").setAttribute("aria-expanded", String(open));
    if (open) $("auto-enabled").focus();
  };
  $("open-settings").addEventListener("click", () => drawer(true));
  $("close-settings").addEventListener("click", () => drawer(false));
  $("settings-backdrop").addEventListener("click", () => drawer(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && $("settings-drawer").classList.contains("open")) drawer(false); });
  $("cal-prev").addEventListener("click", () => $("studio-strip").scrollBy({ left: -440 }));
  $("cal-next").addEventListener("click", () => $("studio-strip").scrollBy({ left: 440 }));
  document.querySelectorAll("[data-review-tab]").forEach((tab) => tab.addEventListener("click", () => { studio.tab = tab.dataset.reviewTab; renderBody(); }));
  $("review-approve").addEventListener("click", () => review({ review_status: "approved", review_note: "" }, "Approved: ready to upload."));
  $("review-changes").addEventListener("click", () => {
    const note = window.prompt("What should change?", card()?.review_note || "");
    if (note === null) return;
    review({ review_status: "changes", review_note: note.trim() }, "Marked: needs changes. Open the step page to change it.");
  });
  $("review-published").addEventListener("click", () => {
    const link = $("review-link").value.trim();
    if (!link) { notice("Paste the YouTube link first.", true); return; }
    review({ status: "published", video_url: link }, "Marked published.");
  });

  refresh().then(() => {
    // open the first video waiting for review, else the first video
    const first = studio.board.videos.find((item) => item.state === "waiting_review") || studio.board.videos[0];
    if (!studio.board.videos.some((item) => item.state === "waiting_review")) studio.filter = "all";
    renderGrid();
    if (first) select(first.episode_id);
  });
  const timer = setInterval(refresh, 15000);
  window.addEventListener("pagehide", () => clearInterval(timer));
})();
