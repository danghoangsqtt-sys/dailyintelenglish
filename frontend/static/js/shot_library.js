/** Shot Library page (Task 29.7): the ready-made pictures of the cast. Review each one once (approve / reject); only approved,
 * current shots are reused by a new episode, so a wrong outfit or a stare at the camera can never reach a video. */
(() => {
  const state = { shots: [], scenes: [], characters: [], busy: false, filters: { scene_id: "", kind: "", review_state: "" } };
  const byId = (id) => document.getElementById(id);
  const KINDS = [["single", "Single"], ["duo_close", "Duo close"], ["duo_wide", "Duo wide"]];

  function sceneName(id) {
    return state.scenes.find((scene) => scene.id === id)?.name || "Scene";
  }

  function characterNames(ids) {
    return ids.map((id) => state.characters.find((c) => c.id === id)?.name || "Character").join(" + ");
  }

  function badge(text, className = "") {
    const element = document.createElement("span");
    element.className = `track-badge ${className}`.trim();
    element.textContent = text;
    return element;
  }

  function showMessage(text, kind = "error") {
    const element = byId("shot-message");
    element.textContent = text;
    element.className = text ? `message message-${kind}` : "";
    element.hidden = !text;
  }

  function renderCounts() {
    const counts = { approved: 0, pending: 0, rejected: 0, stale: 0 };
    state.shots.forEach((shot) => {
      counts[shot.review_state] += 1;
      if (shot.stale) counts.stale += 1;
    });
    byId("shot-count").textContent = state.shots.length
      ? `${state.shots.length} shots · ${counts.approved} approved · ${counts.pending} waiting for review · ${counts.rejected} rejected`
        + (counts.stale ? ` · ${counts.stale} stale` : "")
      : "";
    const approveAll = byId("approve-all-btn");
    approveAll.disabled = state.busy || !state.shots.some((shot) => shot.review_state === "pending" && !shot.stale);
  }

  function renderShots() {
    const grid = byId("shot-grid");
    grid.replaceChildren();
    byId("shot-empty").hidden = state.shots.length > 0;
    state.shots.forEach((shot) => {
      const card = document.createElement("article");
      card.className = `shot-card is-${shot.review_state}${shot.stale ? " is-stale" : ""}`;
      card.dataset.shotId = shot.id;
      const image = document.createElement("img");
      image.src = `${shot.content_url}?v=${encodeURIComponent(shot.updated_at)}`;
      image.alt = `${sceneName(shot.scene_id)} ${shot.kind} shot`;
      image.loading = "lazy";
      const title = document.createElement("p");
      title.className = "shot-title";
      title.textContent = `${KINDS.find(([id]) => id === shot.kind)?.[1] || shot.kind} · ${characterNames(shot.character_ids)}`;
      const meta = document.createElement("p");
      meta.className = "shot-meta";
      meta.textContent = [sceneName(shot.scene_id), shot.action, shot.expression !== "calm" ? shot.expression : ""]
        .filter(Boolean).join(" · ");
      const badges = document.createElement("div");
      badges.className = "track-badges";
      badges.append(badge(shot.review_state === "pending" ? "needs review" : shot.review_state,
        shot.review_state === "approved" ? "is-pace" : shot.review_state === "rejected" ? "is-warning" : "is-missing"));
      if (shot.stale) badges.append(badge("stale: a character changed", "is-warning"));
      if (shot.use_count) badges.append(badge(`used ${shot.use_count}×`));
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const approve = document.createElement("button");
      approve.type = "button";
      approve.className = shot.review_state === "approved" ? "btn btn-ghost btn-sm" : "btn btn-primary btn-sm";
      approve.dataset.action = "approve";
      approve.textContent = "Approve";
      approve.disabled = state.busy || shot.review_state === "approved" || shot.stale;
      approve.title = shot.stale ? "A character changed since this picture was drawn." : "";
      approve.addEventListener("click", () => review(shot.id, "approved"));
      const reject = document.createElement("button");
      reject.type = "button";
      reject.className = "btn btn-ghost btn-sm";
      reject.dataset.action = "reject";
      reject.textContent = "Reject";
      reject.disabled = state.busy || shot.review_state === "rejected";
      reject.addEventListener("click", () => review(shot.id, "rejected"));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn btn-ghost btn-sm delete-btn";
      remove.dataset.action = "delete";
      remove.textContent = "Delete";
      remove.disabled = state.busy;
      remove.addEventListener("click", () => removeShot(shot.id));
      actions.append(approve, reject, remove);
      card.append(image, title, meta, badges, actions);
      grid.append(card);
    });
    renderCounts();
  }

  async function load() {
    try {
      const [shots, scenes, characters] = await Promise.all([
        Api.listLibraryShots(state.filters), Api.listScenes(), Api.listCharacters(),
      ]);
      state.shots = shots;
      state.scenes = scenes;
      state.characters = characters;
      renderSceneFilter();
      showMessage("");
    } catch (error) {
      console.error("Failed to load the shot library:", error);
      showMessage(error.message || "Could not load the shot library.");
    }
    renderShots();
  }

  function renderSceneFilter() {
    const select = byId("filter-scene");
    if (select.options.length - 1 === state.scenes.length) return;
    const current = state.filters.scene_id;
    select.replaceChildren(new Option("All scenes", ""));
    state.scenes.forEach((scene) => select.append(new Option(scene.name, scene.id)));
    select.value = current;
  }

  async function review(id, reviewState) {
    state.busy = true;
    renderShots();
    try {
      await Api.reviewLibraryShot(id, reviewState);
      showMessage("");
    } catch (error) {
      showMessage(error.message || "Could not save the review.");
    }
    state.busy = false;
    await load();
  }

  async function removeShot(id) {
    if (!window.confirm("Delete this picture from the library? Episodes already made keep their own copy.")) return;
    state.busy = true;
    renderShots();
    try {
      await Api.deleteLibraryShot(id);
      showMessage("");
    } catch (error) {
      showMessage(error.message || "Could not delete the picture.");
    }
    state.busy = false;
    await load();
  }

  async function approveAllPending() {
    const pending = state.shots.filter((shot) => shot.review_state === "pending" && !shot.stale);
    if (!pending.length) return;
    if (!window.confirm(`Approve the ${pending.length} pictures in view? Only do this after looking at them.`)) return;
    state.busy = true;
    renderShots();
    let note = null;
    try {
      for (const shot of pending) await Api.reviewLibraryShot(shot.id, "approved");
      note = [`${pending.length} pictures approved.`, "success"];
    } catch (error) {
      note = [error.message || "Could not approve every picture.", "error"];
    }
    state.busy = false;
    await load();
    showMessage(...note); // load() clears the message, so the result is shown after it
  }

  function setup() {
    [["filter-scene", "scene_id"], ["filter-kind", "kind"], ["filter-state", "review_state"]].forEach(([id, key]) => {
      byId(id).addEventListener("change", (event) => {
        state.filters[key] = event.target.value;
        load();
      });
    });
    byId("approve-all-btn").addEventListener("click", approveAllPending);
    load();
  }

  document.addEventListener("DOMContentLoaded", setup);
})();
