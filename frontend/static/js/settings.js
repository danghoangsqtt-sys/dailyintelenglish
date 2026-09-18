/** Settings page: view/edit the Gemini API key. UI state only — no business logic. */
(() => {
  const statusEl = document.getElementById("current-status");
  const inputEl = document.getElementById("api-key-input");
  const toggleVisibilityBtn = document.getElementById("toggle-visibility-btn");
  const saveBtn = document.getElementById("save-btn");
  const clearBtn = document.getElementById("clear-btn");
  const messageEl = document.getElementById("message");

  const SOURCE_LABELS = {
    database: "Saved in Settings",
    env: "From .env file",
    none: "Not configured",
  };

  function showMessage(text, isError) {
    messageEl.textContent = text;
    messageEl.className = `message ${isError ? "message-error" : "message-success"}`;
    messageEl.hidden = false;
  }

  function renderStatus(status) {
    const label = SOURCE_LABELS[status.source] || status.source;
    statusEl.textContent = status.masked_key ? `${label}: ${status.masked_key}` : label;
  }

  async function loadStatus() {
    try {
      const status = await Api.getSettings();
      renderStatus(status);
    } catch (error) {
      statusEl.textContent = "Could not load current status.";
      showMessage(error.message || "Could not load current status.", true);
    }
  }

  toggleVisibilityBtn.addEventListener("click", () => {
    const showing = inputEl.type === "text";
    inputEl.type = showing ? "password" : "text";
    toggleVisibilityBtn.textContent = showing ? "👁️" : "🙈";
  });

  saveBtn.addEventListener("click", async () => {
    const value = inputEl.value.trim();
    if (!value) {
      showMessage("Please enter an API key before saving.", true);
      return;
    }
    saveBtn.disabled = true;
    try {
      const status = await Api.updateGeminiApiKey(value);
      renderStatus(status);
      inputEl.value = "";
      showMessage("API key saved — takes effect immediately.", false);
    } catch (error) {
      showMessage(error.message || "Could not save the API key.", true);
    } finally {
      saveBtn.disabled = false;
    }
  });

  clearBtn.addEventListener("click", async () => {
    clearBtn.disabled = true;
    try {
      const status = await Api.clearGeminiApiKey();
      renderStatus(status);
      showMessage("Stored key cleared.", false);
    } catch (error) {
      showMessage(error.message || "Could not clear the stored key.", true);
    } finally {
      clearBtn.disabled = false;
    }
  });

  loadStatus();
})();
