/* global Api */
/**
 * Phase 90 (D128–D130): edit a word-roots or grammar Short on its video, like a video editor -- the beats on the left,
 * the 9:16 video playing in the middle (the app's Remotion preview player), the selected beat's cards on the right.
 * Every edit shows on the video at once; cards autosave (their audio stays); a spoken text edit marks only that line's
 * audio to be made again ("Make the voice again"); the video is rendered once with Step 5's Generate button.
 */
const BeatEditor = (() => {
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ROLES = [["s", "S (subject)"], ["v", "V (verb)"], ["o", "O (object)"], ["be", "BE"], ["ing", "-ing"], ["v3", "V3"],
    ["modal", "Modal"], ["have", "HAVE"], ["adj", "Adjective"], ["plain", "Plain"]];
  const KINDS = [["formula", "Formula"], ["compare", "Two sentences"], ["example", "Example sentence"], ["rule", "Rule"],
    ["sticker", "Sticker"], ["stamp", "Stamp"], ["lego", "Pieces that join"], ["table", "Table"], ["formulas", "Formula list"],
    ["promise", "Yellow card"], ["core", "Core rule"], ["quiz", "Quiz"]];
  const BEAT_NAMES = { hook: "Hook", scene: "Scene", summary: "Summary", core: "Core rule", quiz: "Quiz", follow: "Follow",
    twins: "Same root?", wheel: "Promise", origin: "Origin", head: "Head", head_logic: "Head logic", head_example: "Head example",
    whole: "Word", split: "Split", example: "Example" };
  const NEW_CARDS = { formula: { chips: [{ text: "S", role: "s" }, { text: "BE", role: "be" }, { text: "V3", role: "v3" }] },
    compare: { left_en: "", left_vi: "", right_en: "", right_vi: "" }, example: { en: "", vi: "", marks: [] }, rule: { text: "" },
    sticker: { text: "" }, stamp: { text: "" }, lego: { chips: [{ text: "BE", role: "be" }, { text: "-ING", role: "ing" }], result: { text: "BEING", role: "be" } },
    table: { columns: ["", ""], rows: [["", ""]] }, formulas: { items: [""] }, promise: { text: "" }, core: { text: "" },
    quiz: { text: "", options: ["", ""] } };
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  async function mount(container, projectId) {
    const state = { view: null, lines: [], selected: 0, player: null, history: [], future: [], timer: null, saving: false,
      dirty: new Set(), message: "", busy: false };
    container.innerHTML = `<div class="beat-editor">
      <div class="beat-editor-head"><h2>Edit on the video</h2>
        <p class="section-hint">Click a beat, change its cards on the right and see it on the video at once. Cards keep their voice; a changed spoken line needs its voice made again. Generate the video once when you are done.</p>
        <div class="beat-editor-bar"><button type="button" class="btn btn-ghost btn-sm" data-act="undo">↶ Undo</button>
          <button type="button" class="btn btn-ghost btn-sm" data-act="redo">↷ Redo</button>
          <span class="beat-editor-status" aria-live="polite"></span>
          <button type="button" class="btn btn-primary btn-sm" data-act="voice" hidden>Make the voice again</button></div></div>
      <div class="beat-editor-grid"><ol class="beat-list" aria-label="Beats"></ol>
        <div class="beat-player"><div class="beat-player-box"></div><p class="section-hint beat-player-note"></p></div>
        <div class="beat-form"></div></div></div>`;
    const $ = (selector) => container.querySelector(selector);

    function card(index = state.selected) { return state.lines[index]?.card || {}; }
    function key() { return state.view?.key || "grammar"; }
    function status(text) { $(".beat-editor-status").textContent = text; }

    // ---------- the preview player: the edited cards go straight into its props
    function props() {
      const base = clone(state.view.props);
      base.lines.forEach((line, index) => {
        const picture = line[key()]?.pictureUrl;
        line[key()] = { ...clone(state.lines[index].card), ...(picture ? { pictureUrl: picture } : {}) };
        line.text = state.lines[index].text;
      });
      return base;
    }
    function refreshPlayer(seek = false) {
      if (!window.SoloPreview) { $(".beat-player-note").textContent = "The preview player is not available."; return; }
      const data = props();
      if (state.player) state.player.update(data); else state.player = window.SoloPreview.mount($(".beat-player-box"), data);
      if (seek) state.player.seek(Math.round(((data.lines[state.selected]?.startSec || 0) + 0.4) * data.fps));
      $(".beat-player-note").textContent = state.view.with_audio ? "" : "Silent preview with estimated timings: make the voice to hear it.";
    }

    // ---------- grammar scenes: a header or a card edited on one line is applied to its scene's other lines
    // the lines of a scene, found from the card as it was before the edit (its title may be the edited field)
    function sceneOf(here) {
      return state.lines.map((line, at) => at).filter((at) => card(at).beat === here.beat && card(at).scene === here.scene
        && (here.beat !== "scene" || card(at).title === here.title));
    }
    function applyGrammar(index, before, after) {
      const members = sceneOf(before);
      for (const at of members) {
        if (at === index) continue;
        const other = card(at);
        for (const field of ["label", "title", "subtitle"]) if (other[field] === before[field]) other[field] = after[field];
        // the same card (by content) changed in a later line of the scene: change it there too
        if (at > index) {
          other.cards = other.cards.map((item) => {
            const found = before.cards.findIndex((old) => same(old, item));
            return found >= 0 && after.cards[found] ? clone(after.cards[found]) : item;
          }).filter((item) => !(before.cards.some((old) => same(old, item)) && !after.cards.some((now) => same(now, item))));
          const added = after.cards.filter((now) => !before.cards.some((old) => same(old, now)) && !other.cards.some((it) => same(it, now)));
          if (added.length && other.cards.length) other.cards.push(...clone(added));
        }
        state.dirty.add(at);
      }
    }

    function change(mutate) {
      const index = state.selected;
      const before = clone(card(index));
      state.history.push(clone(state.lines)); state.future = [];
      if (state.history.length > 100) state.history.shift();
      mutate(card(index));
      if (key() === "grammar") applyGrammar(index, before, card(index));
      state.dirty.add(index);
      refreshPlayer(); renderList(); scheduleSave();
    }
    function scheduleSave() { clearTimeout(state.timer); status("Saving…"); state.timer = setTimeout(save, 800); }
    async function save() {
      if (state.saving) { scheduleSave(); return; }
      const indexes = [...state.dirty]; state.dirty.clear();
      if (!indexes.length) { status("Saved"); return; }
      state.saving = true;
      try {
        await Api.saveBeats(projectId, indexes.map((at) => ({ line_id: state.lines[at].id, card: state.lines[at].card })));
        status("Saved");
      } catch (error) {
        indexes.forEach((at) => state.dirty.add(at));
        status(`Not saved: ${error.message || error}`);
      } finally { state.saving = false; }
    }
    function travel(from, to) {
      if (!from.length) return;
      to.push(clone(state.lines));
      const snapshot = from.pop();
      snapshot.forEach((line, at) => { if (!same(line.card, state.lines[at].card)) state.dirty.add(at); });
      state.lines = snapshot;
      refreshPlayer(); renderList(); renderForm(); scheduleSave();
    }

    // ---------- the beat list
    function renderList() {
      const list = $(".beat-list");
      list.innerHTML = state.lines.map((line, at) => {
        const c = line.card, label = BEAT_NAMES[c.beat] || c.beat || "Beat";
        const sub = key() === "grammar" ? (c.beat === "scene" ? ` ${c.scene}` : "") : (c.word ? ` · ${c.word}` : "");
        return `<li><button type="button" class="beat-item${at === state.selected ? " selected" : ""}" data-beat="${at}">
          <span class="beat-no">${at + 1}</span><span class="beat-kind"><span>${escape(label)}</span><span translate="no">${escape(sub)}</span></span>
          ${line.audio_ok ? "" : '<span class="beat-voice-dot" title="Its voice must be made again">●</span>'}
          <span class="beat-text">${escape(line.text)}</span></button></li>`;
      }).join("");
      const stale = state.lines.filter((line) => !line.audio_ok).length;
      const voice = $("[data-act='voice']");
      voice.hidden = !stale; voice.textContent = `Make the voice again (${stale})`;
      $("[data-act='undo']").disabled = !state.history.length; $("[data-act='redo']").disabled = !state.future.length;
    }

    // ---------- the form for the selected beat
    const field = (name, value, label, attrs = "") => `<label class="beat-field">${label}<input type="text" data-f="${name}" value="${escape(value)}" ${attrs}/></label>`;
    const roleSelect = (path, role) => `<select data-f="${path}" aria-label="Colour">${ROLES.map(([value, name]) =>
      `<option value="${value}"${value === role ? " selected" : ""}>${name}</option>`).join("")}</select>`;
    const chipRows = (base, chips) => chips.map((chip, at) => `<div class="beat-chip-row">
      <input type="text" data-f="${base}.${at}.text" value="${escape(chip.text)}" aria-label="Chip text"/>${roleSelect(`${base}.${at}.role`, chip.role)}
      <button type="button" class="btn btn-ghost btn-sm" data-act="chip-remove" data-path="${base}" data-at="${at}" aria-label="Remove">✕</button></div>`).join("")
      + `<button type="button" class="btn btn-ghost btn-sm" data-act="chip-add" data-path="${base}">+ Chip</button>`;

    function itemForm(item, at, count) {
      const p = `cards.${at}`;
      let body = "";
      if (item.kind === "formula" || item.kind === "lego") {
        body = chipRows(`${p}.chips`, item.chips || []);
        if (item.kind === "lego") body += `<div class="beat-chip-row">= <input type="text" data-f="${p}.result.text" value="${escape(item.result?.text)}" aria-label="Result"/>${roleSelect(`${p}.result.role`, item.result?.role)}</div>`;
        else body += field(`${p}.text`, item.text, "Note under it");
      } else if (item.kind === "compare") {
        body = field(`${p}.left_en`, item.left_en, "Left sentence") + field(`${p}.left_vi`, item.left_vi, "Left translation")
          + field(`${p}.right_en`, item.right_en, "Right sentence") + field(`${p}.right_vi`, item.right_vi, "Right translation") + field(`${p}.text`, item.text, "What they share");
      } else if (item.kind === "example") {
        body = field(`${p}.en`, item.en, "English sentence") + field(`${p}.vi`, item.vi, "Translation")
          + `<div class="beat-sub">Coloured words</div>` + chipRows(`${p}.marks`, item.marks || []);
      } else if (item.kind === "table") {
        const columns = item.columns || [];
        body = `<div class="beat-table" style="grid-template-columns:repeat(${columns.length},1fr) auto">`
          + columns.map((col, c) => `<input type="text" class="beat-table-head" data-f="${p}.columns.${c}" value="${escape(col)}" aria-label="Column ${c + 1}"/>`).join("") + "<span></span>"
          + (item.rows || []).map((row, r) => row.map((cell, c) => `<input type="text" data-f="${p}.rows.${r}.${c}" value="${escape(cell)}" aria-label="Row ${r + 1} column ${c + 1}"/>`).join("")
            + `<button type="button" class="btn btn-ghost btn-sm" data-act="row-remove" data-path="${p}" data-at="${r}" aria-label="Remove row">✕</button>`).join("")
          + `</div><button type="button" class="btn btn-ghost btn-sm" data-act="row-add" data-path="${p}">+ Row</button>`;
      } else if (item.kind === "formulas") {
        body = (item.items || []).map((text, i) => field(`${p}.items.${i}`, text, `Formula ${i + 1}`)).join("")
          + `<button type="button" class="btn btn-ghost btn-sm" data-act="item-add" data-path="${p}">+ Formula</button>`;
      } else if (item.kind === "quiz") {
        body = field(`${p}.text`, item.text, "Question (use ___ for the blank)") + (item.options || []).map((text, i) => field(`${p}.options.${i}`, text, `Option ${String.fromCharCode(65 + i)}`)).join("");
      } else {
        body = field(`${p}.text`, item.text, "Text");
      }
      const name = (KINDS.find(([value]) => value === item.kind) || [item.kind, item.kind])[1];
      return `<fieldset class="beat-card"><legend>${escape(name)}</legend>${body}
        <div class="beat-card-actions"><button type="button" class="btn btn-ghost btn-sm" data-act="card-up" data-at="${at}" ${at === 0 ? "disabled" : ""}>↑</button>
        <button type="button" class="btn btn-ghost btn-sm" data-act="card-down" data-at="${at}" ${at === count - 1 ? "disabled" : ""}>↓</button>
        <button type="button" class="btn btn-ghost btn-sm" data-act="card-remove" data-at="${at}">Remove card</button></div></fieldset>`;
    }

    function rootsForm(c) {
      const parts = (c.parts || []).map((part, at) => `<div class="beat-chip-row">
        <input type="text" data-f="parts.${at}.text" value="${escape(part.text)}" aria-label="Part"/>
        <select data-f="parts.${at}.role" aria-label="Role">${["prefix", "root", "suffix"].map((role) => `<option value="${role}"${role === part.role ? " selected" : ""}>${role}</option>`).join("")}</select>
        <input type="text" data-f="parts.${at}.meaning" value="${escape(part.meaning)}" aria-label="Meaning of the part"/></div>`).join("");
      return [c.word !== undefined ? field("word", c.word, "Word") : "", field("meaning", c.meaning, "Meaning"),
        parts ? `<div class="beat-sub">Split</div>${parts}` : "", c.breakdown !== undefined ? field("breakdown", c.breakdown, "Breakdown line") : "",
        ["example", "head_example"].includes(c.beat) ? field("example_en", c.example_en, "Example") + field("example_vi", c.example_vi, "Translation") : "",
        c.beat === "origin" ? field("origin", c.origin, "Origin form") : "",
        c.word ? `${field("picture", c.picture, "Picture description")}<button type="button" class="btn btn-ghost btn-sm" data-act="redraw">Draw the picture again</button>` : "",
      ].join("");
    }

    function renderForm() {
      const form = $(".beat-form"), line = state.lines[state.selected];
      if (!line) { form.innerHTML = ""; return; }
      const c = line.card;
      const header = key() === "grammar" ? field("label", c.label, "Scene label") + field("title", c.title, "Title") + field("subtitle", c.subtitle, "Subtitle") : "";
      const cards = key() === "grammar" ? (c.cards || []).map((item, at) => itemForm(item, at, c.cards.length)).join("")
        + `<div class="beat-add"><select data-act="kind" aria-label="Card kind">${KINDS.map(([value, name]) => `<option value="${value}">${name}</option>`).join("")}</select>
          <button type="button" class="btn btn-ghost btn-sm" data-act="card-add">+ Add card</button></div>` : rootsForm(c);
      form.innerHTML = `<h3>Beat ${state.selected + 1}</h3>
        <label class="beat-field">Spoken line<textarea data-act="text" rows="3">${escape(line.text)}</textarea></label>
        <button type="button" class="btn btn-ghost btn-sm" data-act="text-save" disabled>Save the spoken line</button>
        ${header}${cards}`;
    }

    // ---------- events
    function setPath(target, path, value) {
      const parts = path.split("."); let node = target;
      parts.slice(0, -1).forEach((part, i) => { if (node[part] === undefined) node[part] = /^\d+$/.test(parts[i + 1]) ? [] : {}; node = node[part]; });
      node[parts.at(-1)] = value;
    }
    function getPath(target, path) { return path.split(".").reduce((node, part) => node?.[part], target); }

    container.addEventListener("input", (event) => {
      const input = event.target.closest("[data-f]");
      if (input) change((c) => setPath(c, input.dataset.f, input.value));
      if (event.target.matches("[data-act='text']")) $("[data-act='text-save']").disabled = event.target.value.trim() === state.lines[state.selected].text;
    });
    container.addEventListener("change", (event) => {
      const input = event.target.closest("select[data-f]");
      if (input) change((c) => setPath(c, input.dataset.f, input.value));
    });
    container.addEventListener("click", async (event) => {
      const beat = event.target.closest("[data-beat]");
      if (beat) { state.selected = Number(beat.dataset.beat); renderList(); renderForm(); refreshPlayer(true); return; }
      const button = event.target.closest("[data-act]"); if (!button || button.tagName === "SELECT" || button.tagName === "TEXTAREA") return;
      const act = button.dataset.act, at = Number(button.dataset.at), path = button.dataset.path;
      if (act === "undo") return travel(state.history, state.future);
      if (act === "redo") return travel(state.future, state.history);
      if (act === "voice") return makeVoice(button);
      if (act === "text-save") return saveText(button);
      if (act === "redraw") return redraw(button);
      const edits = {
        "chip-add": (c) => getPath(c, path).push({ text: "?", role: "plain" }),
        "chip-remove": (c) => getPath(c, path).splice(at, 1),
        "row-add": (c) => { const item = getPath(c, path); item.rows = [...(item.rows || []), item.columns.map(() => "")]; },
        "row-remove": (c) => getPath(c, path).rows.splice(at, 1),
        "item-add": (c) => { const item = getPath(c, path); item.items = [...(item.items || []), ""]; },
        "card-up": (c) => c.cards.splice(at - 1, 0, c.cards.splice(at, 1)[0]),
        "card-down": (c) => c.cards.splice(at + 1, 0, c.cards.splice(at, 1)[0]),
        "card-remove": (c) => c.cards.splice(at, 1),
        "card-add": (c) => { const kind = $("[data-act='kind']").value; c.cards = [...(c.cards || []), { kind, ...clone(NEW_CARDS[kind]) }].slice(-5); },
      };
      if (edits[act]) { change(edits[act]); renderForm(); }
    });
    document.addEventListener("keydown", (event) => {
      if (!container.isConnected || !(event.ctrlKey || event.metaKey)) return;
      if (event.target.matches("input, textarea, select")) return;  // the field's own undo
      if (event.key.toLowerCase() === "z") { event.preventDefault(); travel(state.history, state.future); }
      if (event.key.toLowerCase() === "y") { event.preventDefault(); travel(state.future, state.history); }
    });

    async function saveText(button) {
      const text = $("[data-act='text']").value.trim(); if (!text) return;
      button.disabled = true; status("Saving…");
      try {
        await Api.saveBeatText(projectId, state.lines[state.selected].id, text);
        state.lines[state.selected].text = text; state.lines[state.selected].audio_ok = false;
        status("Saved · make the voice again for this line"); renderList(); refreshPlayer();
      } catch (error) { status(`Not saved: ${error.message || error}`); button.disabled = false; }
    }
    async function redraw(button) {
      const c = card(); button.disabled = true; status("Drawing the picture… (about a minute)");
      try {
        await save();
        await Api.redrawBeatPicture(projectId, c.word, c.picture || "");
        await reload(); status("Picture drawn");
      } catch (error) { status(`${error.message || error}`); } finally { button.disabled = false; }
    }
    // Phase 90.3: only the lines whose voice no longer matches are synthesized, then the mix is made again
    async function makeVoice(button) {
      if (state.busy) return; state.busy = true; button.disabled = true;
      try {
        await save();
        const stale = state.lines.filter((line) => !line.audio_ok);
        for (const [at, line] of stale.entries()) {
          status(`Making the voice ${at + 1}/${stale.length}…`);
          await Api.previewTtsLine(projectId, line.id, { reuse_cached: true });
        }
        status("Mixing the audio…");
        let music = null;
        try { music = (await Api.getAudioStatus(projectId))?.background_music || null; } catch { music = null; }
        await Api.generateAudio(projectId, music);
        await reload(); status("Voice made · generate the video when you are done");
      } catch (error) { status(`The voice could not be made: ${error.message || error}`); }
      finally { state.busy = false; button.disabled = false; }
    }

    async function reload() {
      state.view = await Api.getBeats(projectId);
      state.lines = state.view.lines.map((line) => ({ ...line, card: clone(line.card) }));
      state.selected = Math.min(state.selected, state.lines.length - 1);
      renderList(); renderForm(); refreshPlayer();
    }
    await reload();
    return { reload };
  }
  return { mount };
})();
window.BeatEditor = BeatEditor;
