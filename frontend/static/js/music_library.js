/** Music Library page: upload, preview, list, and delete local background tracks. */
(() => {
  // Client-side pre-check only — the server enforces the real limit via
  // MAX_MUSIC_UPLOAD_BYTES (app/core/constants.py). Keep this value in sync with
  // MAX_MUSIC_UPLOAD_MB there; there's no shared-config channel between the two yet.
  const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
  const ALLOWED_EXTENSIONS = [".mp3", ".wav"];
  let uploadInFlight = false;
  let loadPromise = null;
  const deletesInFlight = new Set();

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
      const size = document.createElement("span");
      size.className = "track-size";
      size.textContent = formatBytes(track.size_bytes);
      details.append(name, size);

      const player = document.createElement("audio");
      player.controls = true;
      player.preload = "metadata";
      player.src = track.content_url || Api.musicContentUrl(track.filename);
      player.setAttribute("aria-label", `Preview ${track.filename}`);

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "btn btn-ghost delete-btn";
      deleteButton.dataset.action = "delete";
      deleteButton.textContent = "Delete";
      deleteButton.disabled = deletesInFlight.has(track.filename);

      card.append(details, player, deleteButton);
      list.append(card);
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

  document.addEventListener("DOMContentLoaded", () => {
    setupUpload();
    setupDelete();
    document.getElementById("theme-toggle").addEventListener("click", Theme.toggle);
    loadTracks();
  });
})();
