/** Global Character and Scene Library. All server calls go through Api. */
(() => {
  const SHEET_LABELS = {
    full_body: "Full body",
    portrait_calm: "Calm",
    portrait_smile: "Smile",
    portrait_surprised: "Surprised",
  };
  const state = {
    characters: [], scenes: [], options: null, health: null,
    selectedId: null, editingSceneId: null, sceneFilter: "all", busy: false, progress: null,
  };

  const $ = (id) => document.getElementById(id);

  function message(text, error = false) {
    const box = $("library-message");
    box.hidden = !text;
    box.classList.toggle("error", error);
    box.setAttribute("role", error ? "alert" : "status");
    box.textContent = text || "";
  }

  function canGenerate() {
    return Boolean(state.health?.enabled && state.health?.venv_image_present);
  }

  function generationHint() {
    if (!state.health?.enabled) return "AI visuals generation is disabled in settings.";
    if (!state.health?.venv_image_present) return "The local image environment is missing.";
    return "";
  }

  function setGenerateButton(button, allowed) {
    button.disabled = state.busy || !canGenerate() || !allowed;
    button.title = generationHint() || (allowed ? "" : "Complete the previous character step first.");
  }

  function optionList(select, values) {
    select.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.append(option);
    });
  }

  function fillOptions() {
    const form = $("character-form");
    const mapping = {
      gender: state.options.genders,
      age_group: state.options.age_groups,
      top_color: state.options.colors,
      top_item: state.options.tops,
      bottom_color: state.options.colors,
      bottom_item: state.options.bottoms,
    };
    Object.entries(mapping).forEach(([name, values]) => optionList(form.elements[name], values));
    form.elements.bottom_color.value = "navy blue";
    const sceneForm = $("scene-form");
    optionList(sceneForm.elements.category, state.options.scene_categories || ["other"]);
    optionList(sceneForm.elements.time_of_day, state.options.times_of_day || ["day"]);
    sceneForm.elements.category.value = "other";
    sceneForm.elements.time_of_day.value = "day";
  }

  function selectedCharacter() {
    return state.characters.find((character) => character.id === state.selectedId) || null;
  }

  function assetCard(asset, label, fullBody = false) {
    const card = document.createElement("article");
    card.className = `library-asset${fullBody ? " full-body" : ""}`;
    const image = document.createElement("img");
    image.src = asset.url;
    image.alt = `${label} portrait`;
    const title = document.createElement("strong");
    title.textContent = label;
    card.append(image, title);
    if (asset.prompt_truncated) {
      const warning = document.createElement("div");
      warning.className = "library-truncation";
      warning.textContent = "⚠ description too long";
      card.append(warning);
    }
    return card;
  }

  function renderCharacterList() {
    const list = $("character-list");
    list.replaceChildren();
    if (!state.characters.length) {
      const empty = document.createElement("p");
      empty.className = "library-hint";
      empty.textContent = "No characters yet. Create your first character.";
      list.append(empty);
      return;
    }
    state.characters.forEach((character) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "library-card card";
      card.setAttribute("aria-current", String(character.id === state.selectedId));
      card.addEventListener("click", () => {
        state.selectedId = character.id;
        renderCharacters();
      });
      if (character.face_url) {
        const face = document.createElement("img");
        face.className = "library-face";
        face.src = character.face_url;
        face.alt = "";
        card.append(face);
      } else {
        const placeholder = document.createElement("span");
        placeholder.className = "library-placeholder";
        placeholder.textContent = "Portrait";
        card.append(placeholder);
      }
      const copy = document.createElement("span");
      const name = document.createElement("span");
      name.className = "library-card-name";
      name.textContent = character.name;
      const badge = document.createElement("span");
      badge.className = "library-badge";
      badge.textContent = character.status;
      copy.append(name, badge);
      card.append(copy);
      list.append(card);
    });
  }

  function renderCandidates(character) {
    const grid = $("candidate-grid");
    grid.replaceChildren();
    const candidates = character.assets.filter((asset) => asset.kind === "candidate");
    candidates.forEach((asset, index) => {
      const card = assetCard(asset, `Candidate ${index + 1}`);
      const pick = document.createElement("button");
      pick.className = "btn btn-ghost btn-sm";
      pick.type = "button";
      pick.textContent = character.reference_asset_id === asset.id ? "✓ Selected" : "Choose this portrait";
      pick.disabled = state.busy || character.status === "locked";
      pick.addEventListener("click", async () => {
        await act(async () => Api.pickCharacterReference(character.id, asset.id), "Portrait selected.");
      });
      card.append(pick);
      grid.append(card);
    });
  }

  function renderSheet(character) {
    const grid = $("sheet-grid");
    grid.replaceChildren();
    Object.entries(SHEET_LABELS).forEach(([kind, label]) => {
      const asset = character.assets.find((item) => item.kind === kind);
      if (!asset) return;
      const card = assetCard(asset, label, kind === "full_body");
      const buttons = document.createElement("div");
      buttons.className = "library-actions";
      const approve = document.createElement("button");
      approve.type = "button";
      approve.className = "btn btn-ghost btn-sm";
      approve.textContent = asset.approved ? "✓ Approved" : "✓ Approve";
      approve.disabled = state.busy || character.status === "locked";
      approve.addEventListener("click", () => act(
        () => Api.approveCharacterAsset(character.id, asset.id, !asset.approved),
        asset.approved ? "Approval removed." : "Sheet asset approved.",
      ));
      const regenerate = document.createElement("button");
      regenerate.type = "button";
      regenerate.className = "btn btn-ghost btn-sm";
      regenerate.textContent = "↻ Regenerate";
      setGenerateButton(regenerate, character.status !== "locked");
      regenerate.addEventListener("click", () => startJob(() => Api.generateCharacterSheet(character.id, kind)));
      buttons.append(approve, regenerate);
      card.append(buttons);
      grid.append(card);
    });
  }

  function renderEditor() {
    const character = selectedCharacter();
    const form = $("character-form");
    const locked = character?.status === "locked";
    $("editor-title").textContent = character ? character.name : "New character";
    for (const field of form.querySelectorAll("input, select")) {
      if (character && character[field.name] !== undefined) field.value = character[field.name];
      field.disabled = Boolean(locked);
    }
    $("save-character").textContent = character ? "Save character" : "Create character";
    $("save-character").disabled = Boolean(locked || state.busy);
    $("delete-character").hidden = !character;
    $("delete-character").disabled = state.busy;
    $("character-workflow").hidden = !character;
    if (!character) return;
    renderCandidates(character);
    renderSheet(character);
    setGenerateButton($("generate-candidates"), !locked);
    setGenerateButton($("generate-sheet"), Boolean(character.reference_asset_id && !locked));
    const approved = Object.keys(SHEET_LABELS).every((kind) =>
      character.assets.some((asset) => asset.kind === kind && asset.approved));
    $("lock-character").hidden = locked;
    $("lock-character").disabled = state.busy || !approved || !character.reference_asset_id;
    $("unlock-character").hidden = !locked;
    $("unlock-character").disabled = state.busy;
    $("lock-summary").textContent = locked
      ? "Appearance and outfit are locked. Unlock to make changes after removing this character from project casts."
      : `${Object.keys(SHEET_LABELS).filter((kind) => character.assets.some((asset) => asset.kind === kind && asset.approved)).length} of 4 sheet assets approved.`;
  }

  function renderCharacters() {
    renderCharacterList();
    renderEditor();
  }

  function renderSceneFilters() {
    const bar = $("scene-filters");
    bar.replaceChildren();
    const present = [...new Set(state.scenes.map((scene) => scene.category || "other"))].sort();
    if (!present.includes(state.sceneFilter)) state.sceneFilter = "all";
    ["all", ...present].forEach((category) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "btn btn-ghost btn-sm";
      chip.dataset.category = category;
      const count = category === "all" ? state.scenes.length
        : state.scenes.filter((scene) => (scene.category || "other") === category).length;
      chip.textContent = `${category === "all" ? "All" : category} (${count})`;
      chip.setAttribute("aria-pressed", String(state.sceneFilter === category));
      chip.addEventListener("click", () => { state.sceneFilter = category; renderScenes(); });
      bar.append(chip);
    });
  }

  function updateStaleWarning() {
    const form = $("scene-form");
    const original = state.scenes.find((scene) => scene.id === state.editingSceneId);
    $("scene-stale-warning").hidden = !(original && original.preview_url && (
      form.elements.place.value.trim() !== original.place || form.elements.time_of_day.value !== original.time_of_day));
  }

  function renderScenes() {
    renderSceneFilters();
    const grid = $("scene-grid");
    grid.replaceChildren();
    const visible = state.scenes.filter(
      (scene) => state.sceneFilter === "all" || (scene.category || "other") === state.sceneFilter);
    visible.forEach((scene) => {
      const card = document.createElement("article");
      card.className = "card library-scene";
      card.dataset.sceneId = scene.id;
      if (scene.preview_url) {
        const image = document.createElement("img");
        image.src = scene.preview_url;
        image.alt = `${scene.name} plate`;
        card.append(image);
      } else {
        const placeholder = document.createElement("div");
        placeholder.className = "scene-placeholder";
        placeholder.textContent = "No plate yet \u2014 generated on first use";
        card.append(placeholder);
      }
      const title = document.createElement("h3");
      title.textContent = scene.name;
      if (scene.is_builtin) {
        const badge = document.createElement("span");
        badge.className = "library-badge";
        badge.textContent = "Built-in";
        title.append(" ", badge);
      }
      const place = document.createElement("p");
      place.textContent = scene.place;
      const meta = document.createElement("p");
      meta.className = "scene-meta";
      const used = scene.used_count || 0;
      meta.textContent = `${scene.category || "other"} · ${scene.time_of_day || "day"} · ${scene.staging}`
        + ` · Used in ${used} project${used === 1 ? "" : "s"}`;
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "btn btn-ghost btn-sm";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => {
        state.editingSceneId = scene.id;
        $("scene-editor-title").textContent = `Edit ${scene.name}`;
        const form = $("scene-form");
        form.elements.name.value = scene.name;
        form.elements.place.value = scene.place;
        form.elements.staging.value = scene.staging;
        form.elements.category.value = scene.category || "other";
        form.elements.time_of_day.value = scene.time_of_day || "day";
        updateStaleWarning();
        $("save-scene").textContent = "Save scene";
        $("cancel-scene-edit").hidden = false;
        form.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "btn btn-ghost btn-sm";
      preview.textContent = scene.preview_url ? "↻ Plate" : "Make plate";
      setGenerateButton(preview, true);
      preview.addEventListener("click", () => startJob(() => Api.generateScenePreview(scene.id)));
      const duplicate = document.createElement("button");
      duplicate.type = "button";
      duplicate.className = "btn btn-ghost btn-sm";
      duplicate.textContent = "Duplicate";
      duplicate.addEventListener("click", () => act(() => Api.duplicateScene(scene.id), "Scene duplicated."));
      actions.append(edit, preview, duplicate);
      if (!scene.is_builtin) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-ghost btn-sm";
        remove.textContent = "Delete";
        remove.addEventListener("click", async () => {
          if (confirm(`Delete scene "${scene.name}"?`)) await act(() => Api.deleteScene(scene.id), "Scene deleted.");
        });
        actions.append(remove);
      }
      card.append(title, place, meta, actions);
      grid.append(card);
    });
  }

  async function refresh() {
    [state.characters, state.scenes, state.health] = await Promise.all([
      Api.listCharacters(), Api.listScenes(), Api.getVisualsHealth(),
    ]);
    if (state.selectedId && !selectedCharacter()) state.selectedId = null;
    renderCharacters();
    renderScenes();
  }

  async function act(operation, success) {
    try {
      state.busy = true;
      renderCharacters();
      await operation();
      await refresh();
      message(success);
    } catch (error) {
      message(error.message || "The library action failed.", true);
    } finally {
      state.busy = false;
      renderCharacters();
      renderScenes();
    }
  }

  async function startJob(operation) {
    if (state.busy || !canGenerate()) return;
    state.busy = true;
    renderCharacters();
    renderScenes();
    message("");
    try {
      const job = await operation();
      const container = $("library-progress");
      state.progress?.destroy();
      state.progress = GenerationStatus.mount({
        element: container, baselineSec: 120, startedAtIso: job.created_at,
      });
      const cancel = $("cancel-library-job");
      cancel.hidden = false;
      cancel.disabled = false;
      cancel.onclick = async () => {
        cancel.disabled = true;
        try {
          await Api.cancelImageJob(job.id);
        } catch (error) {
          cancel.disabled = false;
          message(error.message || "Could not cancel the job.", true);
        }
      };
      let current = job;
      while (!["complete", "error", "cancelled"].includes(current.status)) {
        state.progress.setProgress({ stageLabel: current.stage || "Queued", progressPercent: current.progress });
        await new Promise((resolve) => setTimeout(resolve, 500));
        current = await Api.getImageJob(job.id);
      }
      state.progress.setProgress({ stageLabel: current.stage, progressPercent: current.progress, done: true });
      if (current.status === "error") throw new Error(current.error || "Image generation failed.");
      await refresh();
      message(current.status === "cancelled" ? "Generation cancelled. Finished images were kept." : "Images are ready for review.");
    } catch (error) {
      message(error.message || "Image generation failed.", true);
    } finally {
      $("cancel-library-job").hidden = true;
      $("cancel-library-job").onclick = null;
      state.busy = false;
      renderCharacters();
      renderScenes();
    }
  }

  function resetSceneForm() {
    state.editingSceneId = null;
    $("scene-form").reset();
    $("scene-stale-warning").hidden = true;
    $("scene-editor-title").textContent = "New scene";
    $("save-scene").textContent = "Add scene";
    $("cancel-scene-edit").hidden = true;
  }

  function setupEvents() {
    $("new-character").addEventListener("click", () => {
      state.selectedId = null;
      $("character-form").reset();
      $("character-form").elements.bottom_color.value = "navy blue";
      renderCharacters();
      $("character-form").elements.name.focus();
    });
    $("character-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(event.currentTarget));
      const existing = selectedCharacter();
      await act(async () => {
        const saved = existing ? await Api.updateCharacter(existing.id, body) : await Api.createCharacter(body);
        state.selectedId = saved.id;
      }, existing ? "Character saved." : "Character created. Generate candidates next.");
    });
    $("delete-character").addEventListener("click", async () => {
      const character = selectedCharacter();
      if (!character || !confirm(`Delete "${character.name}"?`)) return;
      await act(async () => {
        try {
          await Api.deleteCharacter(character.id);
        } catch (error) {
          if (error.status !== 409 || !confirm("This character is used in a project. Remove it from those casts and delete it?")) throw error;
          await Api.deleteCharacter(character.id, true);
        }
        state.selectedId = null;
        $("character-form").reset();
      }, "Character deleted.");
    });
    $("generate-candidates").addEventListener("click", () => startJob(
      () => Api.generateCharacterCandidates(state.selectedId)));
    $("generate-sheet").addEventListener("click", () => startJob(
      () => Api.generateCharacterSheet(state.selectedId)));
    $("lock-character").addEventListener("click", () => act(
      () => Api.lockCharacter(state.selectedId), "Character locked."));
    $("unlock-character").addEventListener("click", () => act(
      () => Api.unlockCharacter(state.selectedId), "Character unlocked."));
    $("characters-tab").addEventListener("click", () => {
      $("characters-panel").hidden = false;
      $("scenes-panel").hidden = true;
      $("characters-tab").setAttribute("aria-selected", "true");
      $("scenes-tab").setAttribute("aria-selected", "false");
    });
    $("scenes-tab").addEventListener("click", () => {
      $("characters-panel").hidden = true;
      $("scenes-panel").hidden = false;
      $("characters-tab").setAttribute("aria-selected", "false");
      $("scenes-tab").setAttribute("aria-selected", "true");
    });
    $("scene-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(event.currentTarget));
      const editing = state.editingSceneId;
      const original = state.scenes.find((scene) => scene.id === editing);
      const patch = original
        ? Object.fromEntries(Object.entries(body).filter(([key, value]) => value !== original[key]))
        : body;
      await act(() => editing ? Api.updateScene(editing, patch) : Api.createScene(body),
        editing ? "Scene saved." : "Scene added.");
      resetSceneForm();
    });
    $("cancel-scene-edit").addEventListener("click", resetSceneForm);
    $("scene-form").elements.place.addEventListener("input", updateStaleWarning);
    $("scene-form").elements.time_of_day.addEventListener("change", updateStaleWarning);
    $("theme-toggle").addEventListener("click", Theme.toggle);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    setupEvents();
    try {
      state.options = await Api.getVisualsOptions();
      fillOptions();
      await refresh();
    } catch (error) {
      message(error.message || "The library could not load.", true);
    }
  });
})();
