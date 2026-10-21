/**
 * Task 36.7 (D106-D108): the channel cockpit on the dashboard -- stats, the next episode to publish, today's actions, the
 * channel roadmap, the production board by step and the next two weeks. The project grid (dashboard.js) stays below.
 * Phase 56 (ENH-038): "Start here" on top -- continue the latest project, the next planned episode, or a new video.
 */
(() => {
  const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const $ = (id) => document.getElementById(id);
  let selectedStage = null;

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node[key] = value;
    });
    (Array.isArray(children) ? children : [children]).forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }

  const day = (iso) => `${WEEKDAYS[new Date(`${iso}T00:00:00`).getDay()]} ${iso}`;
  const episodeName = (item) => (item.series ? `${item.series} · Ep. ${item.number}: ${item.title}` : item.name);

  function renderStats(stats) {
    const entries = [
      [stats.topics, "topics"], [stats.series, "series"], [stats.episodes.planned, "planned"],
      [stats.episodes.created, "in production"], [stats.produced, "ready"], [stats.episodes.published, "published"],
    ];
    $("cockpit-stats").replaceChildren(...entries.map(([value, label]) =>
      el("div", { className: "cockpit-stat" }, [el("b", { textContent: value }), el("span", { textContent: label })])));
  }

  function renderNext(next) {
    $("cockpit-next").replaceChildren(...(next
      ? [el("strong", { textContent: `${next.series} · Ep. ${next.number}: ${next.title}` }),
        el("p", { textContent: `${day(next.publish_date)} · ${next.topic}` }),
        el("a", { className: "btn btn-ghost btn-sm", href: next.project_id ? `/step2?project_id=${next.project_id}` : "/channel",
          textContent: next.project_id ? "Open the episode" : "Create its project" })]
      : [el("p", { className: "cockpit-empty", textContent: "Nothing dated yet." }),
        el("a", { className: "btn btn-ghost btn-sm", href: "/channel", textContent: "Plan the publishing dates" })]));
  }

  function startCard(kind, title, lines, link, label) {
    return el("article", { className: "start-card", dataset: { kind } }, [
      el("h3", { textContent: title }),
      ...lines.filter(Boolean).map((line, index) => el(index ? "p" : "strong", { textContent: line })),
      el("a", { className: `btn ${kind === "new" ? "btn-ghost" : "btn-primary"} btn-sm`, href: link, textContent: label }),
    ]);
  }

  function renderStart(start) {
    const going = start.continue;
    const next = start.next_episode;
    $("start-cards").replaceChildren(
      going
        ? startCard("continue", "▶ Continue", [going.name, `Next: Step ${going.step_number} — ${going.step_label}`],
          going.link, "Continue →")
        : startCard("continue", "▶ Continue", ["Nothing in progress", "Every project is finished up to its YouTube package."],
          "#project-grid", "See all projects"),
      next
        ? startCard("episode", "★ Next planned episode", [`${next.series} · Ep. ${next.number}: ${next.title}`,
          next.publish_date ? `${day(next.publish_date)} · ${next.topic}` : next.topic], next.link, "Create its project →")
        : start.has_plan
          ? startCard("episode", "★ Next planned episode", ["Every planned episode has a project",
            "Add more series or episodes to the channel plan."], "/channel", "Open the channel plan")
          : startCard("episode", "★ Next planned episode", ["No channel plan yet",
            "Plan topics and series with AI, then make their episodes one by one."], "/channel", "Plan the channel →"),
      startCard("new", "＋ New video", ["Your own topic", "Choose the topic, level and characters in Step 1."], "/step1", "Start a new video"));
  }

  function renderActions(actions) {
    $("cockpit-actions").replaceChildren(...(actions.length
      ? actions.map((action) => el("li", { dataset: { kind: action.kind } }, el("a", { href: action.link, textContent: action.label })))
      : [el("li", { className: "cockpit-empty", textContent: "Nothing urgent. Keep producing ahead of the calendar." })]));
  }

  function renderRoadmap(roadmap) {
    const shown = selectedStage ?? roadmap.current;
    $("roadmap-steps").replaceChildren(...roadmap.stages.map((stage, index) => {
      const state = stage.done ? "done" : index === roadmap.current ? "current" : "todo";
      return el("li", {}, el("button", {
        type: "button", dataset: { state, stage: stage.key }, "aria-pressed": String(index === shown),
        onclick: () => { selectedStage = index; renderRoadmap(roadmap); },
      }, [el("span", { className: "stage-name", textContent: `${index + 1}. ${stage.title}` }),
        el("span", { className: "stage-meta", textContent: stage.done ? "✓ done" : `${stage.progress} · ${state === "current" ? "you are here" : "later"}` })]));
    }));
    $("roadmap-steps").querySelectorAll("button").forEach((button, index) => button.setAttribute("aria-pressed", String(index === shown)));
    const stage = roadmap.stages[shown];
    const detail = [el("ul", {}, stage.checks.map((check) => el("li", { dataset: { done: String(check.done) } }, [
      el("span", { textContent: check.done ? "✅" : "⬜" }),
      el("a", { href: check.link, textContent: check.label }),
      check.progress ? el("span", { className: "stage-meta", textContent: check.progress }) : null,
    ])))];
    if (shown === roadmap.current && roadmap.next) {
      detail.push(el("div", { className: "roadmap-next" },
        el("a", { className: "btn btn-primary btn-sm", href: roadmap.next.link, textContent: `Next: ${roadmap.next.label} →` })));
    }
    $("roadmap-detail").replaceChildren(...detail);
  }

  function renderBoard(columns) {
    $("production-board").replaceChildren(...columns.map((column) => el("div", { className: "board-column", dataset: { step: column.key } }, [
      el("h3", { textContent: `${column.label} (${column.items.length})` }),
      ...column.items.slice(0, 12).map((item) => el("a", {
        className: "board-card", href: item.link, dataset: { published: String(Boolean(item.published)) },
      }, [el("span", { textContent: episodeName(item) }),
        el("small", { textContent: item.published ? "published" : item.publish_date ? day(item.publish_date) : item.topic || "no date" })])),
      column.items.length > 12 ? el("small", { textContent: `+${column.items.length - 12} more` }) : null,
    ])));
  }

  function renderCalendar(calendar) {
    $("cockpit-calendar").replaceChildren(...(calendar.length
      ? calendar.map((item) => el("li", {}, [
        el("strong", { textContent: day(item.publish_date) }),
        el("span", { textContent: `${item.topic} — ${item.series} · Ep. ${item.number}: ${item.title}` }),
        el("span", { className: "status-chip", textContent: item.status }),
      ]))
      : [el("li", { className: "cockpit-empty", textContent: "No episode dated in the next two weeks." })]));
  }

  async function load() {
    try {
      const data = await Api.getChannelDashboard();
      if (data.start) renderStart(data.start);
      renderStats(data.stats);
      renderNext(data.next_publish);
      renderActions(data.actions);
      renderRoadmap(data.roadmap);
      renderBoard(data.board);
      renderCalendar(data.calendar);
    } catch (error) {
      $("cockpit-actions").replaceChildren(el("li", { className: "cockpit-empty", textContent: error.message || "The channel overview could not load." }));
      $("start-cards").replaceChildren(startCard("new", "＋ New video", ["Your own topic"], "/step1", "Start a new video"));
    }
  }

  document.addEventListener("DOMContentLoaded", load);
})();
