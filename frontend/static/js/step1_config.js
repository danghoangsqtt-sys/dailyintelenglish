/**
 * Step 1 — Script Config wizard. UI state + validation only; all persistence
 * goes through Api.createProject() (frontend/static/js/api.js), never fetch()
 * directly (CR-05).
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
    { value: "scottish", label: "Scottish", flag: "🏴" },
    { value: "indian", label: "Indian", flag: "🇮🇳" },
    { value: "singaporean", label: "Singaporean", flag: "🇸🇬" },
    { value: "new_zealand", label: "New Zealand", flag: "🇳🇿" },
    { value: "south_african", label: "South African", flag: "🇿🇦" },
  ];

  const GENDERS = ["male", "female", "neutral"];
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
    languageFeatures: Object.fromEntries(LANGUAGE_FEATURES.map((f) => [f.key, f.default])),
  };

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
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
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

  function setLoading(loading) {
    const btn = document.getElementById("submit-btn");
    btn.disabled = loading;
    btn.innerHTML = loading
      ? '<span class="spinner"></span> Creating…'
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
          name: "",
          gender: GENDERS[i % GENDERS.length],
          accent: state.accent,
        });
      }
    } else if (count < speakers.length) {
      speakers.length = count;
    }
  }

  function speakerCardHtml(speaker, index) {
    return `
      <div class="card speaker-card" data-index="${index}">
        <label class="field-label" for="speaker-name-${index}">Speaker ${index + 1} Name</label>
        <input type="text" id="speaker-name-${index}" data-field="name" data-index="${index}" value="${escapeHtml(speaker.name)}" placeholder="e.g. Alex" />

        <label class="field-label" for="speaker-gender-${index}">Gender</label>
        <select id="speaker-gender-${index}" data-field="gender" data-index="${index}">
          ${GENDERS.map((g) => `<option value="${g}" ${g === speaker.gender ? "selected" : ""}>${g}</option>`).join("")}
        </select>

        <label class="field-label" for="speaker-accent-${index}">Accent</label>
        <select id="speaker-accent-${index}" data-field="accent" data-index="${index}">
          ${ACCENTS.map(
            (a) => `<option value="${a.value}" ${a.value === speaker.accent ? "selected" : ""}>${a.flag} ${a.label}</option>`
          ).join("")}
        </select>
      </div>`;
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
            `<button type="button" class="chip" data-value="${item.value}" aria-pressed="${item.value === value}">${item.icon || item.flag} ${item.label}</button>`
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
      if (!speaker.name.trim()) errors.push(`Speaker ${index + 1} needs a name.`);
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
        tts_engine: "omnivoice",
        voice_description: "",
        speed: 1.0,
        pitch: 0.0,
        volume: 1.0,
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
      const project = await Api.createProject(buildPayload());
      window.location.href = `/step2?project_id=${encodeURIComponent(project.id)}&name=${encodeURIComponent(project.name)}`;
    } catch (err) {
      console.error("Failed to create project:", err);
      showError("We couldn't create the project. Please check your input and try again.");
      isSubmitting = false;
      setLoading(false);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);

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

    document.getElementById("config-form").addEventListener("submit", handleSubmit);
  });
})();
