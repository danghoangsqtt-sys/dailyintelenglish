/** The Character Library page: the tab switch and the Scenes tab (the Profiles tab is `character_profiles.js`; the old
 * "Generate locally" character tab was removed in Phase 35, D89). All server calls go through Api. */
(() => {
  const state = {
    scenes: [], options: null, health: null,
    selectedSceneId: null, editingSceneId: null, sceneFilter: "all", busy: false, progress: null,
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
    button.title = generationHint();
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
    const sceneForm = $("scene-form");
    optionList(sceneForm.elements.category, state.options.scene_categories || ["other"]);
    optionList(sceneForm.elements.time_of_day, state.options.times_of_day || ["day"]);
    sceneForm.elements.category.value = "other";
    sceneForm.elements.time_of_day.value = "day";
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

  function sceneMeta(scene) {
    const used = scene.used_count || 0;
    return `${scene.category || "other"} · ${scene.time_of_day || "day"} · ${scene.staging}`
      + ` · Used in ${used} project${used === 1 ? "" : "s"}`;
  }

  function renderSceneDetail() {
    const scene = state.scenes.find((item) => item.id === state.selectedSceneId) || null;
    $("scene-detail").hidden = !scene;
    if (!scene) return;
    const plate = $("scene-detail-plate");
    plate.hidden = !scene.preview_url;
    $("scene-detail-empty").hidden = Boolean(scene.preview_url);
    if (scene.preview_url) {
      plate.src = scene.preview_url;
      plate.alt = `${scene.name} plate`;
    }
    $("scene-detail-name").textContent = scene.name;
    $("scene-detail-place").textContent = scene.place;
    $("scene-detail-meta").textContent = sceneMeta(scene);
  }

  function selectScene(scene) {
    state.selectedSceneId = scene.id;
    document.querySelectorAll("#scene-grid .library-scene").forEach((card) =>
      card.setAttribute("aria-current", String(card.dataset.sceneId === scene.id)));
    renderSceneDetail();
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
      card.setAttribute("aria-current", String(scene.id === state.selectedSceneId));
      card.addEventListener("click", (event) => {
        if (!event.target.closest("button")) selectScene(scene); // a button keeps its own meaning
      });
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
      meta.textContent = sceneMeta(scene);
      const actions = document.createElement("div");
      actions.className = "library-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "btn btn-ghost btn-sm";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => {
        selectScene(scene);
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
      preview.className = "btn btn-ghost btn-sm needs-local-gpu";  // Phase 71: drawn with Qwen on this computer
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
          if (await ConfirmDialog.ask(`Delete scene "${scene.name}"?`, { confirmLabel: "Delete", danger: true })) await act(() => Api.deleteScene(scene.id), "Scene deleted.");
        });
        actions.append(remove);
      }
      card.append(title, place, meta, actions);
      grid.append(card);
    });
    renderSceneDetail();
  }

  async function refresh() {
    [state.scenes, state.health] = await Promise.all([Api.listScenes(), Api.getVisualsHealth()]);
    renderScenes();
  }

  async function act(operation, success) {
    try {
      state.busy = true;
      renderScenes();
      await operation();
      await refresh();
      message(success);
    } catch (error) {
      message(error.message || "The library action failed.", true);
    } finally {
      state.busy = false;
      renderScenes();
    }
  }

  async function startJob(operation) {
    if (state.busy || !canGenerate()) return;
    state.busy = true;
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
    // Two tabs -- Profiles (default) and scenes.
    const tabs = ["profiles", "scenes"];
    tabs.forEach((name) => $(`${name}-tab`).addEventListener("click", () => {
      tabs.forEach((other) => {
        $(`${other}-panel`).hidden = other !== name;
        $(`${other}-tab`).setAttribute("aria-selected", String(other === name));
      });
    }));
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
