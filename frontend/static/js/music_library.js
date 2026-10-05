/** Music Library page: generate (Task 22.2), upload, preview, list, and delete local background tracks. */
(() => {
  // Client-side pre-check only — the server enforces the real limit via
  // MAX_MUSIC_UPLOAD_BYTES (app/core/constants.py). Keep this value in sync with
  // MAX_MUSIC_UPLOAD_MB there; there's no shared-config channel between the two yet.
  const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
  const ALLOWED_EXTENSIONS = [".mp3", ".wav"];
  let uploadInFlight = false;
  let loadPromise = null;
  const deletesInFlight = new Set();
  const JOB_POLL_MS = 1500;
  let styleLabels = {};
  let activeJobId = null;

  function formatDuration(totalSeconds) {
    const seconds = Math.round(totalSeconds);
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  }

  function provenanceText(provenance) {
    const parts = [
      styleLabels[provenance.style] || provenance.style,
      formatDuration(provenance.duration_s),
      `seed ${provenance.seed}`,
      `${provenance.model} · ${provenance.licence}`,
    ];
    return provenance.brief ? `“${provenance.brief}” · ${parts.join(" · ")}` : parts.join(" · ");
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
      name.textContent = track.filename;
      const source = document.createElement("span");
      const isAi = track.source === "ai";
      source.className = `track-source${isAi ? " is-ai" : ""}`;
      source.textContent = isAi ? "AI generated" : "Uploaded";
      const size = document.createElement("span");
      size.className = "track-size";
      size.textContent = formatBytes(track.size_bytes);
      details.append(name, source, size);
      if (isAi && track.provenance) {
        const provenance = document.createElement("p");
        provenance.className = "track-provenance";
        provenance.textContent = provenanceText(track.provenance);
        provenance.title = track.provenance.caption;
        details.append(provenance);
      }

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
      preview.append(waveformCanvas, player);

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "btn btn-ghost delete-btn";
      deleteButton.dataset.action = "delete";
      deleteButton.textContent = "Delete";
      deleteButton.disabled = deletesInFlight.has(track.filename);

      card.append(details, preview, deleteButton);
      list.append(card);
      // Rendered into the DOM first so the canvas has a real clientWidth to size against.
      Waveform.render(waveformCanvas, player.src, player);
    });
  }

  async function loadTracks() {
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
      try {
        renderTracks(await Api.listMusic());
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

  function validateFile(file) {
    const lowerName = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
      return "Choose an MP3 or WAV music file.";
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
    button.textContent = isUploading ? "Uploading…" : "Choose Music File";
  }

  async function uploadFile(file) {
    if (!file || uploadInFlight) return;
    setMessage("none");
    const validationMessage = validateFile(file);
    if (validationMessage) {
      setMessage("error", validationMessage);
      return;
    }

    setUploadState(true);
    let uploadedTrack;
    try {
      uploadedTrack = await Api.uploadMusic(file);
    } catch (error) {
      console.error("Failed to upload music:", error);
      setMessage("error", "We couldn't upload that music file. Check the format and try again.");
      return;
    } finally {
      setUploadState(false);
      document.getElementById("music-file-input").value = "";
    }

    setMessage("success", `${uploadedTrack.filename} was added to your library.`);
    await loadTracks();
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

    input.addEventListener("change", () => uploadFile(input.files[0]));
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
    zone.addEventListener("drop", (event) => uploadFile(event.dataTransfer.files[0]));
  }

  function setupDelete() {
    document.getElementById("track-list").addEventListener("click", (event) => {
      const button = event.target.closest("[data-action='delete']");
      if (!button) return;
      const card = button.closest("[data-filename]");
      deleteTrack(card.dataset.filename, button);
    });
  }

  function setGenerateBusy(busy, text = "") {
    document.getElementById("generate-button").disabled = busy;
    document.getElementById("generate-cancel").hidden = !busy;
    document.getElementById("generate-progress").textContent = text;
    ["music-style", "music-brief", "music-minutes", "music-seconds"].forEach((id) => {
      document.getElementById(id).disabled = busy;
    });
  }

  function jobText(job) {
    if (job.status === "pending") return "Queued — waiting for the GPU…";
    if (job.cancel_requested) return "Cancelling…";
    return `${job.stage || "Starting"}… ${job.progress || 0}%`;
  }

  async function pollJob(jobId) {
    let job;
    try {
      job = await Api.getMusicJob(jobId);
    } catch (error) {
      console.error("Failed to read music job:", error);
      setTimeout(() => pollJob(jobId), JOB_POLL_MS * 2);
      return;
    }
    if (job.status === "pending" || job.status === "running") {
      document.getElementById("generate-progress").textContent = jobText(job);
      setTimeout(() => pollJob(jobId), JOB_POLL_MS);
      return;
    }
    activeJobId = null;
    if (job.status === "complete") {
      const result = JSON.parse(job.result_json || "{}");
      setGenerateBusy(false, `Done: ${result.filename}`);
      setMessage("success", `${result.filename} was generated and added to your library.`);
      await loadTracks();
    } else if (job.status === "cancelled") {
      setGenerateBusy(false, "Cancelled.");
    } else {
      setGenerateBusy(false, "Failed — see the message below.");
      setMessage("error", `Music generation failed: ${job.error || "unknown error"}`);
    }
  }

  async function generate(event) {
    event.preventDefault();
    if (activeJobId) return;
    setMessage("none");
    const minutes = Number(document.getElementById("music-minutes").value || 0);
    const seconds = Number(document.getElementById("music-seconds").value || 0);
    const duration = Math.round(minutes * 60 + seconds);
    const form = document.getElementById("generate-form");
    const { minDuration, maxDuration } = form.dataset;
    if (!Number.isFinite(duration) || duration < Number(minDuration) || duration > Number(maxDuration)) {
      setMessage("error", `Choose a length between ${formatDuration(minDuration)} and ${formatDuration(maxDuration)}.`);
      return;
    }
    setGenerateBusy(true, "Queuing…");
    try {
      const job = await Api.generateMusic({
        style: document.getElementById("music-style").value,
        brief: document.getElementById("music-brief").value,
        duration_s: duration,
      });
      activeJobId = job.id;
      pollJob(job.id);
    } catch (error) {
      console.error("Failed to queue music generation:", error);
      setGenerateBusy(false);
      setMessage("error", `We couldn't start music generation: ${error.message}`);
    }
  }

  async function cancelGeneration() {
    if (!activeJobId) return;
    document.getElementById("generate-cancel").disabled = true;
    try {
      await Api.cancelMusicJob(activeJobId);
    } catch (error) {
      console.error("Failed to cancel music job:", error);
    } finally {
      document.getElementById("generate-cancel").disabled = false;
    }
  }

  async function setupGenerate() {
    const form = document.getElementById("generate-form");
    const unavailable = document.getElementById("generate-unavailable");
    form.addEventListener("submit", generate);
    document.getElementById("generate-cancel").addEventListener("click", cancelGeneration);
    let options;
    try {
      options = await Api.getMusicOptions();
    } catch (error) {
      console.error("Failed to load music options:", error);
      options = { styles: [], available: false, unavailable_reason: "Music generation options could not be loaded." };
    }
    const select = document.getElementById("music-style");
    select.replaceChildren(...options.styles.map((style) => new Option(style.label, style.id)));
    styleLabels = Object.fromEntries(options.styles.map((style) => [style.id, style.label]));
    form.dataset.minDuration = options.min_duration_s;
    form.dataset.maxDuration = options.max_duration_s;
    if (options.max_brief_chars) document.getElementById("music-brief").maxLength = options.max_brief_chars;
    if (!options.available) {
      unavailable.textContent = `AI music is unavailable: ${options.unavailable_reason}`;
      unavailable.hidden = false;
      setGenerateBusy(true);
      document.getElementById("generate-cancel").hidden = true;
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    setupUpload();
    setupDelete();
    await setupGenerate(); // style labels first, so AI provenance lines read "Lofi / chill"
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    loadTracks();
  });
})();
