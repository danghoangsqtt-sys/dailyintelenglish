/** Phase 66 (ENH-048): the Shorts batch page -- AI ideas from one topic, or today's news with the AI's picks; the
 *  reviewed list is saved as a dated Channel plan series (the night Automation makes it), optionally with projects now. */
(function () {
  const $ = (id) => document.getElementById(id);
  const TEMPLATES = [["news", "English news"], ["blur", "Text on blur"], ["mistakes", "Don't say / Say"], ["wordday", "Word of the day"],
    ["top5", "Top 5 phrases"], ["quiz", "Countdown quiz"], ["listen", "Listening challenge"], ["chat", "Chat (2 characters)"],
    ["wyr", "Would you rather (2 characters)"]];
  const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const state = { tab: "topic", template: "mistakes", items: [], stories: [], feeds: [], profiles: [], selected: 0, player: null, timer: null };

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
      if (!window.SoloPreview || !window.ShortsSample) { $("preview-error").textContent = "The preview player is not available."; return; }
      const idea = previewIdea();
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
    node.append(...children);
    return node;
  };
  const notice = (id, text, error = false) => { $(id).textContent = text; $(id).classList.toggle("is-error", error); };
  const twoCharacters = () => ["chat", "wyr"].includes(state.template);

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
    $("cast-one-label").firstChild.textContent = twoCharacters() ? "First character" : "Narrator";
    $("cast-two-label").hidden = !twoCharacters();
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
    if (tab === "news") { state.template = "news"; renderCast(); if (!state.feeds.length) loadFeeds(); }
    else { state.template = $("batch-template").value; renderCast(); }
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
      const { ideas } = await Api.proposeBatchIdeas({ topic: $("batch-topic").value.trim(), template: $("batch-template").value,
        count: Number($("batch-count").value), cefr_level: $("batch-level").value, hint: $("batch-hint").value.trim() });
      state.items = ideas.map((idea) => ({ ...idea, source_text: "" }));
      state.selected = 0;
      renderItems();
      refreshPreview();
      if (!$("batch-series").value) $("batch-series").value = $("batch-topic").value.trim().slice(0, 100);
      notice("batch-notice", `${ideas.length} ideas. Edit or remove them, then create the batch.`);
    } catch (error) { notice("batch-notice", error.message || "The AI could not propose ideas.", true); }
  });

  $("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const items = state.items.filter((item) => item.title.trim());
    if (!items.length) { notice("batch-notice", "Propose or choose the Shorts first.", true); return; }
    const cast = [$("batch-cast-0").value, ...(twoCharacters() ? [$("batch-cast-1").value] : [])].filter(Boolean);
    try {
      const result = await Api.createBatch({ topic_name: $("batch-playlist").value.trim(), series_name: $("batch-series").value.trim(),
        template: state.template, cast, cefr_level: state.tab === "news" ? $("news-level").value : $("batch-level").value,
        start_date: $("batch-start").value, every_days: Number($("batch-every").value) || 1, make_projects: $("batch-make").checked,
        ...($("batch-audience").value ? { audience: $("batch-audience").value } : {}),
        items: items.map(({ title, brief, source_text }) => ({ title: title.trim(), brief: (brief || "").trim(), source_text: source_text || "" })) });
      notice("batch-notice", `Created: ${result.episodes} Shorts dated ${result.first_date} → ${result.last_date}`
        + (result.projects ? `, ${result.projects} projects made.` : ". Automation makes them before their dates."));
    } catch (error) { notice("batch-notice", error.message || "The batch could not be created.", true); }
  });

  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
  $("batch-template").addEventListener("change", () => { state.template = $("batch-template").value; renderCast(); refreshPreview(); });
  $("batch-level").addEventListener("change", refreshPreview);
  $("batch-audience").addEventListener("change", refreshPreview);  // Phase 72 (ENH-054)
  Api.getChannelAudience().then((data) => { state.channelAudience = data.audience; refreshPreview(); }).catch(() => {});
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
  fillSelect($("batch-level"), LEVELS.map((level) => [level, level]), "B1");
  fillSelect($("news-level"), LEVELS.map((level) => [level, level]), "B1");
  const tomorrow = new Date(Date.now() + 86400000);
  $("batch-start").value = tomorrow.toISOString().slice(0, 10);
  renderItems();
  refreshPreview();
  Api.listProfiles("state=active").then((profiles) => { state.profiles = profiles; renderCast(); }).catch(() => renderCast());
})();
