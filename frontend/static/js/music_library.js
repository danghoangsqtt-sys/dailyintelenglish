/** Music Library page: upload (many files at once, Task 27.3a), preview, list, edit details (Task 22.7), and delete background tracks. */
(() => {
  // Client-side pre-check only — the server enforces the real limit via
  // MAX_MUSIC_UPLOAD_BYTES (app/core/constants.py). Keep this value in sync with
  // MAX_MUSIC_UPLOAD_MB there; there's no shared-config channel between the two yet.
  const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
  const ALLOWED_EXTENSIONS = [".mp3", ".wav", ".ogg", ".m4a"];
  let uploadInFlight = false;
  let loadPromise = null;
  const deletesInFlight = new Set();
  let options = { moods: [], sources: [], licences: [], paces: [] };
  let analysing = false;
  const DETAIL_FIELDS = ["title", "artist", "mood", "pace", "tags", "source", "licence", "attribution", "source_url"];

  function formatDuration(seconds) {
    if (seconds == null) return "length unknown";
    const total = Math.round(seconds);
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
  }

  function badge(text, className = "") {
    const element = document.createElement("span");
    element.className = `track-badge ${className}`.trim();
    element.textContent = text;
    return element;
  }

  function selectField(name, label, choices, value, emptyLabel) {
    const wrap = document.createElement("label");
    wrap.className = "detail-field";
    wrap.textContent = label;
    const select = document.createElement("select");
    select.name = name;
    select.append(new Option(emptyLabel, ""));
    choices.forEach((choice) => select.append(new Option(choice.label, choice.id)));
    select.value = value || "";
    wrap.append(select);
    return wrap;
  }

  function textField(name, label, value, placeholder, wide = false) {
    const wrap = document.createElement("label");
    wrap.className = `detail-field${wide ? " is-wide" : ""}`;
    wrap.textContent = label;
    const input = document.createElement("input");
    input.type = name === "source_url" ? "url" : "text";
    input.name = name;
    input.value = value || "";
    input.placeholder = placeholder;
    wrap.append(input);
    return wrap;
  }

  function buildDetailsForm(track) {
    const form = document.createElement("form");
    form.className = "details-form";
    form.hidden = true;
    form.noValidate = true;
    form.append(
      textField("title", "Title", track.title, "Track title"),
      textField("artist", "Artist", track.artist, "Composer or artist"),
      selectField("mood", "Mood", options.moods, track.mood,
        track.mood_is_auto ? `Auto (${track.mood_label})` : "Choose a mood"),
      selectField("pace", "Pace", options.paces || [], track.pace_is_auto ? "" : track.pace,
        track.pace_is_auto ? `Auto (${track.pace_label})` : "Auto"),
      textField("tags", "Tags", track.tags, "e.g. cafe, morning, study"),
      selectField("source", "Downloaded from", options.sources, track.source, "Choose a source"),
      selectField("licence", "Licence", options.licences.map((licence) => ({
        id: licence.id,
        label: licence.attribution_required ? `${licence.label} — credit required` : licence.label,
      })), track.licence, "Choose a licence"),
      textField("attribution", "Credit text (for the YouTube description)", track.attribution,
        "e.g. Title by Artist (site), licence", true),
      textField("source_url", "Download page link", track.source_url, "https://…", true),
    );
    const actions = document.createElement("div");
    actions.className = "details-actions";
    const save = document.createElement("button");
    save.type = "submit";
    save.className = "btn btn-primary btn-sm";
    save.textContent = "Save details";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "btn btn-ghost btn-sm";
    cancel.dataset.action = "cancel-details";
    cancel.textContent = "Cancel";
    actions.append(save, cancel);
    form.append(actions);
    return form;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function setMessage(kind, text = "") {
    const status = document.getElementById("status-message");
    const error = document.getElementById("error-message");
    status.hidden = kind !== "success";
    error.hidden = kind !== "error";
    status.textContent = kind === "success" ? text : "";
    error.textContent = kind === "error" ? text : "";
  }

  function buildBadges(track) {
    const badges = document.createElement("div");
    badges.className = "track-badges";
    badges.append(badge(formatDuration(track.duration_s), "is-length"));
    if (track.mood_label) {
      badges.append(badge(track.mood_is_auto ? `${track.mood_label} · auto` : track.mood_label, "is-mood"));
    } else {
      badges.append(badge(track.needs_analysis ? "Analysing…" : "No mood yet", "is-missing"));
    }
    // Task 22.9: the measured pace (calm / medium / lively) and the estimated tempo.
    if (track.pace_label) {
      badges.append(badge(track.pace_is_auto ? `${track.pace_label} · auto` : track.pace_label, "is-pace"));
    }
    if (track.bpm) badges.append(badge(`~${Math.round(track.bpm)} BPM`));
    if (track.licence_label) badges.append(badge(track.licence_label));
    if (track.needs_attribution) badges.append(badge("⚠ Credit needed", "is-warning"));
    return badges;
  }

  /** After analysis: refresh each card's badges (and its closed details form) in place, so audio
   * players keep playing -- re-rendering the list would stop and rewind any track being heard. */
  function updateTracksInPlace(tracks) {
    const list = document.getElementById("track-list");
    const cards = new Map([...list.querySelectorAll("[data-filename]")].map((card) => [card.dataset.filename, card]));
    if (tracks.length !== cards.size || tracks.some((track) => !cards.has(track.filename))) {
      renderTracks(tracks); // the library itself changed meanwhile
      return;
    }
    tracks.forEach((track) => {
      const card = cards.get(track.filename);
      card.querySelector(".track-badges").replaceWith(buildBadges(track));
      const form = card.querySelector(".details-form");
      if (form && form.hidden) form.replaceWith(buildDetailsForm(track));
    });
  }

  function renderTracks(tracks) {
    const list = document.getElementById("track-list");
    const empty = document.getElementById("empty-state");
    const count = document.getElementById("track-count");
    list.replaceChildren();
    count.textContent = `${tracks.length} ${tracks.length === 1 ? "track" : "tracks"}`;
    empty.hidden = tracks.length !== 0;

    tracks.forEach((track) => {
      const card = document.createElement("article");
      card.className = "track-card card";
      card.dataset.filename = track.filename;

      const details = document.createElement("div");
      const name = document.createElement("h3");
      name.className = "track-name";
      name.textContent = track.artist ? `${track.title} — ${track.artist}` : track.title;
      const file = document.createElement("span");
      file.className = "track-size";
      file.textContent = `${track.filename} · ${formatBytes(track.size_bytes)}`;
      details.append(name, file, buildBadges(track));

      const preview = document.createElement("div");
      preview.className = "track-preview";
      const waveformCanvas = document.createElement("canvas");
      waveformCanvas.className = "track-waveform";
      waveformCanvas.setAttribute("role", "img");
      waveformCanvas.setAttribute("aria-label", `Waveform for ${track.filename}`);

      const player = document.createElement("audio");
      player.controls = true;
      player.preload = "metadata";
      player.src = track.content_url || Api.musicContentUrl(track.filename);
      player.setAttribute("aria-label", `Preview ${track.filename}`);
      const playRow = document.createElement("div");
      playRow.className = "track-playrow";
      const playButton = document.createElement("button");
      playButton.type = "button";
      playButton.className = "track-play";
      const glyph = document.createElement("span");
      glyph.setAttribute("aria-hidden", "true");
      playButton.append(glyph);
      const syncPlayButton = () => {
        const playing = !player.paused;
        playButton.setAttribute("aria-pressed", String(playing));
        playButton.setAttribute("aria-label", `${playing ? "Pause" : "Play"} ${track.title}`);
        glyph.textContent = playing ? "❚❚" : "▶";
      };
      playButton.addEventListener("click", () => {
        if (player.paused) player.play().catch((error) => console.error("Could not play the track:", error));
        else player.pause();
      });
      player.addEventListener("play", () => {
        // One track at a time: starting this one pauses every other.
        document.querySelectorAll("#track-list audio").forEach((other) => {
          if (other !== player && !other.paused) other.pause();
        });
        syncPlayButton();
      });
      ["pause", "ended"].forEach((name) => player.addEventListener(name, syncPlayButton));
      syncPlayButton();
      playRow.append(playButton, waveformCanvas);
      preview.append(playRow, player);

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "btn btn-ghost delete-btn";
      deleteButton.dataset.action = "delete";
      deleteButton.textContent = "Delete";
      deleteButton.disabled = deletesInFlight.has(track.filename);

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "btn btn-ghost edit-btn";
      editButton.dataset.action = "edit-details";
      editButton.textContent = "Edit details";
      const buttons = document.createElement("div");
      buttons.className = "track-buttons";
      buttons.append(editButton, deleteButton);

      card.append(details, preview, buttons, buildDetailsForm(track));
      list.append(card);
      // Rendered into the DOM first so the canvas has a real clientWidth to size against.
      Waveform.render(waveformCanvas, player.src, player);
    });
  }

  async function loadTracks() {
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
      try {
        const tracks = await Api.listMusic();
        renderTracks(tracks);
        if (tracks.some((track) => track.needs_analysis)) analyseTracks();
      } catch (error) {
        console.error("Failed to load music library:", error);
        document.getElementById("track-count").textContent = "Unavailable";
        setMessage("error", "We couldn't load the music library. Please try again.");
      } finally {
        loadPromise = null;
      }
    })();
    return loadPromise;
  }

  // Task 22.9: classify new tracks (pace, tempo, mood suggestion) after the list is on screen.
  async function analyseTracks() {
    if (analysing) return;
    analysing = true;
    const note = document.getElementById("analysis-note");
    note.hidden = false;
    try {
      const result = await Api.analyseMusic();
      updateTracksInPlace(result.tracks);
    } catch (error) {
      console.error("Failed to analyse music:", error);
    } finally {
      analysing = false;
      note.hidden = true;
    }
  }

  function validateFile(file) {
    const lowerName = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
      return "Choose an MP3, WAV, OGG or M4A music file.";
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      return "Choose a music file that is 50 MB or smaller.";
    }
    if (file.size === 0) return "Choose a non-empty music file.";
    return null;
  }

  function setUploadState(isUploading) {
    uploadInFlight = isUploading;
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("music-file-input");
    const button = document.getElementById("upload-button");
    zone.classList.toggle("is-uploading", isUploading);
    input.disabled = isUploading;
    button.textContent = isUploading ? "Uploading…" : "Choose Music Files";
  }

  // Task 27.3a: the zone takes many files; they are uploaded one after another (the API takes one per request).
  const QUEUE_LABELS = { waiting: "Waiting", uploading: "Uploading…", added: "Added", skipped: "Skipped", error: "Not added" };

  function renderQueue(items) {
    const list = document.getElementById("upload-queue");
    list.hidden = items.length < 2; // one file needs no queue: its message says it all
    list.replaceChildren(...items.map((item) => {
      const row = document.createElement("li");
      row.dataset.state = item.state;
      const name = document.createElement("span");
      name.className = "queue-name";
      name.textContent = item.file.name;
      const state = document.createElement("span");
      state.className = "queue-state";
      state.textContent = QUEUE_LABELS[item.state];
      row.append(name, state);
      if (item.note) {
        const note = document.createElement("span");
        note.className = "queue-note";
        note.textContent = item.note;
        row.append(note);
      }
      return row;
    }));
  }

  function plural(count, word) {
    return `${count} ${word}${count === 1 ? "" : "s"}`;
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length || uploadInFlight) return;
    setMessage("none");
    setUploadState(true);
    const items = files.map((file) => ({ file, state: "waiting", note: "", track: null }));
    renderQueue(items);
    for (const item of items) {
      const problem = validateFile(item.file);
      if (problem) {
        item.state = "skipped";
        item.note = problem;
        renderQueue(items);
        continue;
      }
      item.state = "uploading";
      renderQueue(items);
      try {
        item.track = await Api.uploadMusic(item.file);
        item.state = "added";
        if (item.track.filename !== item.file.name) item.note = `saved as ${item.track.filename}`;
      } catch (error) {
        console.error("Failed to upload music:", error);
        item.state = "error";
        item.note = "The server did not accept this file. Check the format.";
      }
      renderQueue(items);
    }
    setUploadState(false);
    document.getElementById("music-file-input").value = "";

    const added = items.filter((item) => item.state === "added");
    const notAdded = items.length - added.length;
    if (items.length === 1) { // the single-file messages are unchanged
      const [only] = items;
      if (only.state === "added") setMessage("success", `${only.track.filename} was added to your library.`);
      else if (only.state === "skipped") setMessage("error", only.note);
      else setMessage("error", "We couldn't upload that music file. Check the format and try again.");
    } else if (!added.length) {
      setMessage("error", `No tracks were added: ${notAdded} skipped.`);
    } else if (notAdded) {
      setMessage("success", `${plural(added.length, "track")} added, ${notAdded} skipped.`);
    } else {
      setMessage("success", `${plural(added.length, "track")} added to your library.`);
    }
    if (added.length) await loadTracks();
  }

  async function deleteTrack(filename, button) {
    if (deletesInFlight.has(filename)) return;
    if (!confirm(`Delete "${filename}" from your music library?`)) return;

    deletesInFlight.add(filename);
    button.disabled = true;
    button.textContent = "Deleting…";
    setMessage("none");
    try {
      await Api.deleteMusic(filename);
      setMessage("success", `${filename} was deleted.`);
      await loadTracks();
    } catch (error) {
      console.error("Failed to delete music:", error);
      setMessage("error", "We couldn't delete that track. Please try again.");
    } finally {
      deletesInFlight.delete(filename);
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = "Delete";
      }
    }
  }

  function setupUpload() {
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("music-file-input");

    input.addEventListener("change", () => uploadFiles(input.files));
    zone.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && !uploadInFlight) {
        event.preventDefault();
        input.click();
      }
    });
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        if (!uploadInFlight) zone.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.remove("is-dragging");
      });
    });
    zone.addEventListener("drop", (event) => uploadFiles(event.dataTransfer.files));
  }

  function setupDelete() {
    document.getElementById("track-list").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const card = button.closest("[data-filename]");
      const form = card.querySelector(".details-form");
      if (button.dataset.action === "delete") deleteTrack(card.dataset.filename, button);
      if (button.dataset.action === "edit-details") form.hidden = !form.hidden;
      if (button.dataset.action === "cancel-details") form.hidden = true;
    });
    document.getElementById("track-list").addEventListener("submit", async (event) => {
      const form = event.target.closest(".details-form");
      if (!form) return;
      event.preventDefault();
      const filename = form.closest("[data-filename]").dataset.filename;
      const body = Object.fromEntries(DETAIL_FIELDS.map((field) => [field, form.elements[field].value]));
      const save = form.querySelector("[type='submit']");
      save.disabled = true;
      setMessage("none");
      try {
        await Api.updateMusic(filename, body);
        setMessage("success", `Details saved for ${filename}.`);
        await loadTracks();
      } catch (error) {
        console.error("Failed to save track details:", error);
        setMessage("error", `We could not save those details: ${error.message}`);
        save.disabled = false;
      }
    });
  }

  async function loadOptions() {
    try {
      options = await Api.getMusicOptions();
    } catch (error) {
      console.error("Failed to load music options:", error);
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    setupUpload();
    setupDelete();
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    await loadOptions(); // the details form needs the mood / source / licence choices
    loadTracks();
  });
})();
