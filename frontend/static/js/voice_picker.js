/* Shared English voice picker. Owns display/edit/playback state; provider and persistence rules stay in services. */
window.VoicePicker = (() => {
  let sequence = 0;
  let catalogPromise = null;

  function catalog(refresh = false) {
    if (refresh || !catalogPromise) {
      catalogPromise = Api.listTtsVoices(refresh).catch((error) => {
        catalogPromise = null;
        throw error;
      });
    }
    return catalogPromise;
  }

  function mount(host, options) {
    const prefix = "voice-picker-" + (++sequence);
    host.classList.add("voice-picker");
    host.innerHTML = '<p class="voice-current"></p><div class="voice-filters"></div>' +
       '<label class="field-label voice-select-label">English voice<select class="voice-select"></select></label>' +
      '<p class="voice-count" aria-live="polite"></p>' +
      '<label class="field-label">Try the same sentence<textarea class="voice-sample" maxlength="500" rows="2"></textarea></label>' +
      '<div class="voice-parameters"></div><div class="voice-actions">' +
      '<button type="button" class="btn btn-ghost btn-sm voice-preview">Listen</button>' +
      '<button type="button" class="btn btn-primary btn-sm voice-save">Save voice</button>' +
      '<button type="button" class="btn btn-ghost btn-sm voice-refresh">Refresh voices</button>' +
      '<button type="button" class="btn btn-ghost btn-sm voice-reload" hidden>Reload saved settings</button></div>' +
      '<audio class="voice-audio" controls hidden></audio><p class="voice-status" role="status"></p>';
    const $ = (selector) => host.querySelector(selector);
    const select = $(".voice-select"), sample = $(".voice-sample"), audio = $(".voice-audio");
    select.id = prefix;
    $(".voice-select-label").htmlFor = prefix;
    sample.value = "A clear explanation begins with a simple example. Let us explore this idea together.";
    const state = {
      voiceId: options.voiceId || "", revision: options.revision || null,
      parameters: {speed: 1, pitch: 0, volume: 1, ...(options.parameters || {})},
      saved: "", voices: [], destroyed: false, disabled: false,
      saving: false, listening: false, loading: false, token: 0, abort: null,
    };
    const controls = {};
    if (options.editParameters) {
      [["speed", "Speed", 0.75, 1.5, 0.05], ["pitch", "Pitch", -1, 1, 0.1], ["volume", "Volume", 0, 2, 0.1]].forEach(
        ([key, label, min, max, step]) => {
          const wrapper = document.createElement("label");
          wrapper.className = "field-label";
          wrapper.textContent = label;
          const input = document.createElement("input");
          Object.assign(input, {type: "number", min, max, step, value: state.parameters[key]});
          input.setAttribute("aria-label", "Default voice " + label.toLowerCase());
          input.addEventListener("input", () => {
            state.parameters[key] = Number(input.value);
            stop();
            sync();
          });
          wrapper.append(input);
          $(".voice-parameters").append(wrapper);
          controls[key] = input;
        });
    }

    function filter(label, className) {
      const wrapper = document.createElement("label");
      wrapper.textContent = label;
      wrapper.className = "field-label";
      const input = document.createElement("select");
      input.className = className;
      input.setAttribute("aria-label", label);
      wrapper.append(input);
      $(".voice-filters").append(wrapper);
      return input;
    }
    const locale = filter("Voice locale", "voice-locale");
    const gender = filter("Voice gender", "voice-gender");
    ["", "male", "female", "neutral"].forEach(v => gender.add(new Option(v || "All genders", v)));
    const search = document.createElement("input");
    search.type = "search";
    search.className = "voice-search";
    search.placeholder = "Search name or voice ID";
    search.setAttribute("aria-label", "Search voices");
    $(".voice-filters").append(search);

    function currentValue() {
      return JSON.stringify({voiceId: state.voiceId, parameters: options.editParameters ? state.parameters : null});
    }
    state.saved = currentValue();

    function dirty() { return currentValue() !== state.saved; }
    function message(text, error = false) {
      $(".voice-status").textContent = text;
      $(".voice-status").classList.toggle("is-error", error);
    }
    function stop() {
      state.token += 1;
      state.abort?.abort();
      state.abort = null;
      state.listening = false;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      audio.hidden = true;
    }
    function sync(notify = true) {
      const busy = state.disabled || state.saving || state.loading;
      host.querySelectorAll("button,input,select,textarea").forEach(el => { el.disabled = busy; });
      const known = state.voices.some(v => v.voice_id === state.voiceId);
      const validParameters = Object.values(controls).every(input => input.checkValidity() && input.value !== "");
      $(".voice-preview").disabled = busy || state.listening || !known || !validParameters || !sample.value.trim();
      $(".voice-save").disabled = busy || !dirty() || !known || !validParameters;
      $(".voice-preview").textContent = state.listening ? "Preparing preview…" : "Listen";
      $(".voice-save").textContent = state.saving ? "Saving…" : "Save voice";
      $(".voice-reload").hidden = !options.onReload || !dirty();
      if (notify) options.onDirtyChange?.(dirty() || state.saving);
    }
    function displaySaved() {
      const savedId = JSON.parse(state.saved).voiceId;
      const voice = state.voices.find(v => v.voice_id === savedId);
      $(".voice-current").textContent = "Saved voice: " +
        (voice ? voice.name + " · " + voice.voice_id : savedId || "Project accent/gender default");
    }
    function renderVoices() {
      const query = search.value.trim().toLowerCase();
      const visible = state.voices.filter(v =>
        (!locale.value || v.locale === locale.value) && (!gender.value || v.gender === gender.value) &&
        (!query || (v.name + " " + v.voice_id).toLowerCase().includes(query)));
      select.replaceChildren(new Option("Select an English voice", ""));
      visible.forEach(v => select.add(new Option(v.name + " · " + v.voice_id, v.voice_id)));
      if (state.voiceId && !visible.some(v => v.voice_id === state.voiceId)) {
        select.add(new Option(state.voiceId + " (current selection)", state.voiceId));
      }
      select.value = state.voiceId;
      $(".voice-count").textContent = `${visible.length} of ${state.voices.length} English voices`;
      displaySaved();
      sync();
    }
    async function load(refresh = false) {
      state.loading = true;
      message("Loading English voices…");
      sync();
      try {
        const result = await catalog(refresh);
        if (state.destroyed) return;
        state.voices = result.voices || [];
        const selectedLocale = locale.value;
        locale.replaceChildren(new Option("All English locales", ""));
        [...new Set(state.voices.map(v => v.locale))].sort().forEach(v => locale.add(new Option(v, v)));
        locale.value = selectedLocale;
        if (!locale.value) locale.value = "";
        renderVoices();
        message(result.stale ? "Offline: showing the last saved voice list. Refresh to check availability." :
          state.voiceId && !state.voices.some(v => v.voice_id === state.voiceId) ?
          "The saved voice is unavailable in this list. Refresh or select another voice." : "");
      } catch (error) {
        if (!state.destroyed) message(error.message || "Voice list unavailable. Press Refresh voices to retry.", true);
      } finally {
        if (!state.destroyed) { state.loading = false; sync(); }
      }
    }
    select.addEventListener("change", () => {
      state.voiceId = select.value;
      stop(); message(dirty() ? "Voice changed locally. Press Save voice to apply." : ""); sync();
    });
    [locale, gender].forEach(el => el.addEventListener("change", renderVoices));
    search.addEventListener("input", renderVoices);
    sample.addEventListener("input", () => { stop(); sync(); });
    $(".voice-refresh").addEventListener("click", () => load(true));
    $(".voice-preview").addEventListener("click", async () => {
      stop();
      const token = state.token;
      state.abort = new AbortController();
      state.listening = true;
      message("Preparing the selected voice…"); sync();
      try {
        const result = await Api.previewTtsVoice({
          voice_id: state.voiceId, text: sample.value,
          ...(options.getParameters?.() || state.parameters),
        }, {signal: state.abort.signal});
        if (state.destroyed || token !== state.token) return;
        audio.src = result.audio_url;
        audio.hidden = false;
        message("Preview: " + result.voice.voice_id);
        try { await audio.play(); } catch { /* controls remain available if browser blocks autoplay */ }
      } catch (error) {
        if (!state.destroyed && token === state.token && error.name !== "AbortError") {
          message(error.message || "The selected voice could not be previewed.", true);
        }
      } finally {
        if (!state.destroyed && token === state.token) { state.listening = false; sync(); }
      }
    });
    $(".voice-save").addEventListener("click", async () => {
      if (state.saving || !dirty()) return;
      stop();
      state.saving = true;
      message("Saving voice…"); sync();
      try {
        const value = await options.onSave({
          voice_id: state.voiceId, expected_voice_revision: state.revision, ...state.parameters,
        });
        if (state.destroyed) return;
        state.revision = value.revision;
        state.saved = currentValue();
        displaySaved();
        message(options.savedMessage || "Voice saved.");
        $(".voice-reload").hidden = true;
      } catch (error) {
        if (state.destroyed) return;
        message(error.status === 409 ?
          "Settings changed elsewhere. Your selection is kept; reload saved settings before retrying." :
          error.message || "Voice could not be saved. Your selection is kept.", true);
        $(".voice-reload").hidden = !options.onReload;
      } finally {
        if (!state.destroyed) { state.saving = false; sync(); }
      }
    });
    $(".voice-reload").addEventListener("click", async () => {
      if (!options.onReload || state.saving) return;
      state.saving = true; sync();
      try {
        const value = await options.onReload();
        if (state.destroyed) return;
        state.voiceId = value.voiceId || "";
        state.revision = value.revision;
        state.parameters = {...state.parameters, ...(value.parameters || {})};
        Object.entries(controls).forEach(([key, input]) => { input.value = state.parameters[key]; });
        state.saved = currentValue();
        renderVoices(); message("Saved settings reloaded."); $(".voice-reload").hidden = true;
      } catch (error) {
        if (!state.destroyed) message(error.message || "Settings could not be reloaded.", true);
      } finally {
        if (!state.destroyed) { state.saving = false; sync(); }
      }
    });
    const beforeUnload = (event) => {
      if (dirty() || state.saving) { event.preventDefault(); event.returnValue = ""; }
    };
    window.addEventListener("beforeunload", beforeUnload);
    load();
    return {
      hasUnsaved: () => dirty() || state.saving,
      isSaving: () => state.saving,
      setDisabled: (value) => { state.disabled = value; if (value) stop(); sync(false); },
      setRevision: (revision) => { state.revision = revision; },
      setSaved: (value) => {
        stop(); state.voiceId = value.voiceId || ""; state.revision = value.revision;
        state.parameters = {...state.parameters, ...(value.parameters || {})};
        Object.entries(controls).forEach(([key, input]) => { input.value = state.parameters[key]; });
        state.saved = currentValue(); renderVoices(); message(value.message || "Saved voice applied.");
      },
      destroy: () => {
        state.destroyed = true; stop();
        window.removeEventListener("beforeunload", beforeUnload); host.replaceChildren();
      },
    };
  }
  return {mount};
})();
