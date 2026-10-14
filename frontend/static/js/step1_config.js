/**
 * Step 1 — Script Config wizard. UI state + validation only; all persistence
 * goes through the centralized Api client (frontend/static/js/api.js), never
 * fetch() directly (CR-05).
 */
(() => {
  const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

  const GENRES = [
    { value: "instructions", label: "Instructions", icon: "📋" },
    { value: "directions", label: "Directions", icon: "🧭" },
    { value: "debate", label: "Debate", icon: "🗣️" },
    { value: "informational", label: "Informational", icon: "📰" },
    { value: "interview", label: "Interview", icon: "🎙️" },
    { value: "opinion", label: "Opinion", icon: "💭" },
    { value: "storytelling", label: "Storytelling", icon: "📖" },
    { value: "small_talk", label: "Small Talk", icon: "☕" },
    { value: "negotiation", label: "Negotiation", icon: "🤝" },
    { value: "news", label: "News", icon: "📡" },
  ];

  const ACCENTS = [
    { value: "american", label: "American", flag: "🇺🇸" },
    { value: "british", label: "British", flag: "🇬🇧" },
    { value: "australian", label: "Australian", flag: "🇦🇺" },
    { value: "canadian", label: "Canadian", flag: "🇨🇦" },
    { value: "irish", label: "Irish", flag: "🇮🇪" },
    {
      value: "scottish",
      label: "Scottish",
      flag: "🏴",
      note: "Uses the same voice as British — Edge TTS has no distinct Scottish voice yet",
    },
    { value: "indian", label: "Indian", flag: "🇮🇳" },
    { value: "singaporean", label: "Singaporean", flag: "🇸🇬" },
    { value: "new_zealand", label: "New Zealand", flag: "🇳🇿" },
    { value: "south_african", label: "South African", flag: "🇿🇦" },
  ];

  const GENDERS = ["male", "female", "neutral"];
  // Phase 40 (D119): no default cast -- each slot is "Character N" until a character profile is chosen, and the speaker
  // then takes that character's name (used in the script and the video).
  const slotLabel = (index) => `Character ${index + 1}`;
  const DURATION_PRESETS = [5, 10, 15, 20];
  const MIN_SPEAKERS = 1;
  const MAX_SPEAKERS = 6;

  const LANGUAGE_FEATURES = [
    { key: "collocation", label: "Collocations", default: true },
    { key: "idiom", label: "Idioms", default: true },
    { key: "slang", label: "Slang", default: false },
    { key: "local_expressions", label: "Local Expressions", default: false },
    { key: "phrasal_verbs", label: "Phrasal Verbs", default: true },
    { key: "business_register", label: "Business Register", default: false },
  ];

  const state = {
    cefr: "B1",
    duration: DURATION_PRESETS[1],
    customDurationActive: false,
    genre: GENRES[7].value, // small_talk
    accent: ACCENTS[0].value, // american
    speakers: [],
    profiles: [],  // Phase 33: the character profiles a speaker can be (Api.listProfiles)
    languageFeatures: Object.fromEntries(LANGUAGE_FEATURES.map((f) => [f.key, f.default])),
  };

  const projectId = new URLSearchParams(window.location.search).get("project_id");
  let pageMode = projectId ? "loading" : "create";
  let isSubmitting = false;

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function sanitizeSpeakerCount(rawValue) {
    const parsed = Math.round(Number(rawValue));
    if (!Number.isFinite(parsed)) return MIN_SPEAKERS;
    return clamp(parsed, MIN_SPEAKERS, MAX_SPEAKERS);
  }

  function escapeHtml(str) {
    // textContent -> innerHTML escapes &, <, > (text-node context) but leaves " and '
    // untouched, since neither is special in text content -- only inside an
    // attribute value, which is exactly how every call site here uses the result
    // (value="...", title="..."). Escape those too so this is genuinely safe for both.
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function showError(message) {
    const banner = document.getElementById("error-banner");
    banner.textContent = message;
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearError() {
    const banner = document.getElementById("error-banner");
    banner.hidden = true;
    banner.textContent = "";
  }

  function showStatus(message) {
    const banner = document.getElementById("status-banner");
    banner.textContent = message;
    banner.hidden = false;
  }

  function clearStatus() {
    const banner = document.getElementById("status-banner");
    banner.textContent = "";
    banner.hidden = true;
  }

  function setLoading(loading) {
    const btn = document.getElementById("submit-btn");
    btn.disabled = loading;
    btn.innerHTML = loading
      ? `<span class="spinner"></span> ${pageMode === "edit" ? "Saving…" : "Creating…"}`
      : pageMode === "edit"
        ? "Save Changes"
        : "Create Project";
  }

  // --- CEFR ---
  function renderCefr() {
    const select = document.getElementById("cefr");
    select.innerHTML = CEFR_LEVELS.map(
      (level) => `<option value="${level}" ${level === state.cefr ? "selected" : ""}>${level}</option>`
    ).join("");
    select.addEventListener("change", (e) => {
      state.cefr = e.target.value;
    });
  }

  // --- Duration ---
  function renderDurationPresets() {
    const container = document.getElementById("duration-presets");
    const customInput = document.getElementById("duration-custom");

    function draw() {
      container.innerHTML = DURATION_PRESETS.map(
        (minutes) =>
          `<button type="button" class="preset-btn" data-minutes="${minutes}" aria-pressed="${
            !state.customDurationActive && state.duration === minutes
          }">${minutes} min</button>`
      ).join("");
      container.innerHTML += `<button type="button" class="preset-btn" id="duration-custom-toggle" aria-pressed="${state.customDurationActive}">Custom</button>`;
      customInput.hidden = !state.customDurationActive;
      if (state.customDurationActive) customInput.value = state.duration || "";
    }

    container.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-minutes]");
      if (btn) {
        state.duration = Number(btn.dataset.minutes);
        state.customDurationActive = false;
        draw();
        return;
      }
      if (e.target.id === "duration-custom-toggle") {
        state.customDurationActive = true;
        draw();
        customInput.focus();
      }
    });

    customInput.addEventListener("input", (e) => {
      const value = parseFloat(e.target.value);
      state.duration = Number.isFinite(value) ? value : null;
    });

    draw();
  }

  // --- Speakers ---
  function syncSpeakersToCount(count) {
    const speakers = state.speakers;
    if (count > speakers.length) {
      for (let i = speakers.length; i < count; i++) {
        speakers.push({
          character_id: null,  // Phase 33 (D80): every speaker is a chosen character
          name: "",
          gender: GENDERS[i % 2],
          accent: state.accent,
          tts_engine: "edge_tts",
          voice_description: "",
          // Task 14.10: no explicit speed -- the server resolves this to the
          // project's CEFR-level default (CEFR_DEFAULT_TTS_SPEED) at creation.
          speed: null,
          pitch: 0.0,
          volume: 1.0,
        });
      }
    } else if (count < speakers.length) {
      speakers.length = count;
    }
  }

  function profilePicture(profile) {
    return profile?.pictures?.portrait || profile?.pictures?.base || null;
  }

  // Phase 33 (D80, D88): the speaker IS the chosen character -- the card shows it (picture, name, gender, accent) and keeps
  // the values only in hidden fields; nothing about the speaker is typed or picked here.
  function speakerCardHtml(speaker, index) {
    const profile = state.profiles.find((item) => item.id === speaker.character_id);
    const picture = profilePicture(profile);
    const accent = ACCENTS.find((item) => item.value === speaker.accent);
    return `
      <div class="card speaker-card" data-index="${index}">
        <div class="speaker-character">
          ${picture ? `<img src="${picture}" alt="" class="speaker-face" />` : '<span class="speaker-face speaker-face-empty" aria-hidden="true">?</span>'}
          <div class="speaker-identity">
            <span class="speaker-slot">${slotLabel(index)}</span>
            <strong id="speaker-label-${index}">${speaker.character_id ? escapeHtml(speaker.name) : "Choose a character"}</strong>
            ${speaker.character_id ? `<span class="speaker-meta">${escapeHtml(speaker.gender)} · ${escapeHtml(accent ? accent.label : speaker.accent)}</span>` : ""}
            <button type="button" class="btn ${speaker.character_id ? "btn-ghost" : "btn-primary"} btn-sm" data-choose="${index}">
              ${speaker.character_id ? "Change character" : "Choose character"}</button>
          </div>
        </div>
        <input type="hidden" id="speaker-name-${index}" value="${escapeHtml(speaker.name)}" />
        <input type="hidden" id="speaker-gender-${index}" value="${escapeHtml(speaker.gender)}" />
        <input type="hidden" id="speaker-accent-${index}" value="${escapeHtml(speaker.accent)}" />
      </div>`;
  }

  function voiceDiffers(speaker, profile) {
    const voice = profile.voice || {};
    return speaker.speed != null && (speaker.speed !== voice.speed || speaker.pitch !== voice.pitch || speaker.volume !== voice.volume);
  }

  async function applyProfile(index, profile) {
    const speaker = state.speakers[index];
    const keepVoice = pageMode === "edit" && speaker.character_id && voiceDiffers(speaker, profile)
      && !(await ConfirmDialog.ask(`Use ${profile.name}'s voice settings (speed ${profile.voice.speed}, pitch ${profile.voice.pitch}, `
        + `volume ${profile.voice.volume}) for ${slotLabel(index)}? Cancel keeps this project's own settings.`, { confirmLabel: "Use these settings" }));
    Object.assign(speaker, {
      character_id: profile.id, name: profile.name, gender: profile.gender, accent: profile.accent || speaker.accent,
    });
    if (!keepVoice && pageMode === "edit") {
      Object.assign(speaker, { speed: profile.voice.speed, pitch: profile.voice.pitch, volume: profile.voice.volume });
    }
    renderSpeakerCards();
  }

  function openSelector(index) {
    CharacterSelector.open({
      slots: state.speakers.map((speaker, i) => ({ index: i, label: slotLabel(i), characterId: speaker.character_id })),
      profiles: state.profiles,
      startSlot: index,
      onChoose: (slotIndex, profile) => applyProfile(slotIndex, profile),
    });
  }

  function renderSpeakerCards() {
    const grid = document.getElementById("speaker-grid");
    grid.innerHTML = state.speakers.map(speakerCardHtml).join("");
  }

  function setupSpeakers() {
    const numInput = document.getElementById("num-speakers");
    syncSpeakersToCount(sanitizeSpeakerCount(numInput.value));
    renderSpeakerCards();

    numInput.addEventListener("input", (e) => {
      const count = sanitizeSpeakerCount(e.target.value);
      e.target.value = count;
      syncSpeakersToCount(count);
      renderSpeakerCards();
    });

    document.getElementById("speaker-grid").addEventListener("click", (e) => {
      const button = e.target.closest("[data-choose]");
      if (button && !button.disabled) openSelector(Number(button.dataset.choose));
    });

    document.getElementById("speaker-grid").addEventListener("input", (e) => {
      const field = e.target.dataset.field;
      const index = Number(e.target.dataset.index);
      if (field === undefined || Number.isNaN(index)) return;
      state.speakers[index][field] = e.target.value;
    });

    document.getElementById("speaker-grid").addEventListener("change", (e) => {
      const field = e.target.dataset.field;
      const index = Number(e.target.dataset.index);
      if (field === undefined || Number.isNaN(index)) return;
      state.speakers[index][field] = e.target.value;
    });
  }

  // --- Genre / Accent chip grids ---
  function renderChipGrid(containerId, items, currentValue, onSelect) {
    const container = document.getElementById(containerId);
    function draw(value) {
      container.innerHTML = items
        .map(
          (item) =>
            `<button type="button" class="chip" data-value="${item.value}" aria-pressed="${item.value === value}" ${item.note ? `title="${escapeHtml(item.note)}"` : ""}>${item.icon || item.flag} ${item.label}</button>`
        )
        .join("");
    }
    container.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-value]");
      if (!btn) return;
      onSelect(btn.dataset.value);
      draw(btn.dataset.value);
    });
    draw(currentValue);
  }

  // --- Language feature toggles ---
  function renderLanguageFeatures() {
    const container = document.getElementById("language-features");
    container.innerHTML = LANGUAGE_FEATURES.map(
      (feature) => `
      <label class="toggle-row" for="feature-${feature.key}">
        <span>${feature.label}</span>
        <span class="switch">
          <input type="checkbox" id="feature-${feature.key}" data-key="${feature.key}" ${state.languageFeatures[feature.key] ? "checked" : ""} />
          <span class="switch-track"></span>
        </span>
      </label>`
    ).join("");

    container.addEventListener("change", (e) => {
      const key = e.target.dataset.key;
      if (!key) return;
      state.languageFeatures[key] = e.target.checked;
    });
  }

  function loadProjectIntoState(project) {
    document.getElementById("name").value = project.name || "";
    document.getElementById("topic").value = project.topic || "";

    state.cefr = project.cefr_level || state.cefr;
    const duration = Number(project.duration_minutes);
    if (Number.isFinite(duration) && duration > 0) {
      state.duration = duration;
      state.customDurationActive = !DURATION_PRESETS.includes(duration);
    }
    state.genre = project.genre || state.genre;
    state.accent = project.accent || state.accent;
    state.languageFeatures = Object.fromEntries(
      LANGUAGE_FEATURES.map((feature) => [
        feature.key,
        project.language_features?.[feature.key] ?? feature.default,
      ])
    );
    state.speakers = (project.speakers || []).map((speaker) => ({
      character_id: null,
      name: speaker.name ?? "",
      gender: speaker.gender ?? "neutral",
      accent: speaker.accent ?? state.accent,
      tts_engine: speaker.tts_engine ?? "edge_tts",
      voice_description: speaker.voice_description ?? "",
      speed: speaker.speed ?? 1.0,
      pitch: speaker.pitch ?? 0.0,
      volume: speaker.volume ?? 1.0,
    }));

    const speakerCount = sanitizeSpeakerCount(project.num_speakers ?? state.speakers.length);
    document.getElementById("num-speakers").value = speakerCount;
    syncSpeakersToCount(speakerCount);
  }

  function renderForm() {
    renderCefr();
    renderDurationPresets();
    setupSpeakers();
    renderChipGrid("genre-grid", GENRES, state.genre, (value) => {
      state.genre = value;
    });
    renderChipGrid("accent-grid", ACCENTS, state.accent, (value) => {
      state.accent = value;
    });
    renderLanguageFeatures();
  }

  function activateEditableForm() {
    const form = document.getElementById("config-form");
    form.hidden = false;
    document.getElementById("submit-btn").hidden = false;
    form.addEventListener("submit", handleSubmit);
    KeyboardShortcuts.init({ primaryButtonId: "submit-btn" });
  }

  function lockForm() {
    const form = document.getElementById("config-form");
    form.hidden = false;
    form.querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = true;
    });
    document.getElementById("submit-btn").hidden = true;
  }

  function configureCreateMode() {
    pageMode = "create";
    document.title = "New Project — Daily Beyond English";
    document.getElementById("page-title").textContent = "Step 1 — Project Configuration";
    document.getElementById("page-subtitle").textContent =
      "Set up the topic, level, speakers, and language focus for your new episode.";
    document.getElementById("submit-btn").textContent = "Create Project";
    clearStatus();
    activateEditableForm();
  }

  function configureEditMode() {
    pageMode = "edit";
    document.title = "Edit Project — Daily Beyond English";
    document.getElementById("page-title").textContent = "Step 1 — Edit Project Configuration";
    document.getElementById("page-subtitle").textContent =
      "Update this draft project's topic, level, speakers, and language focus.";
    document.getElementById("submit-btn").textContent = "Save Changes";
    clearStatus();
    activateEditableForm();
  }

  function configureLockedMode() {
    pageMode = "locked";
    document.title = "Project Configuration — Daily Beyond English";
    document.getElementById("page-title").textContent = "Step 1 — Project Configuration";
    document.getElementById("page-subtitle").textContent =
      "Review the configuration used for this project.";
    showStatus(
      "This project has progressed beyond Draft. Configuration is read-only because generated content " +
        "depends on it; changes here would not regenerate downstream work."
    );
    lockForm();
  }

  // --- Validation + submit ---
  function validate() {
    const errors = [];
    const name = document.getElementById("name").value.trim();
    if (!name) errors.push("Project name is required.");

    const topic = document.getElementById("topic").value.trim();
    if (!topic) errors.push("Topic is required.");

    if (!state.duration || state.duration <= 0) errors.push("Duration must be greater than 0 minutes.");

    if (state.speakers.length < MIN_SPEAKERS || state.speakers.length > MAX_SPEAKERS) {
      errors.push(`Number of speakers must be between ${MIN_SPEAKERS} and ${MAX_SPEAKERS}.`);
    }

    state.speakers.forEach((speaker, index) => {
      if (!speaker.character_id) errors.push(`${slotLabel(index)}: choose a character.`);
    });

    return errors;
  }

  function buildPayload() {
    return {
      name: document.getElementById("name").value.trim(),
      topic: document.getElementById("topic").value.trim(),
      cefr_level: state.cefr,
      duration_minutes: state.duration,
      num_speakers: state.speakers.length,
      genre: state.genre,
      accent: state.accent,
      language_features: { ...state.languageFeatures },
      speakers: state.speakers.map((speaker) => ({
        name: speaker.name.trim(),
        gender: speaker.gender,
        accent: speaker.accent,
        tts_engine: speaker.tts_engine ?? "edge_tts",
        voice_description: speaker.voice_description ?? "",
        // null (not a hardcoded 1.0) so an unset speed still resolves to the
        // CEFR-level default server-side; an existing, already-resolved speaker's
        // real speed passes through unchanged.
        speed: speaker.speed ?? null,
        pitch: speaker.pitch ?? 0.0,
        volume: speaker.volume ?? 1.0,
      })),
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (isSubmitting) return;
    clearError();

    const errors = validate();
    if (errors.length > 0) {
      showError(errors.join(" "));
      return;
    }

    isSubmitting = true;
    setLoading(true);
    try {
      const project =
        pageMode === "edit"
          ? await Api.updateProject(projectId, buildPayload())
          : await Api.createProject(buildPayload());
      // Phase 33 (D80): the chosen characters are the project's cast, by ID (never by name)
      await Api.setProjectCast(project.id, state.speakers.map((speaker, index) => ({
        speaker_index: index, character_id: speaker.character_id,
      })));
      // Phase 41 (D120): the project's own output folder (optional)
      try {
        await state.folderPanel?.save(project.id);
      } catch (folderError) {
        showError(`The project was saved, but its folder was not: ${folderError.message}`);
        isSubmitting = false;
        setLoading(false);
        return;
      }
      window.location.href = `/step2?project_id=${encodeURIComponent(project.id)}&name=${encodeURIComponent(project.name)}`;
    } catch (err) {
      console.error(`Failed to ${pageMode === "edit" ? "update" : "create"} project:`, err);
      showError(
        pageMode === "edit"
          ? "We couldn't save the project. Please check your input and try again."
          : "We couldn't create the project. Please check your input and try again."
      );
      isSubmitting = false;
      setLoading(false);
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    StepNav.render("step-nav", { projectId, currentStep: 1, variant: "workflow" });
    WorkspaceShell.init({
      sidebar: document.getElementById("pane-sidebar"),
      resizerLeft: document.getElementById("resizer-left"),
      inspector: document.getElementById("pane-inspector"),
      resizerRight: document.getElementById("resizer-right"),
      collapseBtn: document.getElementById("sidebar-collapse-btn"),
    });
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    const form = document.getElementById("config-form");
    form.hidden = true;

    try {
      state.profiles = await Api.listProfiles("state=active");
    } catch (err) {
      console.error("Failed to load characters:", err);
      showError("We couldn't load the characters. Please reload the page.");
    }

    state.folderPanel = window.ProjectFolder
      ? ProjectFolder.mount(document.getElementById("project-folder"), { projectId: projectId || null })
      : null;
    if (!projectId) {
      syncSpeakersToCount(sanitizeSpeakerCount(document.getElementById("num-speakers").value));
      renderForm();
      configureCreateMode();
      return;
    }

    showStatus("Loading project configuration…");
    try {
      const project = await Api.getProject(projectId);
      loadProjectIntoState(project);
      const visuals = await Api.getProjectVisuals(projectId).catch(() => null);
      (visuals?.cast || []).forEach((member) => {
        if (state.speakers[member.speaker_index]) state.speakers[member.speaker_index].character_id = member.character_id;
      });
      renderForm();
      if (project.status === "draft") {
        configureEditMode();
      } else {
        configureLockedMode();
      }
    } catch (err) {
      console.error("Failed to load project:", err);
      pageMode = "load_error";
      clearStatus();
      document.title = "Project Unavailable — Daily Beyond English";
      document.getElementById("page-title").textContent = "Step 1 — Project Unavailable";
      document.getElementById("page-subtitle").textContent =
        "Return to the dashboard and try opening the project again.";
      showError("We couldn't load this project. Please return to the dashboard and try again.");
    }
  });
})();
