/** Phase 93 (Task 93.7): the voices every video can use -- the local Vietnamese VieNeu voices and the Edge voices --
 *  filtered by language. Read only; a voice is chosen per speaker in Step 4. */
(() => {
  let rows = [];
  let lang = "vi";
  const LANGS = [["vi", "Vietnamese"], ["en-US", "English (US)"], ["en-GB", "English (UK)"], ["en", "Other English"]];

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => (key.startsWith("aria-") ? node.setAttribute(key, value) : (node[key] = value)));
    (Array.isArray(children) ? children : [children]).forEach((child) => child !== null && child !== undefined && node.append(child));
    return node;
  }
  const match = (row) => (lang === "en" ? row.locale.startsWith("en") && !["en-US", "en-GB"].includes(row.locale) : row.locale.startsWith(lang));

  function render() {
    document.getElementById("voice-filter").replaceChildren(...LANGS.map(([key, label]) => el("button", {
      type: "button", className: "e-chip", textContent: label, "aria-pressed": String(key === lang), onclick: () => { lang = key; render(); },
    })));
    const shown = rows.filter(match);
    document.getElementById("voices-count").textContent = `${rows.length} voices`;
    document.getElementById("voice-list").replaceChildren(...(shown.length ? shown.map((row) => el("div", { className: "e-row library-voice" }, [
      el("span", { className: "library-voice-ic", "aria-hidden": "true", textContent: row.gender === "male" ? "♂" : "♀" }),
      el("div", {}, [el("div", { className: "e-t", textContent: row.name }), el("div", { className: "e-m", textContent: row.detail })]),
      el("span", { className: `e-state${row.engine === "vieneu" ? " ok" : ""}`, textContent: row.engine === "vieneu" ? "VieNeu, on this computer" : "Edge, online" }),
      el("span"),
    ])) : [el("p", { className: "e-empty", textContent: "No voice in this language." })]));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const toggle = document.getElementById("theme-toggle");
    if (toggle) toggle.addEventListener("click", Theme.toggle);
    const [edge, engines] = await Promise.all([Api.listTtsVoices().catch(() => null), Api.listTtsEngines().catch(() => [])]);
    const vieneu = (engines || []).find((engine) => engine.id === "vieneu");
    rows = [
      ...((vieneu && vieneu.available && vieneu.voices) || []).map((v) => ({ engine: "vieneu", locale: "vi-VN", gender: v.gender, name: v.id, detail: [v.region, v.style].filter(Boolean).join(" · ") })),
      ...((edge && edge.voices) || []).map((v) => ({ engine: "edge_tts", locale: v.locale, gender: v.gender, name: v.voice_id.split("-").pop().replace("Neural", ""), detail: v.locale })),
    ];
    render();
  });
})();
