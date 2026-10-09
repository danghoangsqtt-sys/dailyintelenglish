/** Shot Library page (Task 29.7): the ready-made pictures of the cast. Review each one once (approve / reject); only approved,
 * current shots are reused by a new episode, so a wrong outfit or a stare at the camera can never reach a video. */
(() => {
  const state = { shots: [], activities: [], scenes: [], characters: [], busy: false, activityBusy: false,
    activityEditing: null, filters: { scene_id: "", kind: "", review_state: "" }, activityFilters: { review_state: "" } };
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

  function activityScope(activity) {
    return activity.character_id ? state.characters.find((character) => character.id === activity.character_id)?.name || "Character" : "Generic";
  }

  function renderActivities() {
    const grid = byId("activity-grid");
    grid.replaceChildren();
    const scope = byId("activity-filter-scope").value;
    const visible = state.activities.filter((activity) => !scope || (scope === "generic" ? !activity.character_id : activity.character_id));
    byId("activity-empty").hidden = visible.length > 0;
    const counts = { approved: 0, pending: 0, rejected: 0 };
    visible.forEach((activity) => { counts[activity.review_state] += 1; });
    byId("activity-count").textContent = visible.length ? `${visible.length} activity pictures · ${counts.approved} approved · ${counts.pending} waiting for review · ${counts.rejected} rejected` : "";
    visible.forEach((activity) => {
      const card = document.createElement("article");
      card.className = `shot-card is-${activity.review_state}`;
      card.dataset.activityId = activity.id;
      const image = document.createElement("img");
      image.src = `${activity.content_url}?v=${encodeURIComponent(activity.updated_at)}`;
      image.alt = `${activity.activity} activity illustration`;
      image.loading = "lazy";
      image.addEventListener("click", () => openActivity(activity));
      const title = document.createElement("p");
      title.className = "shot-title";
      title.textContent = `${activity.activity} · ${activityScope(activity)}`;
      const meta = document.createElement("p");
      meta.className = "shot-meta";
      meta.textContent = [...activity.context_tags, activity.variant].filter(Boolean).join(" · ") || "No context tags";
      const badges = document.createElement("div");
      badges.className = "track-badges";
      badges.append(badge(activity.review_state === "pending" ? "needs review" : activity.review_state,
        activity.review_state === "approved" ? "is-pace" : activity.review_state === "rejected" ? "is-warning" : "is-missing"));
      if (activity.use_count) badges.append(badge(`used ${activity.use_count}×`));
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const edit = document.createElement("button");
      edit.type = "button"; edit.className = "btn btn-ghost btn-sm"; edit.textContent = "Preview / edit";
      edit.disabled = state.activityBusy; edit.addEventListener("click", () => openActivity(activity));
      const approve = document.createElement("button");
      approve.type = "button"; approve.className = "btn btn-primary btn-sm"; approve.textContent = "Approve";
      approve.disabled = state.activityBusy || activity.review_state === "approved";
      approve.addEventListener("click", () => reviewActivity(activity.id, "approved"));
      const reject = document.createElement("button");
      reject.type = "button"; reject.className = "btn btn-ghost btn-sm"; reject.textContent = "Reject";
      reject.disabled = state.activityBusy || activity.review_state === "rejected";
      reject.addEventListener("click", () => reviewActivity(activity.id, "rejected"));
      actions.append(edit, approve, reject);
      card.append(image, title, meta, badges, actions);
      grid.append(card);
    });
  }

  async function refreshActivities() {
    try {
      state.activities = await Api.listLibraryActivities(state.activityFilters);
    } catch (error) {
      showMessage(error.message || "Could not load the Activity Library.");
    }
    renderActivities();
  }

  async function reviewActivity(id, reviewState) {
    state.activityBusy = true; renderActivities();
    try { await Api.reviewLibraryActivity(id, reviewState); showMessage(""); }
    catch (error) { showMessage(error.message || "Could not save the activity review."); }
    state.activityBusy = false;
    await refreshActivities();
  }

  function activityValues(values) {
    return values.split(",").map((value) => value.trim()).filter(Boolean);
  }

  function fillActivityCharacterSelect(select, genericLabel = "Generic") {
    select.replaceChildren(new Option(genericLabel, ""));
    state.characters.forEach((character) => select.append(new Option(character.name, character.id)));
  }

  async function openActivity(activity) {
    state.activityEditing = activity;
    const select = byId("activity-character");
    fillActivityCharacterSelect(select);
    select.value = activity.character_id || "";
    byId("activity-name").value = activity.activity;
    byId("activity-context").value = activity.context_tags.join(", ");
    byId("activity-aliases").value = activity.aliases.join(", ");
    byId("activity-variant").value = activity.variant || "";
    byId("activity-preview").src = `${activity.content_url}?v=${encodeURIComponent(activity.updated_at)}`;
    byId("activity-history").textContent = `${activity.use_count} render use${activity.use_count === 1 ? "" : "s"}`;
    const dialog = byId("activity-dialog");
    if (!dialog.open) dialog.showModal();
  }

  async function saveActivity(event) {
    event.preventDefault();
    if (!state.activityEditing || state.activityBusy) return;
    state.activityBusy = true;
    byId("activity-save-btn").disabled = true;
    try {
      await Api.updateLibraryActivity(state.activityEditing.id, {
        character_id: byId("activity-character").value || null,
        activity: byId("activity-name").value,
        context_tags: activityValues(byId("activity-context").value),
        aliases: activityValues(byId("activity-aliases").value),
        variant: byId("activity-variant").value,
      });
      byId("activity-dialog").close(); showMessage("Activity metadata saved.", "success");
    } catch (error) { showMessage(error.message || "Could not save activity metadata."); }
    state.activityBusy = false; byId("activity-save-btn").disabled = false;
    await refreshActivities();
  }

  let activityUploadPreviewUrl = null;

  function clearActivityUploadPreview() {
    if (activityUploadPreviewUrl) URL.revokeObjectURL(activityUploadPreviewUrl);
    activityUploadPreviewUrl = null;
    byId("activity-upload-preview").removeAttribute("src");
    byId("activity-upload-preview").hidden = true;
    byId("activity-upload-placeholder").hidden = false;
    byId("activity-upload-selection").textContent = "No pictures selected.";
    byId("activity-upload-submit").disabled = true;
  }

  function activityTargetButton(id, name, picture = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "activity-target";
    button.dataset.characterId = id;
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", "false");
    if (picture) {
      const image = document.createElement("img");
      image.src = picture;
      image.alt = "";
      button.append(image);
    } else {
      const icon = document.createElement("span");
      icon.className = "activity-target-icon";
      icon.textContent = id ? name.slice(0, 1).toUpperCase() : "🖼️";
      button.append(icon);
    }
    const label = document.createElement("span");
    label.className = "activity-target-name";
    label.textContent = name;
    button.append(label);
    button.addEventListener("click", () => selectActivityTarget(id));
    return button;
  }

  function renderActivityTargets() {
    const targets = byId("activity-upload-targets");
    targets.replaceChildren(activityTargetButton("", "Generic"));
    state.characters.forEach((character) => {
      targets.append(activityTargetButton(
        character.id, character.name, character.face_url || character.reference_url || character.body_url || "",
      ));
    });
    selectActivityTarget(byId("activity-upload-character").value || "");
  }

  function selectActivityTarget(characterId) {
    byId("activity-upload-character").value = characterId;
    byId("activity-upload-targets").querySelectorAll(".activity-target").forEach((button) => {
      const selected = button.dataset.characterId === characterId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-checked", String(selected));
    });
  }

  function openActivityUpload() {
    byId("activity-upload-form").reset();
    clearActivityUploadPreview();
    renderActivityTargets();
    byId("activity-upload-dialog").showModal();
  }

  function previewActivityUpload() {
    clearActivityUploadPreview();
    const files = byId("activity-upload-file").files;
    const file = files[0];
    if (!file) return;
    activityUploadPreviewUrl = URL.createObjectURL(file);
    const preview = byId("activity-upload-preview");
    preview.src = activityUploadPreviewUrl;
    preview.hidden = false;
    byId("activity-upload-placeholder").hidden = true;
    byId("activity-upload-selection").textContent = `${files.length} picture${files.length === 1 ? "" : "s"} selected.`;
    byId("activity-upload-submit").disabled = false;
  }

  async function uploadActivity(event) {
    event.preventDefault();
    if (state.activityBusy) return;
    state.activityBusy = true;
    const button = byId("activity-upload-submit");
    button.disabled = true;
    const originalLabel = button.textContent;
    button.textContent = "AI is analyzing…";
    try {
      const result = await Api.smartUploadLibraryActivities(new FormData(event.currentTarget));
      if (result.items.length) {
        byId("activity-upload-dialog").close();
        clearActivityUploadPreview();
      }
      await refreshActivities();
      const localCount = result.items.filter((item) => item.analysis_source === "local_ai").length;
      const cloudCount = result.items.filter((item) => item.analysis_source === "cloud_ai").length;
      const fallbackCount = result.items.length - localCount - cloudCount;
      const parts = [`${result.items.length} picture${result.items.length === 1 ? "" : "s"} added`];
      if (localCount) parts.push(`${localCount} described locally`);
      if (cloudCount) parts.push(`${cloudCount} described by cloud fallback`);
      if (fallbackCount) parts.push(`${fallbackCount} need a quick metadata review`);
      if (result.rejected.length) parts.push(`${result.rejected.length} rejected`);
      showMessage(`${parts.join(" · ")}.`, result.items.length ? "success" : "error");
    } catch (error) {
      showMessage(error.message || "Could not add the activity pictures.");
    } finally {
      state.activityBusy = false;
      button.textContent = originalLabel;
      button.disabled = byId("activity-upload-file").files.length === 0;
    }
  }

  async function importActivities() {
    const button = byId("activity-import-btn"), list = byId("activity-import-result");
    button.disabled = true; list.replaceChildren();
    const add = (text, className = "") => { const item = document.createElement("li"); item.textContent = text; item.className = className; list.append(item); };
    try {
      const result = await Api.importLibraryActivities();
      add(`${result.imported.length} activity picture${result.imported.length === 1 ? "" : "s"} imported.`);
      result.rejected.forEach((item) => add(`${item.file}: ${item.reason}`, "is-error"));
    } catch (error) { add(error.message || "Could not import activity pictures.", "is-error"); }
    button.disabled = false;
    await refreshActivities();
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

  async function refreshInbox() {
    try {
      const inbox = await Api.getLibraryInbox();
      byId("inbox-folder").textContent = inbox.folder;
      byId("inbox-count").textContent = inbox.files.length
        ? `${inbox.files.length} picture${inbox.files.length === 1 ? "" : "s"} waiting in the folder` : "The folder is empty.";
      byId("import-btn").disabled = state.busy || inbox.files.length === 0;
    } catch (error) {
      console.error("Failed to read the inbox folder:", error);
    }
  }

  async function importInbox() {
    state.busy = true;
    byId("import-btn").disabled = true;
    const list = byId("import-result");
    list.replaceChildren();
    try {
      const result = await Api.importLibraryInbox();
      const summary = document.createElement("li");
      summary.textContent = `${result.imported.length} imported, ${result.skipped.length} left in the folder.`;
      list.append(summary);
      result.imported.filter((item) => item.cropped).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.file}: cropped to 16:9 (the top was kept).`;
        list.append(li);
      });
      result.skipped.forEach((item) => {
        const li = document.createElement("li");
        li.className = "is-error";
        li.textContent = `${item.file}: ${item.reason}`;
        list.append(li);
      });
    } catch (error) {
      showMessage(error.message || "Could not import the pictures.");
    }
    state.busy = false;
    await load();
    await refreshInbox();
  }

  async function refreshBackgrounds() {
    try {
      const status = await Api.getLibraryBackgrounds();
      byId("bg-folder").textContent = status.folder;
      byId("bg-count").textContent = `${status.images} background picture${status.images === 1 ? "" : "s"} in the folder`;
    } catch (error) {
      console.error("Failed to read the backgrounds folder:", error);
    }
  }

  async function importBackgrounds() {
    byId("bg-import-btn").disabled = true;
    const list = byId("bg-result");
    list.replaceChildren();
    const add = (text, className = "") => {
      const li = document.createElement("li");
      li.textContent = text;
      if (className) li.className = className;
      list.append(li);
    };
    try {
      const result = await Api.importLibraryBackgrounds();
      add(`${result.imported.length} backgrounds imported, ${result.unchanged.length} unchanged, ${result.skipped.length} skipped.`);
      result.imported.filter((item) => item.cropped).forEach((item) => add(`${item.file}: cropped to 16:9.`));
      result.skipped.forEach((item) => add(`${item.file}: ${item.reason}`, "is-error"));
    } catch (error) {
      add(error.message || "Could not import the backgrounds.", "is-error");
    }
    byId("bg-import-btn").disabled = false;
    await refreshBackgrounds();
  }

  async function refreshSprites() {
    try {
      const status = await Api.getLibrarySprites();
      byId("sprite-folder").textContent = status.folder;
      byId("sprite-count").textContent = `${status.inbox.length} sprite picture${status.inbox.length === 1 ? "" : "s"} in the folder`;
      const list = byId("sprite-sets");
      list.replaceChildren();
      status.sets.forEach((set) => {
        const li = document.createElement("li");
        li.dataset.character = set.name;
        if (!set.has_set) {
          li.textContent = `${set.name}: no sprites yet.`;
        } else {
          const missing = set.missing.length ? ` Missing: ${set.missing.join(", ")}.` : "";
          li.textContent = `${set.name}: ${set.faces} of ${set.faces_total} faces, ${set.gestures} of ${set.gestures_total} gestures` +
            `${set.usable ? "" : " (not usable: calm__closed and calm__open are needed)"}.${missing}`;
          if (!set.usable) li.className = "is-error";
        }
        list.append(li);
      });
    } catch (error) {
      console.error("Failed to read the sprite sets:", error);
    }
  }

  async function importSprites() {
    byId("sprite-import-btn").disabled = true;
    const list = byId("sprite-result");
    list.replaceChildren();
    const add = (text, className = "") => {
      const li = document.createElement("li");
      li.textContent = text;
      if (className) li.className = className;
      list.append(li);
    };
    try {
      const result = await Api.importLibrarySprites();
      add(`${result.imported.length} sprite set${result.imported.length === 1 ? "" : "s"} imported: ` +
        (result.imported.map((item) => `${item.name} (${item.pictures} pictures)`).join(", ") || "none") + ".");
      result.refused.forEach((item) => add(`${item.file}: ${item.reason}`, "is-error"));
      result.ignored.forEach((file) => add(`${file}: not a sprite name, ignored.`));
    } catch (error) {
      add(error.message || "Could not import the sprites.", "is-error");
    }
    byId("sprite-import-btn").disabled = false;
    await refreshSprites();
  }

  function setup() {
    byId("import-btn").addEventListener("click", importInbox);
    byId("bg-import-btn").addEventListener("click", importBackgrounds);
    byId("sprite-import-btn").addEventListener("click", importSprites);
    byId("activity-import-btn").addEventListener("click", importActivities);
    byId("activity-upload-open").addEventListener("click", openActivityUpload);
    byId("activity-upload-file").addEventListener("change", previewActivityUpload);
    byId("activity-upload-form").addEventListener("submit", uploadActivity);
    byId("activity-upload-close").addEventListener("click", () => byId("activity-upload-dialog").close());
    byId("activity-upload-dialog").addEventListener("close", clearActivityUploadPreview);
    byId("activity-filter-state").addEventListener("change", (event) => {
      state.activityFilters.review_state = event.target.value; refreshActivities();
    });
    byId("activity-filter-scope").addEventListener("change", renderActivities);
    byId("activity-editor-form").addEventListener("submit", saveActivity);
    byId("activity-close-btn").addEventListener("click", () => byId("activity-dialog").close());
    refreshSprites();
    refreshBackgrounds();
    refreshInbox();
    [["filter-scene", "scene_id"], ["filter-kind", "kind"], ["filter-state", "review_state"]].forEach(([id, key]) => {
      byId(id).addEventListener("change", (event) => {
        state.filters[key] = event.target.value;
        load();
      });
    });
    byId("approve-all-btn").addEventListener("click", approveAllPending);
    load();
    refreshActivities();
  }

  document.addEventListener("DOMContentLoaded", setup);
})();
