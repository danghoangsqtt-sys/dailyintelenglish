/** Phase 66 (ENH-048): the Shorts batch page -- AI ideas from one topic, or today's news with the AI's picks; the
 *  reviewed list is saved as a dated Channel plan series (the night Automation makes it), optionally with projects now. */
(function () {
  const $ = (id) => document.getElementById(id);
  // Phase 80 (owner 2026-10-26): the kinds of video as cards -- the app's video types, then the text templates
  const KINDS = [
    { key: "conversation", name: "Conversation", group: "Video types", cast: 2, desc: "Two talking characters in an everyday situation." },
    { key: "presenter", name: "Solo presenter", group: "Video types", cast: 1, desc: "One presenter explains one idea to camera." },
    { key: "vox", name: "Vox", group: "Video types", cast: 1, desc: "A narrator's voice over pictures and on-screen text." },
    { key: "wordday", name: "Word of the day", group: "Text templates", cast: 1, desc: "One word: meaning, pronunciation, examples, a memory tip." },
    { key: "mistakes", name: "Don't say / Say", group: "Text templates", cast: 1, desc: "Common learner mistakes and the natural phrase." },
    { key: "top5", name: "Top 5 phrases", group: "Text templates", cast: 1, desc: "Five phrases for one situation, as a countdown." },
    { key: "quiz", name: "Countdown quiz", group: "Text templates", cast: 1, desc: "Two or three questions with a countdown." },
    { key: "listen", name: "Listening challenge", group: "Text templates", cast: 1, desc: "Everyday sentences at natural speed." },
    { key: "blur", name: "Text on blur", group: "Text templates", cast: 1, desc: "A short story or lesson in big words." },
    { key: "news", name: "English news", group: "Text templates", cast: 1, desc: "One news story in simple English." },
    { key: "slowpod", name: "Slow English podcast", group: "Text templates", cast: 1, desc: "A slow monologue, one sentence per screen with its Vietnamese." },
    { key: "flashcards", name: "Vocabulary flashcards", group: "Text templates", cast: 1, desc: "8–10 word cards: part of speech, IPA, Vietnamese meaning." },
    { key: "roots", name: "Word roots, prefixes & suffixes", group: "Text templates", cast: 1, desc: "One root, prefix or suffix and its word family, explained in Vietnamese." },
    { key: "grammar", name: "Easy grammar", group: "Text templates", cast: 1, desc: "One grammar point per Short, explained by its essence in Vietnamese, with a summary table." },
    { key: "chat", name: "Chat", group: "Text templates", cast: 2, desc: "A text-message conversation of two characters." },
    { key: "wyr", name: "Would you rather", group: "Text templates", cast: 2, desc: "Questions answered by the second character." },
  ];
  const TEMPLATES = KINDS.map((kind) => [kind.key, kind.name]);
  const NO_SAMPLE = ["conversation", "presenter", "vox"];  // made with characters / a presenter / pictures: no silent sample
  const POLL_MS = 3000;
  const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const state = { tab: "topic", template: "wordday", items: [], stories: [], feeds: [], profiles: [], selected: 0, player: null, timer: null,
    mainFolder: null, results: null, poll: null };

  // Phase 68 (ENH-050): the live 9:16 preview of the template with the selected idea (silent, nothing saved)
  function previewIdea() {
    const item = state.items[state.selected];
    if (item) return { title: item.title || "Your Short", brief: item.brief || "" };
    const topic = ($("batch-topic")?.value || "").trim();
    return { title: topic || "Your idea appears here", brief: state.tab === "news" ? "Today's story, told in simple English." : "Propose ideas to see them here." };
  }

  function refreshPreview() {
    clearTimeout(state.timer);
    state.timer = setTimeout(() => {
      const box = $("batch-player");
      const idea = previewIdea();
      if (NO_SAMPLE.includes(state.template)) {  // Phase 80: these are drawn from characters, a presenter or pictures
        $("preview-what").textContent = `${KINDS.find((kind) => kind.key === state.template).name} · ${idea.title}`;
        $("batch-player").replaceChildren();
        state.player = null;
        $("preview-error").textContent = "No silent preview for this kind: make one video and watch it in the results.";
        return;
      }
      if (!window.SoloPreview || !window.ShortsSample) { $("preview-error").textContent = "The preview player is not available."; return; }
      const level = state.tab === "news" ? $("news-level").value : $("batch-level").value;
      const label = TEMPLATES.find(([key]) => key === state.template)?.[1] || state.template;
      $("preview-what").textContent = `${label} · ${idea.title}`;
      try {
        const props = window.ShortsSample.props(state.template, idea, level, $("batch-audience").value || state.channelAudience || "both");
        if (state.player) state.player.update(props); else state.player = window.SoloPreview.mount(box, props);
        // show a moment with the template's content at once (frame 0 is still empty); Play shows the whole sample
        setTimeout(() => state.player?.seek(Math.round(props.fps * 2.2)), 120);
        $("preview-error").textContent = "";
      } catch (error) {
        $("preview-error").textContent = error.message || "The preview could not be drawn.";
      }
    }, 250);
  }

  const el = (tag, props = {}, children = []) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children.filter((child) => child !== null && child !== undefined));  // Phase 80: no "null" text
    return node;
  };
  const notice = (id, text, error = false) => { $(id).textContent = text; $(id).classList.toggle("is-error", error); };
  const twoCharacters = () => (KINDS.find((kind) => kind.key === state.template)?.cast || 1) === 2;

  function fillSelect(select, options, value) {
    select.replaceChildren(...options.map(([key, label]) => el("option", { value: key, textContent: label })));
    if (value) select.value = value;
  }

  function renderItems() {
    $("batch-items").replaceChildren(...state.items.map((item, index) => {
      const title = el("input", { type: "text", value: item.title, maxLength: 120, ariaLabel: "Title" });
      title.addEventListener("input", () => { item.title = title.value; if (index === state.selected) refreshPreview(); });
      const brief = el("input", { type: "text", value: item.brief, maxLength: 600, ariaLabel: "What it covers", className: "brief" });
      brief.addEventListener("input", () => { item.brief = brief.value; if (index === state.selected) refreshPreview(); });
      const remove = el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Remove" });
      remove.addEventListener("click", (event) => {
        event.stopPropagation();
        state.items.splice(index, 1);
        state.selected = Math.min(state.selected, Math.max(0, state.items.length - 1));
        renderItems();
        refreshPreview();
      });
      const row = el("li", { className: index === state.selected ? "is-selected" : "" },
        [el("span", { className: "batch-badge", textContent: String(index + 1) }), title, remove, brief]);
      row.addEventListener("click", () => {
        if (state.selected === index) return;
        state.selected = index;
        document.querySelectorAll("#batch-items li").forEach((other, at) => other.classList.toggle("is-selected", at === index));
        refreshPreview();
      });
      if (item.source_text) row.append(el("span", { className: "meta", textContent: `Article: ${item.source_text.split(/\s+/).length} words · ${item.url || ""}` }));
      if (item.error) row.append(el("span", { className: "meta", textContent: `⚠ ${item.error}` }));
      return row;
    }));
    $("batch-empty").hidden = state.items.length > 0;
  }

  function renderCast() {
    const options = state.profiles.map((profile) => [profile.id, profile.name]);
    fillSelect($("batch-cast-0"), options, $("batch-cast-0").value);
    fillSelect($("batch-cast-1"), options, $("batch-cast-1").value || options[1]?.[0]);
    $("cast-one-label").firstChild.textContent = twoCharacters() ? "First character" : state.template === "presenter" ? "Presenter" : "Narrator";
    $("cast-two-label").hidden = !twoCharacters();
    $("cast-note").textContent = state.template === "presenter"
      ? "The presenter needs a complete front picture pack (Character Library)."
      : state.template === "conversation" ? "Both characters need their talking pictures (Character Library)." : "";
  }

  function renderKinds() {
    const grid = $("template-grid");
    const nodes = [];
    let group = "";
    KINDS.forEach((kind) => {
      if (kind.group !== group) { group = kind.group; nodes.push(el("p", { className: "template-group", textContent: group })); }
      const card = el("button", { type: "button", className: "template-card", role: "radio" }, [
        el("span", { className: "t-name", textContent: kind.name }), el("span", { className: "t-desc", textContent: kind.desc }),
        el("span", { className: "t-cast", textContent: kind.cast === 2 ? "2 characters" : kind.key === "presenter" ? "presenter" : "narrator" })]);
      card.dataset.template = kind.key;
      card.setAttribute("aria-checked", String(kind.key === state.template));
      card.addEventListener("click", () => setTemplate(kind.key));
      nodes.push(card);
    });
    grid.replaceChildren(...nodes);
    // Phase 92: an example clip on every kind card
    window.TemplateSamples?.attach(grid, { audience: $("batch-audience").value || state.channelAudience });
  }

  function setTemplate(key) {
    if (state.tab === "news" && key !== "news") setTab("topic");
    state.template = key;
    $("batch-template").value = key;
    document.querySelectorAll("#template-grid .template-card").forEach((card) => card.setAttribute("aria-checked", String(card.dataset.template === key)));
    renderCast();
    refreshPreview();
  }

  /** Where the batch's videos will be saved (the main save folder, by topic and series). */
  function renderSaveWhere() {
    const playlist = $("batch-playlist").value.trim() || "Shorts";
    const series = $("batch-series").value.trim() || "Series";
    $("save-where").textContent = state.mainFolder
      ? `Saved in: ${state.mainFolder}\\${playlist}\\${series}\\Ep NN - title`
      : "No main save folder yet: choose one above. Until then the videos stay inside the app; download them from the results.";
  }

  function setTab(tab) {
    state.tab = tab;
    $("topic-panel").hidden = tab !== "topic";
    $("news-panel").hidden = tab !== "news";
    document.querySelectorAll("[data-tab]").forEach((button) => {
      const selected = button.dataset.tab === tab;
      button.setAttribute("aria-selected", String(selected));
      button.className = `btn btn-${selected ? "primary" : "ghost"} btn-sm`;
    });
    if (tab === "news") { state.template = "news"; if (!state.feeds.length) loadFeeds(); }
    else if (state.template === "news") state.template = "wordday";
    $("batch-template").value = state.template;
    document.querySelectorAll("#template-grid .template-card").forEach((card) => card.setAttribute("aria-checked", String(card.dataset.template === state.template)));
    renderCast();
    refreshPreview();
  }

  function storyRow(story, index) {
    const check = el("input", { type: "checkbox", checked: Boolean(story.chosen), ariaLabel: "Use this story" });
    check.addEventListener("change", () => { story.chosen = check.checked; });
    const title = el("a", { href: story.link, target: "_blank", rel: "noopener", textContent: story.title });
    const when = story.published ? new Date(story.published).toLocaleString() : "";
    const row = el("li", {}, [check, title, el("span", { className: "batch-badge", textContent: story.source })]);
    row.dataset.story = String(index);  // dataset is read-only: Object.assign cannot set it
    if (story.hook) row.append(el("span", { className: "hook", textContent: `✨ ${story.hook}${story.why ? ` — ${story.why}` : ""}` }));
    row.append(el("span", { className: "meta", textContent: [when, story.summary].filter(Boolean).join(" · ") }));
    return row;
  }

  function renderStories() { $("news-list").replaceChildren(...state.stories.map(storyRow)); }

  async function loadNews() {
    notice("news-notice", "Reading the feeds…");
    try {
      const result = await Api.getTodayNews();
      state.stories = result.stories;
      renderStories();
      const problems = result.problems.map((item) => `${item.feed}: ${item.error}`).join("; ");
      notice("news-notice", `${result.stories.length} stories from the last 36 hours.${problems ? ` Not read: ${problems}` : ""}`, Boolean(problems) && !result.stories.length);
    } catch (error) { notice("news-notice", error.message || "The news could not be read.", true); }
  }

  async function aiPicks() {
    notice("news-notice", "The AI is choosing the best stories for learners…");
    try {
      const { picks } = await Api.getNewsPicks({ cefr_level: $("news-level").value, count: Number($("batch-count").value) || 5 });
      const byLink = new Map(picks.map((pick) => [pick.link, pick]));
      state.stories.forEach((story) => { const pick = byLink.get(story.link); story.chosen = Boolean(pick); story.hook = pick?.hook; story.why = pick?.why; });
      if (!state.stories.length) state.stories = picks.map((pick) => ({ ...pick, chosen: true }));
      state.stories.sort((a, b) => Number(Boolean(b.chosen)) - Number(Boolean(a.chosen)));
      renderStories();
      notice("news-notice", `${picks.length} stories chosen by the AI. Check them, then read their articles.`);
    } catch (error) { notice("news-notice", error.message || "The AI could not choose; tick stories yourself.", true); }
  }

  async function useStories() {
    const chosen = state.stories.filter((story) => story.chosen);
    if (!chosen.length) { notice("news-notice", "Tick the stories to use first.", true); return; }
    notice("news-notice", `Reading ${chosen.length} article(s)…`);
    try {
      const { articles } = await Api.readNewsArticles(chosen.map((story) => story.link));
      state.items = chosen.map((story, i) => ({ title: (story.title || "").slice(0, 120), brief: story.hook || story.summary || "",
        source_text: articles[i]?.text || "", url: story.link, error: articles[i]?.error || "" }));
      state.selected = 0;
      renderItems();
      refreshPreview();
      if (!$("batch-series").value) $("batch-series").value = `English News · ${new Date().toLocaleDateString()}`;
      const unread = articles.filter((article) => article.error).length;
      notice("news-notice", unread ? `${unread} article(s) could not be read; those Shorts use the headline only.` : "Articles read. Review the list below and create the batch.");
    } catch (error) { notice("news-notice", error.message || "The articles could not be read.", true); }
  }

  async function loadFeeds() {
    try { state.feeds = (await Api.getNewsFeeds()).feeds; renderFeeds(); } catch { /* the box stays empty */ }
  }

  function renderFeeds() {
    $("feeds-list").replaceChildren(...state.feeds.map((feed, index) => {
      const enabled = el("input", { type: "checkbox", checked: feed.enabled, ariaLabel: "Use this feed" });
      enabled.addEventListener("change", () => { feed.enabled = enabled.checked; });
      const remove = el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Remove" });
      remove.addEventListener("click", () => { state.feeds.splice(index, 1); renderFeeds(); });
      return el("li", {}, [enabled, el("span", { textContent: `${feed.name} — ${feed.url}` }), remove]);
    }));
  }

  $("ideas-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    notice("batch-notice", "The AI is writing the ideas…");
    try {
      const { ideas } = await Api.proposeBatchIdeas({ topic: $("batch-topic").value.trim(), template: state.template,
        count: Number($("batch-count").value), cefr_level: $("batch-level").value, hint: $("batch-hint").value.trim() });
      state.items = ideas.map((idea) => ({ ...idea, source_text: "" }));
      state.selected = 0;
      renderItems();
      refreshPreview();
      if (!$("batch-series").value) $("batch-series").value = $("batch-topic").value.trim().slice(0, 100);
      renderSaveWhere();
      notice("batch-notice", `${ideas.length} ideas. Edit or remove them, then create the batch.`);
    } catch (error) { notice("batch-notice", error.message || "The AI could not propose ideas.", true); }
  });

  $("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const items = state.items.filter((item) => item.title.trim());
    if (!items.length) { notice("batch-notice", "Propose or choose the Shorts first.", true); return; }
    const cast = [$("batch-cast-0").value, ...(twoCharacters() ? [$("batch-cast-1").value] : [])].filter(Boolean);
    const now = event.submitter?.dataset.make !== "plan";
    try {
      const result = await Api.createBatch({ topic_name: $("batch-playlist").value.trim(), series_name: $("batch-series").value.trim(),
        template: state.template, cast, cefr_level: state.tab === "news" ? $("news-level").value : $("batch-level").value,
        start_date: $("batch-start").value, every_days: Number($("batch-every").value) || 1, make_projects: now,
        ...($("batch-audience").value ? { audience: $("batch-audience").value } : {}),
        items: items.map(({ title, brief, source_text }) => ({ title: title.trim(), brief: (brief || "").trim(), source_text: source_text || "" })) });
      notice("batch-notice", `Created: ${result.episodes} Shorts dated ${result.first_date} → ${result.last_date}`
        + (result.projects ? `, ${result.projects} projects made.` : ". Automation makes them before their dates."));
      if (now) {
        await Api.makeBatch(result.series_id);
        notice("batch-notice", `Making ${result.episodes} videos now, one after another. Follow them in the results below.`);
      }
      await loadBatches(result.series_id);
      $("results-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { notice("batch-notice", error.message || "The batch could not be created.", true); }
  });


  // ---------------------------------------------------------------- results (Phase 80)
  const STATUS = { planned: "Planned", running: "Making…", waiting_review: "Ready", video_ready: "Video made", needs_attention: "Needs you",
    error: "Failed" };
  const STEP = { project: "project", script: "script", learning: "lesson", audio: "voice", visual_plan: "visual plan", video: "video",
    thumbnail: "thumbnail", youtube: "YouTube texts" };

  async function loadBatches(select) {
    try {
      const { series } = await Api.listBatches();
      const box = $("results-series");
      box.replaceChildren(...series.map((item) => el("option", { value: item.id,
        textContent: `${item.name} · ${item.episodes} · ${item.topic}${item.running ? " · making…" : ""}` })));
      const chosen = select || series.find((item) => item.running)?.id || series[0]?.id;
      if (chosen) { box.value = chosen; await showResults(chosen); }
    } catch { /* the panel keeps "No batch yet" */ }
  }

  function tile(item) {
    const media = item.video_url
      ? el("video", { src: item.video_url, controls: true, preload: "metadata" })
      : el("div", { className: "result-empty", textContent: item.status === "running" ? `Making the ${STEP[item.step] || "video"}…`
        : item.status === "planned" ? "Not made yet" : item.status === "waiting_review" ? "Ready (no video file)" : "No video" });
    const status = el("span", { className: `result-status is-${item.status}`, textContent: STATUS[item.status] || item.status });
    const actions = el("div", { className: "result-actions" }, [
      item.video_url ? el("a", { className: "btn btn-ghost btn-sm", href: item.video_url, download: "", textContent: "⬇ MP4" }) : null,
      item.folder ? el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "📂 Open folder",
        onclick: () => Api.openProjectExport(item.project_id).catch((error) => { $("results-summary").textContent = error.message; }) }) : null,
      item.project_id ? el("a", { className: "btn btn-ghost btn-sm", href: `/step5?project_id=${encodeURIComponent(item.project_id)}`,
        textContent: "Open project" }) : null,
    ]);
    const folder = el("p", { className: "result-folder", textContent: item.folder ? item.folder : item.project_id ? "Saved inside the app (no folder)" : "" });
    if (item.folder) folder.setAttribute("translate", "no");  // a real path is never translated
    const title = el("h3", { textContent: `${item.number}. ${item.title}` });
    title.setAttribute("translate", "no");
    return el("article", { className: "result-tile" }, [media, title, status,
      item.message && item.status !== "waiting_review" ? el("p", { className: "result-message", textContent: item.message }) : null, folder, actions]);
  }

  async function showResults(seriesId) {
    clearTimeout(state.poll);
    if (!seriesId) return;
    try {
      const view = await Api.batchResults(seriesId);
      if ($("results-series").value !== seriesId) return;  // another batch was chosen meanwhile
      state.results = view;
      const ready = view.items.filter((item) => ["waiting_review", "video_ready"].includes(item.status)).length;
      const missing = view.items.length - ready;
      $("results-summary").textContent = view.running ? `Making the videos: ${ready} of ${view.items.length} ready.`
        : `${ready} of ${view.items.length} ready.${view.main_folder ? "" : " No main save folder: the videos stay inside the app."}`;
      $("results-make").hidden = view.running || missing === 0;
      $("results-stop").hidden = !view.running;
      $("results-grid").replaceChildren(...view.items.map(tile));
      if (view.running) state.poll = setTimeout(() => showResults(seriesId), POLL_MS);
    } catch (error) {
      $("results-summary").textContent = error.message || "The results could not load.";
    }
  }
  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
  $("batch-template").addEventListener("change", () => setTemplate($("batch-template").value));
  ["batch-playlist", "batch-series"].forEach((id) => $(id).addEventListener("input", renderSaveWhere));
  document.addEventListener("main-folder:changed", (event) => { state.mainFolder = event.detail?.output_dir || null; renderSaveWhere(); });
  $("results-series").addEventListener("change", () => showResults($("results-series").value));
  $("results-make").addEventListener("click", async () => {
    try { await Api.makeBatch($("results-series").value); showResults($("results-series").value); }
    catch (error) { $("results-summary").textContent = error.message || "The videos could not be started."; }
  });
  $("results-stop").addEventListener("click", async () => {
    await Api.stopBatch($("results-series").value).catch(() => {});
    $("results-summary").textContent = "Stopping after the current step…";
  });
  $("batch-level").addEventListener("change", refreshPreview);
  $("batch-audience").addEventListener("change", refreshPreview);  // Phase 72 (ENH-054)
  $("batch-audience").addEventListener("change", () => window.TemplateSamples?.setAudience($("batch-audience").value || state.channelAudience));
  Api.getChannelAudience().then((data) => { state.channelAudience = data.audience; refreshPreview();
    window.TemplateSamples?.setAudience($("batch-audience").value || data.audience); }).catch(() => {});
  $("news-level").addEventListener("change", refreshPreview);
  $("batch-topic").addEventListener("input", () => { if (!state.items.length) refreshPreview(); });
  $("news-load").addEventListener("click", loadNews);
  $("news-picks").addEventListener("click", aiPicks);
  $("news-use").addEventListener("click", useStories);
  $("feed-add").addEventListener("click", () => {
    const url = $("feed-url").value.trim();
    if (!url) return;
    state.feeds.push({ url, name: $("feed-name").value.trim() || url, enabled: true });
    $("feed-url").value = ""; $("feed-name").value = "";
    renderFeeds();
  });
  $("feeds-save").addEventListener("click", async () => {
    try { state.feeds = (await Api.saveNewsFeeds(state.feeds)).feeds; renderFeeds(); notice("news-notice", "Feeds saved."); }
    catch (error) { notice("news-notice", error.message || "The feeds could not be saved.", true); }
  });

  fillSelect($("batch-template"), TEMPLATES, state.template);
  renderKinds();
  Api.getMainFolder().then((view) => { state.mainFolder = view.output_dir; renderSaveWhere(); }).catch(() => renderSaveWhere());
  loadBatches();
  fillSelect($("batch-level"), LEVELS.map((level) => [level, level]), "B1");
  fillSelect($("news-level"), LEVELS.map((level) => [level, level]), "B1");
  const tomorrow = new Date(Date.now() + 86400000);
  $("batch-start").value = tomorrow.toISOString().slice(0, 10);
  renderItems();
  refreshPreview();
  Api.listProfiles("state=active").then((profiles) => { state.profiles = profiles; renderCast(); }).catch(() => renderCast());
})();
