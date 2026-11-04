/* global Api */
/**
 * Phase 92 (D134–D137): a short muted example clip on every kind card (Step 1 and the Shorts batch page), so a new user
 * sees what each kind of video looks like. The clip plays while the card is hovered, focused or chosen, and never when
 * the viewer prefers reduced motion (the poster stays); clicking the clip opens a larger one in a dialog with
 * "Example only" and what the kind is best for. Clips: frontend/static/samples (npm run render:samples).
 */
const TemplateSamples = (() => {
  // what each kind is best for (one line, Vietnamese in i18n_vi.js)
  const BEST_FOR = {
    conversation: "Two characters talk through an everyday situation; 16:9 lessons of 5–15 minutes.",
    presenter: "One presenter explains one idea to camera; 16:9 or a Short.",
    vox: "A narrator's voice over pictures and on-screen text; explains why or how.",
    news: "One news story in simple English; a Short under a minute.",
    blur: "One short story or idea in big text on a blurred background.",
    mistakes: "A common mistake and the natural way to say it.",
    loadword: "One word said faster and faster until it stays in memory.",
    picstory: "One short sentence on each screen, over a picture of that action.",
    levelup: "A plain phrase, then the natural one twice, over its picture.",
    whatis: "Viewers name everyday objects: the object, a 1-2-3, the name.",
    wordday: "One word said six times over its picture, then an example.",
    top5: "Five phrases on one topic, counted down.",
    quiz: "Two or three A/B/C questions with a countdown; viewers comment.",
    listen: "One sentence at natural speed, then the words: a listening test.",
    slowpod: "A calm, slow monologue with the Vietnamese under each line.",
    flashcards: "Eight to ten words of one topic: part of speech, IPA, meaning.",
    roots: "One root, prefix or suffix and its word family, in Vietnamese; 1–3 minutes.",
    grammar: "One grammar point explained by its essence, in Vietnamese; 1–3 minutes.",
    chat: "A text-message chat between two people; read along.",
    wyr: "Would you rather: two choices, a timer and the answer.",
  };
  const MODES = { classic: "conversation", solo_explainer: "presenter", vox: "vox" };
  const reduced = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  let index = null, language = "vi", dialog = null, vertical = false;
  // owner 2026-11-03: on the Shorts batch page the conversation, presenter and VOX kinds are vertical Shorts, so their
  // vertical clips are shown there (Step 1 shows the 16:9 long videos)
  const keyOf = (kind) => (vertical && index?.[`${kind}_short`] ? `${kind}_short` : kind);

  async function load() {
    if (index) return index;
    try { index = await (await fetch("/static/samples/index.json", { cache: "no-cache" })).json(); } catch { index = {}; }
    return index;
  }
  const src = (entry, kind) => `/static/samples/${entry[kind === "poster" ? `poster_${language}` : language]}`;

  function openDialog(kind) {
    const entry = index?.[keyOf(kind)]; if (!entry) return;
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.className = "sample-dialog";
      dialog.innerHTML = `<div class="sample-dialog-head"><strong class="sample-dialog-title"></strong>
        <button type="button" class="btn btn-ghost btn-sm" data-close aria-label="Close">✕</button></div>
        <video class="sample-dialog-video" muted loop playsinline></video>
        <p class="sample-dialog-note"><span class="badge">Example only</span> <span class="sample-dialog-best"></span></p>`;
      dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
      dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
      dialog.addEventListener("close", () => dialog.querySelector("video").pause());
      document.body.append(dialog);
    }
    const video = dialog.querySelector("video");
    video.className = `sample-dialog-video ${entry.aspect === "16:9" ? "is-wide" : ""}`;
    video.poster = src(entry, "poster"); video.src = src(entry, "clip");
    dialog.querySelector(".sample-dialog-title").textContent = dialog.dataset.title = titleOf(kind);
    const bestBox = dialog.querySelector(".sample-dialog-best");
    bestBox.replaceChildren(...bestFor(kind));
    dialog.showModal();
    if (!reduced()) video.play().catch(() => {});
  }
  let titles = {};
  // two spans, so each translates on its own (i18n_vi.js)
  const bestFor = (kind) => [Object.assign(document.createElement("span"), { textContent: "Best for:" }), " ",
    Object.assign(document.createElement("span"), { textContent: BEST_FOR[kind] || "" })];
  const titleOf = (kind) => titles[kind] || kind;

  function decorate(card, kind) {
    const entry = index?.[keyOf(kind)];
    if (!entry || card.querySelector(".sample-thumb")) return;
    const thumb = document.createElement("span");
    thumb.className = `sample-thumb ${entry.aspect === "16:9" ? "is-wide" : ""}`;
    thumb.innerHTML = `<video muted loop playsinline preload="none" aria-hidden="true"></video><span class="sample-thumb-badge" role="button" tabindex="0" title="See an example" aria-label="See an example">⤢</span>`;
    const video = thumb.querySelector("video");
    video.poster = src(entry, "poster"); video.dataset.src = src(entry, "clip");
    const play = () => { if (reduced()) return; if (!video.src) video.src = video.dataset.src; video.play().catch(() => {}); };
    const stop = () => { if (card.getAttribute("aria-checked") !== "true" && card.getAttribute("aria-pressed") !== "true") video.pause(); };
    card.addEventListener("mouseenter", play); card.addEventListener("focus", play);
    card.addEventListener("mouseleave", stop); card.addEventListener("blur", stop);
    new MutationObserver(() => (card.getAttribute("aria-checked") === "true" ? play() : stop())).observe(card, { attributes: true, attributeFilter: ["aria-checked", "aria-pressed"] });
    // the card (and its clip) still chooses the kind; only the "Example" badge opens the larger example
    const badge = thumb.querySelector(".sample-thumb-badge");
    badge.addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); openDialog(kind); });
    badge.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); openDialog(kind); }
    });
    card.prepend(thumb);  // the card keeps its own description; "best for" is in the larger example's dialog
    titles[kind] = card.querySelector("strong, .t-name")?.textContent?.trim() || kind;
    if (card.getAttribute("aria-checked") === "true") play();
  }

  /** Add the clips to the cards under `root`: `[data-template]` Short templates and `[data-mode]` video types. */
  async function attach(root, { audience, shorts = false } = {}) {
    await load();
    vertical = shorts;
    language = audience === "international" ? "en" : "vi";
    root.querySelectorAll("[data-template]").forEach((card) => decorate(card, card.dataset.template));
    root.querySelectorAll("[data-mode]").forEach((card) => { if (MODES[card.dataset.mode]) decorate(card, MODES[card.dataset.mode]); });
  }
  /** The channel audience decides the clip language (Phase 72): Quốc tế -> English, otherwise Vietnamese. */
  async function setAudience(audience) {
    language = audience === "international" ? "en" : "vi";
    document.querySelectorAll(".sample-thumb video").forEach((video) => {
      const card = video.closest("[data-template], [data-mode]"); if (!card) return;
      const entry = index?.[keyOf(card.dataset.template || MODES[card.dataset.mode])]; if (!entry) return;
      const playing = !video.paused;
      video.poster = src(entry, "poster"); video.dataset.src = src(entry, "clip");
      if (video.src) { video.src = video.dataset.src; if (playing) video.play().catch(() => {}); }
    });
  }
  /** The kind's clip in the current language (null until the index is loaded or when the kind has none). */
  function clipFor(kind) {
    const entry = index?.[keyOf(kind)];
    return entry ? { src: src(entry, "clip"), poster: src(entry, "poster"), aspect: entry.aspect } : null;
  }
  return { attach, setAudience, openDialog, clipFor, BEST_FOR };
})();
window.TemplateSamples = TemplateSamples;
