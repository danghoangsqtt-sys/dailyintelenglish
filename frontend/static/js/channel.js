/**
 * Task 36.5 (D103-D105): the channel plan page -- the AI channel map, the topic -> series -> episode tree and the
 * publishing calendar. All server calls go through Api.
 */
(() => {
  const CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const GENRES = ["small_talk", "interview", "storytelling", "debate", "opinion", "informational", "instructions",
    "directions", "negotiation", "news"];
  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const state = { channel: null, profiles: [], proposal: null, busy: false };
  const $ = (id) => document.getElementById(id);

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else if (key in node) node[key] = value;
      else node.setAttribute(key, value);
    });
    (Array.isArray(children) ? children : [children]).forEach((child) => {
      if (child !== null && child !== undefined) node.append(child);
    });
    return node;
  }

  function message(text, isError = false) {
    const box = $("channel-message");
    box.hidden = !text;
    box.textContent = text || "";
    box.classList.toggle("is-error", isError);
  }

  async function act(operation, success) {
    if (state.busy) return;
    state.busy = true;
    try {
      const result = await operation();
      if (result && result.topics) state.channel = result;
      else state.channel = await Api.getChannel();
      message(success || "");
    } catch (error) {
      message(error.message || "That did not work.", true);
    } finally {
      state.busy = false;
      render();
    }
  }

  const readyProfiles = () => state.profiles.filter((profile) => profile.readiness?.video_ready);

  function castSelect(value, onChange, label) {
    const select = el("select", { "aria-label": label, onchange: (event) => onChange(event.target.value) },
      [el("option", { value: "", textContent: "— choose —" }),
        ...readyProfiles().map((profile) => el("option", { value: profile.id, textContent: profile.name }))]);
    select.value = value || "";
    return select;
  }

  // ---------------------------------------------------------------- 1. the AI map

  function renderPlanForm() {
    const picks = $("plan-cefr");
    if (!picks.childElementCount) {
      CEFR.forEach((level) => picks.append(el("label", {}, [
        el("input", { type: "checkbox", name: "cefr", value: level, checked: ["A2", "B1"].includes(level) }), ` ${level}`])));
      const defaults = ["Alex", "Lina"];
      ["plan-cast0", "plan-cast1"].forEach((id, index) => {
        const select = $(id);
        select.replaceChildren(el("option", { value: "", textContent: "— none —" }),
          ...readyProfiles().map((profile) => el("option", { value: profile.id, textContent: profile.name })));
        select.value = readyProfiles().find((profile) => profile.name === defaults[index])?.id || "";
      });
    }
  }

  async function propose(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const levels = [...form.querySelectorAll("input[name=cefr]:checked")].map((input) => input.value);
    const body = {
      audience: form.elements.audience.value, focus: form.elements.focus.value, cefr_levels: levels.length ? levels : ["B1"],
      topics: Number(form.elements.topics.value), series_per_topic: Number(form.elements.series_per_topic.value),
      episodes_per_series: Number(form.elements.episodes_per_series.value),
    };
    $("plan-propose").disabled = true;
    $("plan-progress").textContent = "The AI is planning the channel… (about a minute)";
    try {
      state.proposal = await Api.proposeChannelPlan(body);
      message("");
    } catch (error) {
      message(error.message || "The AI could not plan the channel.", true);
    } finally {
      $("plan-propose").disabled = false;
      $("plan-progress").textContent = "";
      renderProposal();
    }
  }

  function renderProposal() {
    const box = $("plan-proposal");
    box.hidden = !state.proposal;
    const tree = $("proposal-tree");
    tree.replaceChildren();
    if (!state.proposal) return;
    state.proposal.topics.forEach((topic, topicIndex) => {
      const card = el("div", { className: "proposal-topic", dataset: { topic: topicIndex } }, [
        el("div", { className: "topic-head" }, [
          el("input", { className: "inline-input name", value: topic.name, "aria-label": "Topic name",
            oninput: (event) => { topic.name = event.target.value; } }),
          el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Remove topic",
            onclick: () => { state.proposal.topics.splice(topicIndex, 1); if (!state.proposal.topics.length) state.proposal = null; renderProposal(); } }),
        ]),
        el("div", { className: "channel-hint", textContent: topic.description }),
      ]);
      topic.series.forEach((series, seriesIndex) => {
        card.append(el("div", { className: "proposal-series" }, [
          el("div", { className: "series-head" }, [
            el("input", { className: "inline-input name", value: series.name, "aria-label": "Series name",
              oninput: (event) => { series.name = event.target.value; } }),
            el("span", { className: "status-chip", textContent: `${series.cefr_level} · ${series.genre.replace("_", " ")}` }),
            el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Remove series",
              onclick: () => {
                topic.series.splice(seriesIndex, 1);
                if (!topic.series.length) state.proposal.topics.splice(topicIndex, 1);
                if (!state.proposal.topics.length) state.proposal = null;
                renderProposal();
              } }),
          ]),
          el("ol", {}, series.episodes.map((episode) => el("li", {}, [
            el("input", { className: "inline-input", value: episode.title, "aria-label": "Episode title", title: episode.brief,
              oninput: (event) => { episode.title = event.target.value; } }),
          ]))),
        ]));
      });
      tree.append(card);
    });
  }

  async function applyProposal() {
    const cast = [$("plan-cast0").value, $("plan-cast1").value].filter(Boolean);
    const plan = state.proposal;
    await act(() => Api.applyChannelPlan(plan, cast), "The map was added to the channel.");
    if (!$("channel-message").classList.contains("is-error")) {
      state.proposal = null;
      renderProposal();
    }
  }

  // ---------------------------------------------------------------- 2. the tree

  function saveOnChange(input, save) {
    input.addEventListener("change", () => act(() => save(input.value.trim()), "Saved."));
    return input;
  }

  function episodeRow(episode) {
    const project = episode.project_id
      ? el("a", { href: `/step2?project_id=${encodeURIComponent(episode.project_id)}`, textContent: "Open project" })
      : el("span", { className: "channel-hint", textContent: "—" });
    const url = saveOnChange(el("input", { className: "inline-input url", value: episode.video_url || "",
      placeholder: "YouTube link after publishing", "aria-label": `Video link of episode ${episode.number}` }),
    (value) => Api.updateChannelEpisode(episode.id, { video_url: value }));
    const actions = el("td", {}, []);
    if (episode.status === "created") {
      actions.append(el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Mark published",
        dataset: { action: "publish" },
        onclick: () => act(() => Api.updateChannelEpisode(episode.id, { status: "published", video_url: url.value.trim() }),
          `Episode ${episode.number} marked published.`) }));
    }
    actions.append(el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "✕", title: "Delete episode",
      onclick: () => confirm(`Delete episode ${episode.number}?`) && act(() => Api.deleteChannelEpisode(episode.id), "Episode deleted.") }));
    return el("tr", { dataset: { episode: episode.id } }, [
      el("td", { textContent: `Ep. ${episode.number}` }),
      el("td", {}, saveOnChange(el("input", { className: "inline-input name", value: episode.title, title: episode.brief,
        "aria-label": `Title of episode ${episode.number}` }), (value) => Api.updateChannelEpisode(episode.id, { title: value }))),
      el("td", {}, el("span", { className: "status-chip", dataset: { status: episode.status }, textContent: episode.status })),
      el("td", { textContent: episode.publish_date || "—" }),
      el("td", {}, project),
      el("td", {}, url),
      actions,
    ]);
  }

  function seriesCard(series) {
    const cast = series.cast || [];
    const setCast = (index, value) => {
      const next = [...cast];
      next[index] = value;
      act(() => Api.updateChannelSeries(series.id, { cast: next.filter(Boolean) }), "Cast saved.");
    };
    const genre = el("select", { "aria-label": "Genre",
      onchange: (event) => act(() => Api.updateChannelSeries(series.id, { genre: event.target.value }), "Saved.") },
    GENRES.map((value) => el("option", { value, textContent: value.replace("_", " ") })));
    genre.value = series.genre;
    const level = el("select", { "aria-label": "Level",
      onchange: (event) => act(() => Api.updateChannelSeries(series.id, { cefr_level: event.target.value }), "Saved.") },
    CEFR.map((value) => el("option", { value, textContent: value })));
    level.value = series.cefr_level;
    const planned = series.episodes.filter((episode) => !episode.project_id).length;
    const newEpisode = el("input", { className: "inline-input", placeholder: "New episode title", "aria-label": "New episode title" });
    return el("div", { className: "series-card", dataset: { series: series.id } }, [
      el("div", { className: "series-head" }, [
        saveOnChange(el("input", { className: "inline-input name", value: series.name, "aria-label": "Series name" }),
          (value) => Api.updateChannelSeries(series.id, { name: value })),
        el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Delete series",
          onclick: () => confirm(`Delete the series "${series.name}"? Its projects are kept.`)
            && act(() => Api.deleteChannelSeries(series.id), "Series deleted.") }),
      ]),
      el("div", { className: "channel-hint", textContent: series.description }),
      el("div", { className: "series-meta" }, [
        level, genre, "Cast:",
        castSelect(cast[0], (value) => setCast(0, value), "Speaker 1"),
        castSelect(cast[1], (value) => setCast(1, value), "Speaker 2"),
        saveOnChange(el("input", { className: "inline-input url", value: series.playlist_url || "",
          placeholder: "Series playlist link (optional)", "aria-label": "Series playlist link" }),
        (value) => Api.updateChannelSeries(series.id, { playlist_url: value })),
      ]),
      el("table", { className: "episode-table" }, [
        el("thead", {}, el("tr", {}, ["#", "Title", "Status", "Date", "Project", "Video", ""].map((text) => el("th", { textContent: text })))),
        el("tbody", {}, series.episodes.map(episodeRow)),
      ]),
      el("div", { className: "row-actions" }, [
        el("button", { type: "button", className: "btn btn-primary btn-sm", dataset: { action: "create-projects" },
          textContent: planned ? `Create ${planned} project${planned === 1 ? "" : "s"}` : "All projects created",
          disabled: !planned || cast.filter(Boolean).length < 2,
          title: cast.filter(Boolean).length < 2 ? "Choose two characters first." : "",
          onclick: () => act(() => Api.createSeriesProjects(series.id), "Projects created — open them from the table.") }),
        newEpisode,
        el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "+ Episode",
          onclick: () => newEpisode.value.trim()
            && act(() => Api.addChannelEpisode(series.id, { title: newEpisode.value.trim() }), "Episode added.") }),
      ]),
    ]);
  }

  function topicCard(topic) {
    const newSeries = el("input", { className: "inline-input", placeholder: "New series name", "aria-label": "New series name" });
    return el("div", { className: "topic-card", dataset: { topic: topic.id } }, [
      el("div", { className: "topic-head" }, [
        saveOnChange(el("input", { className: "inline-input name", value: topic.name, "aria-label": "Topic name" }),
          (value) => Api.updateChannelTopic(topic.id, { name: value })),
        saveOnChange(el("input", { className: "inline-input url", value: topic.playlist_url || "",
          placeholder: "YouTube playlist link", "aria-label": "Topic playlist link" }),
        (value) => Api.updateChannelTopic(topic.id, { playlist_url: value })),
        el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "Delete topic",
          onclick: () => confirm(`Delete the topic "${topic.name}" and its series? Projects are kept.`)
            && act(() => Api.deleteChannelTopic(topic.id), "Topic deleted.") }),
      ]),
      el("div", { className: "channel-hint", textContent: topic.description }),
      ...topic.series.map(seriesCard),
      el("div", { className: "row-actions" }, [
        newSeries,
        el("button", { type: "button", className: "btn btn-ghost btn-sm", textContent: "+ Series",
          onclick: () => newSeries.value.trim()
            && act(() => Api.createChannelSeries(topic.id, { name: newSeries.value.trim() }), "Series added.") }),
      ]),
    ]);
  }

  // ---------------------------------------------------------------- 3. the calendar

  function renderCalendar() {
    const picks = $("calendar-weekdays");
    if (!picks.childElementCount) {
      WEEKDAYS.forEach((day, index) => picks.append(el("label", {}, [
        el("input", { type: "checkbox", name: "weekday", value: index, checked: [0, 2, 4].includes(index) }), ` ${day}`])));
      $("calendar-form").elements.start_date.value = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    }
    const rows = [];
    (state.channel?.topics || []).forEach((topic) => topic.series.forEach((series) => series.episodes.forEach((episode) => {
      if (episode.publish_date) rows.push({ topic, series, episode });
    })));
    rows.sort((a, b) => a.episode.publish_date.localeCompare(b.episode.publish_date));
    $("calendar-list").replaceChildren(...rows.map(({ topic, series, episode }) => el("li", {}, [
      el("strong", { textContent: `${WEEKDAYS[(new Date(`${episode.publish_date}T00:00:00`).getDay() + 6) % 7]} ${episode.publish_date}` }),
      el("span", { textContent: topic.name }),
      el("span", { textContent: `${series.name} · Ep. ${episode.number}: ${episode.title}` }),
      el("span", { className: "status-chip", dataset: { status: episode.status }, textContent: episode.status }),
    ])));
  }

  async function plan(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const weekdays = [...form.querySelectorAll("input[name=weekday]:checked")].map((input) => Number(input.value));
    if (!weekdays.length) return message("Choose at least one publishing day.", true);
    await act(() => Api.scheduleChannel({ start_date: form.elements.start_date.value, weekdays }), "Publishing dates planned.");
  }

  // ---------------------------------------------------------------- page

  function render() {
    const counts = state.channel?.counts || { planned: 0, created: 0, published: 0 };
    $("channel-counts").replaceChildren(
      el("span", { className: "status-chip", textContent: `${state.channel?.topics.length || 0} topics` }),
      el("span", { className: "status-chip", textContent: `${counts.planned} planned` }),
      el("span", { className: "status-chip", dataset: { status: "created" }, textContent: `${counts.created} in production` }),
      el("span", { className: "status-chip", dataset: { status: "published" }, textContent: `${counts.published} published` }));
    const tree = $("channel-tree");
    const topics = state.channel?.topics || [];
    tree.replaceChildren(...(topics.length ? topics.map(topicCard)
      : [el("p", { className: "channel-hint", textContent: "No topics yet: plan with AI above or add one below." })]));
    renderPlanForm();
    renderCalendar();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    $("theme-toggle").addEventListener("click", Theme.toggle);
    $("plan-form").addEventListener("submit", propose);
    $("plan-apply").addEventListener("click", applyProposal);
    $("plan-discard").addEventListener("click", () => { state.proposal = null; renderProposal(); });
    $("calendar-form").addEventListener("submit", plan);
    $("new-topic").addEventListener("click", () => {
      const name = $("new-topic-name").value.trim();
      if (name) act(() => Api.createChannelTopic({ name }), "Topic added.").then(() => { $("new-topic-name").value = ""; });
    });
    try {
      [state.channel, state.profiles] = await Promise.all([Api.getChannel(), Api.listProfiles("state=active")]);
    } catch (error) {
      message(error.message || "The channel plan could not load.", true);
    }
    render();
  });
})();
