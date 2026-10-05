/**
 * Step 5 Storyboard (Task 24.4): the AI proposes story beats, the owner edits and approves.
 * Self-contained; all server calls go through Api. The server stays authoritative -- the image
 * estimate here only previews the server's `estimate_images` while editing.
 */
(function () {
  const EXPRESSIONS = ["calm", "smile", "laugh", "surprised", "thinking", "worried", "serious"];
  const GPU_MINUTES_PER_IMAGE = 2;
  const NEW_PLACE = "__new__";
  const state = {
    projectId: new URLSearchParams(window.location.search).get("project_id"),
    lines: [], speakerNames: {}, lineSpeakers: [], cast: [], scenes: [],
    beats: [], meta: {}, proposal: null, dirty: false, busy: false, cap: 12,
  };
  const $ = (id) => document.getElementById(id);

  function element(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "text") node.textContent = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else node[key] = value;
    });
    children.forEach((child) => node.append(child));
    return node;
  }

  function placeKey(beat) {
    return beat.scene_id || `new:${beat.new_place || ""}`;
  }

  /** Mirror of storyboard_service.estimate_images (owner E4). */
  function estimateImages(beats, castSize) {
    const framing = Math.max(1, castSize + (castSize >= 2 ? 2 : 0));
    const actions = new Map();
    let inserts = 0;
    beats.forEach((beat) => {
      if (beat.kind === "insert") { inserts += 1; return; }
      const key = placeKey(beat);
      if (!actions.has(key)) actions.set(key, new Set());
      actions.get(key).add(beat.action || "");
    });
    let total = inserts;
    actions.forEach((found) => { total += framing + found.size - 1; });
    return total;
  }

  function sceneName(id) {
    const scene = state.scenes.find((item) => item.id === id);
    return scene ? scene.name : id;
  }

  function markDirty() {
    state.dirty = true;
    renderSummary();
  }

  function renderSummary() {
    const summary = $("storyboard-summary");
    summary.replaceChildren();
    const hasBeats = state.beats.length > 0;
    $("storyboard-save").disabled = state.busy || !hasBeats;
    $("storyboard-approve").disabled = state.busy || !hasBeats;
    $("storyboard-propose").disabled = state.busy || state.lines.length === 0;
    $("storyboard-propose").textContent = state.busy === "propose" ? "Proposing…"
      : hasBeats ? "Propose again with AI" : "Propose with AI";
    if (state.lines.length === 0) {
      summary.textContent = "Write or generate the script first; the storyboard follows its lines.";
      return;
    }
    if (!hasBeats) {
      summary.textContent = "No storyboard yet. Let the AI propose one from the script.";
      return;
    }
    const images = estimateImages(state.beats, state.cast.length);
    const cost = element("span", {
      className: images > state.cap ? "over-cap" : "",
      text: `${images}/${state.cap} images · ~${images * GPU_MINUTES_PER_IMAGE} GPU min`,
    });
    const parts = [`${state.beats.length} beats · `, cost];
    if (state.meta.status) parts.push(` · ${state.meta.status} (${state.meta.source})`);
    if (state.proposal) {
      parts.push(` · proposal: ${state.proposal.path}${state.proposal.reason ? ` — ${state.proposal.reason}` : ""}`);
    }
    if (state.dirty) parts.push(" · unsaved changes");
    summary.append(...parts);
  }

  function renderWarnings(warnings) {
    const box = $("storyboard-warnings");
    box.replaceChildren(...(warnings || []).map((text) => element("p", { text })));
  }

  function placeSelect(beat, index) {
    const select = element("select", { id: `beat-${index}-place`, name: "place" });
    const groups = new Map();
    state.scenes.forEach((scene) => {
      const category = scene.category || "other";
      if (!groups.has(category)) groups.set(category, element("optgroup", { label: category }));
      groups.get(category).append(element("option", { value: scene.id, text: scene.name }));
    });
    [...groups.keys()].sort().forEach((key) => select.append(groups.get(key)));
    select.append(element("option", { value: NEW_PLACE, text: "New place…" }));
    select.value = beat.scene_id || NEW_PLACE;
    return select;
  }

  function renderBeats() {
    const list = $("storyboard-beats");
    list.replaceChildren();
    state.beats.forEach((beat, index) => list.append(beatCard(beat, index)));
    renderSummary();
  }

  function beatCard(beat, index) {
    const card = element("article", { className: "card storyboard-beat", dataset: { index: String(index) } });
    const where = beat.kind === "insert" ? `insert: ${beat.new_place || "illustration"}`
      : beat.scene_id ? sceneName(beat.scene_id) : beat.new_place || "new place";
    card.append(element("h4", { text: `Beat ${index + 1} · lines ${beat.line_from + 1}–${beat.line_to + 1} · ${where}` }));
    const details = element("details", {}, [element("summary", { text: "Script lines" })]);
    for (let line = beat.line_from; line <= beat.line_to; line += 1) {
      const item = state.lines[line];
      if (item) details.append(element("p", { text: `${line + 1}. ${state.speakerNames[item.speaker_id] || "Speaker"}: ${item.text}` }));
    }
    card.append(details);

    const fields = element("div", { className: "storyboard-fields" });
    const kind = element("select", { id: `beat-${index}-kind`, name: "kind" }, [
      element("option", { value: "scene", text: "Scene (people in a place)" }),
      element("option", { value: "insert", text: "Insert (illustration)" }),
    ]);
    kind.value = beat.kind;
    kind.addEventListener("change", () => {
      beat.kind = kind.value;
      if (beat.kind === "insert") beat.scene_id = null;
      else if (!beat.scene_id && !beat.new_place) beat.scene_id = state.scenes[0] ? state.scenes[0].id : null;
      markDirty();
      renderBeats();
    });
    fields.append(element("label", { htmlFor: kind.id, text: "Kind" }), kind);

    if (beat.kind === "scene") {
      const place = placeSelect(beat, index);
      place.addEventListener("change", () => {
        beat.scene_id = place.value === NEW_PLACE ? null : place.value;
        if (beat.scene_id) beat.new_place = null;
        markDirty();
        renderBeats();
      });
      fields.append(element("label", { htmlFor: place.id, text: "Place" }), place);
    }
    if (beat.kind === "insert" || !beat.scene_id) {
      const custom = element("input", {
        id: `beat-${index}-new-place`, name: "new_place", maxLength: 40, value: beat.new_place || "",
        placeholder: beat.kind === "insert" ? "what the picture shows" : "a short place, up to 5 words",
      });
      custom.addEventListener("input", () => { beat.new_place = custom.value.trim() || null; markDirty(); });
      fields.append(element("label", { htmlFor: custom.id, text: beat.kind === "insert" ? "Shows" : "New place" }), custom);
    }
    const action = element("input", {
      id: `beat-${index}-action`, name: "action", maxLength: 40, value: beat.action || "",
      placeholder: "e.g. drinking coffee",
    });
    action.addEventListener("input", () => { beat.action = action.value.trim(); markDirty(); });
    fields.append(element("label", { htmlFor: action.id, text: "Action" }), action);
    const expression = element("select", { id: `beat-${index}-expression`, name: "expression" },
      EXPRESSIONS.map((value) => element("option", { value, text: value })));
    expression.value = beat.expression || "calm";
    expression.addEventListener("change", () => { beat.expression = expression.value; markDirty(); });
    fields.append(element("label", { htmlFor: expression.id, text: "Expression" }), expression);
    card.append(fields);

    const speakers = element("div", { className: "storyboard-speakers" }, [element("span", { text: "On screen:" })]);
    state.cast.forEach((member) => {
      const box = element("input", {
        type: "checkbox", id: `beat-${index}-speaker-${member.speaker_index}`,
        checked: (beat.speakers || []).includes(member.speaker_index),
      });
      box.addEventListener("change", () => {
        const chosen = new Set(beat.speakers || []);
        if (box.checked) chosen.add(member.speaker_index); else chosen.delete(member.speaker_index);
        if (chosen.size > 2) { box.checked = false; return; }
        beat.speakers = [...chosen].sort((a, b) => a - b);
        markDirty();
      });
      speakers.append(element("label", { htmlFor: box.id }, [box, ` ${member.speaker_name}`]));
    });
    card.append(speakers);

    const actions = element("div", { className: "library-actions" });
    if (beat.line_to > beat.line_from) {
      const at = element("select", { id: `beat-${index}-split-at`, ariaLabel: "Split before line" });
      for (let line = beat.line_from + 1; line <= beat.line_to; line += 1) {
        at.append(element("option", { value: String(line), text: `line ${line + 1}` }));
      }
      const split = element("button", { type: "button", className: "btn btn-ghost btn-sm", text: "Split at" });
      split.addEventListener("click", () => {
        const cut = Number(at.value);
        state.beats.splice(index + 1, 0, { ...beat, line_from: cut, speakers: [...(beat.speakers || [])] });
        beat.line_to = cut - 1;
        markDirty();
        renderBeats();
      });
      actions.append(split, at);
    }
    if (index < state.beats.length - 1) {
      const merge = element("button", { type: "button", className: "btn btn-ghost btn-sm", text: "Merge with next" });
      merge.addEventListener("click", () => {
        beat.line_to = state.beats[index + 1].line_to;
        state.beats.splice(index + 1, 1);
        markDirty();
        renderBeats();
      });
      actions.append(merge);
    }
    card.append(actions);
    return card;
  }

  function applyStoryboard(storyboard) {
    state.beats = storyboard.beats.map((beat) => ({ ...beat, speakers: [...(beat.speakers || [])] }));
    state.meta = { status: storyboard.status, source: storyboard.source };
    state.cap = storyboard.estimate ? storyboard.estimate.cap : state.cap;
    state.proposal = storyboard.proposal || null;
    state.dirty = false;
    renderWarnings(storyboard.warnings);
    renderBeats();
  }

  async function run(kind, operation) {
    if (state.busy) return;
    state.busy = kind;
    $("storyboard-error").textContent = "";
    renderSummary();
    try {
      applyStoryboard(await operation());
    } catch (error) {
      $("storyboard-error").textContent = error.message || "The storyboard request failed.";
    } finally {
      state.busy = false;
      renderSummary();
    }
  }

  function payload(status) {
    return {
      status,
      beats: state.beats.map((beat) => ({
        line_from: beat.line_from, line_to: beat.line_to, kind: beat.kind,
        scene_id: beat.kind === "scene" ? beat.scene_id : null,
        new_place: beat.kind === "insert" || !beat.scene_id ? beat.new_place : null,
        speakers: beat.speakers || [], action: beat.action || "", expression: beat.expression || "calm",
      })),
    };
  }

  async function load() {
    if (!state.projectId || !$("storyboard-section")) return;
    try {
      const [project, lines, visuals, scenes, storyboard] = await Promise.all([
        Api.getProject(state.projectId), Api.getScript(state.projectId), Api.getProjectVisuals(state.projectId),
        Api.listScenes(), Api.getStoryboard(state.projectId),
      ]);
      state.lines = lines;
      state.speakerNames = Object.fromEntries(project.speakers.map((speaker) => [speaker.id, speaker.name]));
      const namesByIndex = Object.fromEntries(project.speakers.map((speaker) => [speaker.speaker_index, speaker.name]));
      state.cast = visuals.cast.map((member) => ({
        ...member, speaker_name: namesByIndex[member.speaker_index] || `Speaker ${member.speaker_index + 1}`,
      }));
      state.scenes = scenes;
      applyStoryboard(storyboard);
    } catch (error) {
      $("storyboard-error").textContent = error.message || "The storyboard could not load.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!$("storyboard-section")) return;
    $("storyboard-propose").addEventListener("click", () => run("propose", () => Api.proposeStoryboard(state.projectId)));
    $("storyboard-save").addEventListener("click", () => run("save", () => Api.saveStoryboard(state.projectId, payload("draft"))));
    $("storyboard-approve").addEventListener("click", () => run("approve", () => Api.saveStoryboard(state.projectId, payload("approved"))));
    load();
  });
})();
