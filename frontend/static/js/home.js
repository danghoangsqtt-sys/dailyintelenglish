/**
 * Phase 93 (Task 93.3, D141): Home -- Lina's summary, the videos waiting for the owner, the work in progress and this
 * week's publishing days. Reads the review board (Automation) and the channel overview; owns no data of its own.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const WAITING = { waiting_review: ["wait", "Waiting for review"], needs_attention: ["err", "Needs a fix"], changes: ["wait", "Changes asked"] };
  const MOVING = { making: ["run", "Making now"], in_progress: ["", "In progress"] };
  const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("aria-") || key === "role") node.setAttribute(key, value);
      else node[key] = value;
    });
    (Array.isArray(children) ? children : [children]).forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }
  const iso = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const minutes = (seconds) => (seconds ? `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}` : "");
  const name = (card) => (card.series ? `${card.series} · ${card.title}` : card.title);
  const thumb = (url, wide) => el("div", { className: `e-thumb${wide ? " e-wide" : ""}` }, url ? el("img", { src: url, alt: "", loading: "lazy" }) : null);

  function row(card, [tone, label], actions, note) {
    const meta = [card.kind, card.vertical ? "Short" : "16:9", minutes(card.duration), note].filter(Boolean).join(" · ");
    return el("div", { className: "e-row" }, [
      thumb(card.thumbnail_url, !card.vertical),
      el("div", {}, [el("div", { className: "e-t", textContent: name(card) }), el("div", { className: "e-m", textContent: meta })]),
      el("span", { className: `e-state ${tone}`, textContent: label }),
      el("div", { className: "e-acts" }, actions),
    ]);
  }
  const action = (label, href, primary) => el("a", { className: `btn btn-sm${primary ? " btn-primary" : ""}`, href, textContent: label });

  function renderWaiting(cards, extraActions) {
    const list = $("waiting-list");
    $("waiting-count").hidden = !cards.length;
    $("waiting-count").textContent = String(cards.length);
    window.dispatchEvent(new CustomEvent("dbe:waiting", { detail: cards.length }));
    if (!cards.length && !extraActions.length) {
      list.replaceChildren(el("p", { className: "e-empty", textContent: "Nothing waits for you. Every finished video has been reviewed." }));
      return;
    }
    list.replaceChildren(
      ...cards.slice(0, 6).map((card) => row(card, WAITING[card.state], [
        card.project_id ? action("Open", `/step5?project_id=${encodeURIComponent(card.project_id)}`) : null,
        action(card.state === "needs_attention" ? "See the problem" : "Review", "/channel#auto", true),
      ], card.message)),
      ...extraActions.map((item) => el("div", { className: "e-row home-action" }, [
        el("span", { className: "e-thumb", "aria-hidden": "true" }),
        el("div", {}, el("div", { className: "e-t", textContent: item.label })), el("span"),
        el("div", { className: "e-acts" }, action("Open", item.link, true)),
      ])),
      cards.length > 6 ? el("p", { className: "e-empty" }, el("a", { href: "/channel#auto", textContent: `See all ${cards.length} in the review list` })) : null,
    );
  }

  function renderMoving(cards, going, next) {
    const rows = cards.slice(0, 5).map((card) => row(card, MOVING[card.state], [], card.step ? `Step: ${card.step}` : ""));
    if (next) {  // the channel plan's next episode without a project (the former "Start here" card)
      rows.push(el("div", { className: "e-row home-next" }, [
        el("span", { className: "e-thumb", "aria-hidden": "true" }),
        el("div", {}, [el("div", { className: "e-t", textContent: `${next.series} · Ep. ${next.number}: ${next.title}` }),
          el("div", { className: "e-m", textContent: [next.publish_date, next.topic].filter(Boolean).join(" · ") })]),
        el("span", { className: "e-state", textContent: "Next planned" }),
        el("div", { className: "e-acts" }, action("Create its project", next.link, true)),
      ]));
    }
    if (going) {
      rows.unshift(el("div", { className: "e-row" }, [
        el("span", { className: "e-thumb", "aria-hidden": "true" }),
        el("div", {}, [el("div", { className: "e-t", textContent: going.name }),
          el("div", { className: "e-m", textContent: `Next: Step ${going.step_number} — ${going.step_label}` }),
          el("div", { className: "e-steps", "aria-label": `Step ${going.step_number} of 7` },
            [1, 2, 3, 4, 5, 6, 7].map((n) => el("i", { className: n < going.step_number ? "d" : n === going.step_number ? "n" : "" })))]),
        el("span"), el("div", { className: "e-acts" }, action("Continue", going.link, true)),
      ]));
    }
    $("moving-list").replaceChildren(...(rows.length ? rows : [el("p", { className: "e-empty", textContent: "Nothing is being made right now." })]));
  }

  function renderWeek(calendar, today) {
    const start = new Date(`${today || iso(new Date())}T00:00:00`);
    const days = Array.from({ length: 7 }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
    $("week-list").replaceChildren(...days.map((date, index) => {
      const items = calendar.filter((item) => item.publish_date === iso(date));
      return el("div", { className: `home-day${index === 0 ? " today" : ""}` }, [
        el("div", { className: "home-day-d" }, [index === 0 ? "Today" : WEEKDAYS[date.getDay()], el("b", { className: "e-num", textContent: String(date.getDate()) })]),
        el("div", {}, items.length ? [...items.slice(0, 3).map((item) => el("a", {
          className: "home-ev", href: item.project_id ? `/step2?project_id=${encodeURIComponent(item.project_id)}` : "/channel", dataset: { status: item.status },
        }, [el("span", { className: "home-ev-t", textContent: `${item.series} · ${item.title}` }), el("small", { textContent: item.status })])),
          items.length > 3 ? el("a", { className: "home-ev-more", href: "/channel", textContent: `+${items.length - 3} more` }) : null]
          : el("span", { className: "e-muted home-ev-none", textContent: "Nothing planned." })),
      ]);
    }));
  }

  function renderBand(waiting, going) {
    const line = $("home-line"), acts = $("home-acts");
    if (waiting.length) {
      line.replaceChildren(waiting.length === 1 ? "There is " : "There are ", el("b", { textContent: `${waiting.length} video${waiting.length === 1 ? "" : "s"}` }),
        " waiting for you. Once you approve them they are scheduled.");
      acts.replaceChildren(el("a", { className: "btn btn-primary e-sun", href: "/channel#auto", textContent: `Review ${waiting.length} video${waiting.length === 1 ? "" : "s"}` }),
        going ? el("a", { className: "btn btn-ghost", href: going.link, textContent: "Continue my video" }) : null);
    } else if (going) {
      line.replaceChildren("Nothing waits for review. Continue with ", el("b", { textContent: going.name }));
      acts.replaceChildren(el("a", { className: "btn btn-primary e-sun", href: going.link, textContent: `Continue at Step ${going.step_number}` }));
    } else {
      line.textContent = "Nothing waits for you. What should the next video be about?";
      acts.replaceChildren();
    }
  }

  function animateLina() {
    const lina = $("home-lina");
    if (!lina || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const frame = (n) => `/api/assistant/frames/${n}.webp`;
    ["calm__closed", "blink"].forEach((n) => { new Image().src = frame(n); });
    lina.addEventListener("error", () => lina.closest(".e-lina").setAttribute("hidden", ""), { once: true });
    setTimeout(() => { lina.src = frame("calm__closed"); lina.alt = "Lina"; }, 2200);
    (function blink() {
      setTimeout(() => {
        if (lina.src.includes("calm__closed")) { lina.src = frame("blink"); setTimeout(() => { lina.src = frame("calm__closed"); }, 120); }
        blink();
      }, 2600 + Math.random() * 3200);
    })();
  }

  async function load() {
    $("home-date").textContent = new Date().toLocaleDateString(document.documentElement.lang === "vi" ? "vi-VN" : "en-GB", { weekday: "long", day: "numeric", month: "long" });
    const [board, channel] = await Promise.all([Api.getAutomationBoard().catch(() => null), Api.getChannelDashboard().catch(() => null)]);
    const videos = (board && board.videos) || [];
    const waiting = videos.filter((card) => WAITING[card.state]);
    const moving = videos.filter((card) => MOVING[card.state]);
    const going = channel && channel.start ? channel.start.continue : null;
    renderBand(waiting, going);
    renderWaiting(waiting, ((channel && channel.actions) || []).slice(0, waiting.length ? 3 : 5));
    renderMoving(moving, going, channel && channel.start ? channel.start.next_episode : null);
    renderWeek((channel && channel.calendar) || [], channel && channel.today);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = $("theme-toggle");
    if (toggle) toggle.addEventListener("click", Theme.toggle);
    animateLina();
    load().catch((error) => {
      $("waiting-list").replaceChildren(el("p", { className: "e-empty", textContent: error.message || "Home could not load." }));
    });
  });
})();
