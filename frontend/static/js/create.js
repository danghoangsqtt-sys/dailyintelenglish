/**
 * Phase 93 (Task 93.4): Create video -- the kinds of video grouped by purpose, each with its Phase 92 example clip
 * (`/static/samples/index.json`); a card opens Step 1 with that kind chosen.
 */
(() => {
  const GROUPS = [
    ["academic", "Academic", "taught in Vietnamese · 1–3 minutes", "9:16", [["grammar", "Easy grammar", "One grammar point explained by its essence", "New"], ["roots", "Word roots, prefixes & suffixes", "One root and its word family", "New"],
      ["slowpod", "Slow English podcast", "One sentence per screen with its translation"], ["flashcards", "Vocabulary flashcards", "8–10 words on one topic"]]],
    ["characters", "Characters and presenter", "characters from the library", "9:16", [["conversation_short", "Conversation", "Two characters talk"], ["presenter_short", "Presenter", "One idea explained to camera"],
      ["vox_short", "VOX", "A narrated story over pictures"], ["chat", "Chat", "Two characters text each other"]]],
    ["quick", "Quick text templates", "under a minute", "9:16", [["readalong", "Read Along", "A full English passage with word highlighting"], ["loadword", "Load the word", "One word, faster and faster"], ["picstory", "Picture story", "A picture for each sentence"], ["levelup", "Basic vs Advanced", "A plain phrase, then the natural one"], ["wordday", "Word of the day", "One word said six times over its picture"], ["mistakes", "Don't say / Say", "A common mistake and the natural way"],
      ["news", "English news", "One story in simple English"], ["top5", "Top 5 phrases", "Five ways to say one thing"], ["blur", "Text on blur", "Big words over a blurred picture"], ["listen", "Listening challenge", "Hear it, then see it"]]],
    ["interactive", "Interactive", "viewers answer in the comments", "9:16", [["whatis", "What is this called?", "An object, a 1-2-3, its name"], ["quiz", "Countdown quiz", "Viewers comment the answer"], ["wyr", "Would you rather", "Two choices, viewers vote"]]],
    ["long", "16:9 videos", "for the main channel", "16:9", [["conversation", "Conversation", "Characters talk, scene by scene"], ["presenter", "Presenter", "A presenter explains one topic"], ["vox", "VOX", "A narrated explainer with pictures"], ["doodle", "Doodle story", "A whole story over hand-drawn pictures"]]],
  ];
  // how Step 1 picks each kind
  const STEP1 = { conversation: "mode=classic", presenter: "mode=solo_explainer", vox: "mode=vox", doodle: "mode=doodle", conversation_short: "mode=classic", presenter_short: "mode=solo_explainer", vox_short: "mode=vox" };
  const topic = new URLSearchParams(location.search).get("topic") || "";  // from Home's "next video" box
  const href = (kind) => `/step1?${STEP1[kind] || `mode=shorts&template=${kind}`}${topic ? `&topic=${encodeURIComponent(topic)}` : ""}`;
  let samples = {};
  let group = "all";
  let aspect = "9:16";

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => (key === "dataset" ? Object.assign(node.dataset, value) : key.startsWith("aria-") ? node.setAttribute(key, value) : (node[key] = value)));
    (Array.isArray(children) ? children : [children]).forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }

  function card([kind, name, line, tag]) {
    const sample = samples[kind];
    const lang = document.documentElement.lang === "en" ? "en" : "vi";
    const poster = sample ? `/static/samples/${sample[`poster_${lang}`] || sample.poster_vi}` : "";
    const clip = sample ? `/static/samples/${sample[lang] || sample.vi}` : "";
    const media = el("div", { className: `e-thumb${sample && sample.aspect === "16:9" ? " e-wide" : ""}` }, [
      poster ? el("img", { src: poster, alt: "", loading: "lazy" }) : null, tag ? el("span", { className: "create-tag", textContent: tag }) : null]);
    const link = el("a", { className: "e-tpl", href: href(kind), dataset: { kind } }, [media, el("b", { textContent: name }), el("span", { textContent: line })]);
    if (clip && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      let video = null;
      const play = () => {
        if (!video) { video = el("video", { src: clip, muted: true, loop: true, playsInline: true, poster }); video.setAttribute("aria-hidden", "true"); media.append(video); }
        video.play().catch(() => {});
      };
      const stop = () => { if (video) video.pause(); };
      link.addEventListener("mouseenter", play); link.addEventListener("focus", play);
      link.addEventListener("mouseleave", stop); link.addEventListener("blur", stop);
    }
    return link;
  }

  function render() {
    document.getElementById("create-groups").replaceChildren(...[["all", "All"], ...GROUPS.filter((g) => g[3] === aspect).map((g) => [g[0], g[1]])].map(([key, label]) =>
      el("button", { type: "button", className: "e-chip", textContent: label, "aria-pressed": String(key === group), onclick: () => { group = key; render(); } })));
    const shown = GROUPS.filter((g) => g[3] === aspect && (group === "all" || g[0] === group));
    document.getElementById("create-gallery").replaceChildren(...shown.map(([key, title, sub, , kinds]) => el("section", { className: "create-group", dataset: { group: key } }, [
      el("div", { className: "e-sh" }, [el("h2", { textContent: title }), el("span", { className: "e-muted", textContent: sub })]),
      el("div", { className: "e-gallery" }, kinds.map(card)),
    ])));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const toggle = document.getElementById("theme-toggle");
    if (toggle) toggle.addEventListener("click", Theme.toggle);
    document.querySelectorAll("[data-aspect]").forEach((button) => button.addEventListener("click", () => {
      aspect = button.dataset.aspect; group = "all";
      document.querySelectorAll("[data-aspect]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      render();
    }));
    try { samples = await (await fetch("/static/samples/index.json")).json(); } catch { samples = {}; }
    render();
  });
})();
