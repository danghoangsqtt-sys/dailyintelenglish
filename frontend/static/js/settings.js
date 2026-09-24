/** Settings page (Task 18.3): AI mode selector (local / cloud-first), cloud
 * provider form (base URL, model, write-only key), test connection, and the
 * effective-mode/reason display (PM review C3) -- lets the page show WHY the
 * effective mode differs from the selected one, when it does.
 *
 * The diagnostic "cloud" (no-fallback) mode is deliberately not exposed here
 * -- only "local" and "cloud_first" are user-facing choices.
 */
(() => {
  const localRadio = document.getElementById("ai-mode-local");
  const cloudFirstRadio = document.getElementById("ai-mode-cloud-first");
  const disabledNoteEl = document.getElementById("ai-mode-disabled-note");
  const effectiveStatusEl = document.getElementById("effective-mode-status");

  const baseUrlInput = document.getElementById("cloud-base-url");
  const modelInput = document.getElementById("cloud-model");
  const apiKeyInput = document.getElementById("cloud-api-key");
  const keyStatusEl = document.getElementById("cloud-key-status");

  const saveBtn = document.getElementById("save-cloud-settings-btn");
  const clearKeyBtn = document.getElementById("clear-cloud-key-btn");
  const testConnectionBtn = document.getElementById("test-connection-btn");
  const testConnectionResultEl = document.getElementById("test-connection-result");
  const saveStatusEl = document.getElementById("save-status");

  const EFFECTIVE_MODE_LABELS = { local: "Local", cloud: "Cloud", cloud_first: "Cloud-first" };

  function renderAiModeRadios(status) {
    if (!localRadio || !cloudFirstRadio) return;
    localRadio.checked = status.ai_mode === "local";
    cloudFirstRadio.checked = status.ai_mode === "cloud_first";
    cloudFirstRadio.disabled = !status.allow_cloud;
    cloudFirstRadio.closest(".settings-radio-option")?.classList.toggle("is-disabled", !status.allow_cloud);

    if (disabledNoteEl) {
      if (!status.allow_cloud) {
        disabledNoteEl.hidden = false;
        disabledNoteEl.textContent =
          "Cloud is disabled by DIE_AI_ALLOW_CLOUD=false — ask whoever manages this install's .env to enable it.";
        disabledNoteEl.classList.add("is-error");
      } else {
        disabledNoteEl.hidden = true;
        disabledNoteEl.classList.remove("is-error");
      }
    }
  }

  function renderEffectiveModeStatus(status) {
    if (!effectiveStatusEl) return;
    const selectedLabel = EFFECTIVE_MODE_LABELS[status.ai_mode] || status.ai_mode;
    const effectiveLabel = EFFECTIVE_MODE_LABELS[status.effective_mode] || status.effective_mode;
    if (status.effective_mode === status.ai_mode) {
      effectiveStatusEl.textContent = `Selected: ${selectedLabel} — running as ${effectiveLabel}.`;
    } else {
      effectiveStatusEl.textContent =
        `Selected: ${selectedLabel} — running as ${effectiveLabel} (${status.effective_reason}).`;
    }
  }

  function renderCloudForm(status) {
    if (baseUrlInput && document.activeElement !== baseUrlInput) baseUrlInput.value = status.cloud_base_url || "";
    if (modelInput && document.activeElement !== modelInput) modelInput.value = status.cloud_model || "";
    if (keyStatusEl) {
      const sourceLabel = { database: "saved in Settings", env: "from environment", none: "not configured" }[
        status.cloud_source
      ] || status.cloud_source;
      keyStatusEl.textContent = status.cloud_configured
        ? `Key ending in ${status.cloud_last4} (${sourceLabel}).`
        : `No key configured (${sourceLabel}).`;
      keyStatusEl.classList.remove("is-error", "is-success");
    }
  }

  async function loadStatus() {
    try {
      const status = await Api.getSettings();
      renderAiModeRadios(status);
      renderEffectiveModeStatus(status);
      renderCloudForm(status);
      return status;
    } catch (error) {
      if (effectiveStatusEl) effectiveStatusEl.textContent = error.message || "Could not load current status.";
      return null;
    }
  }

  async function handleModeChange(newMode) {
    try {
      await Api.updateAiMode(newMode);
      await loadStatus();
    } catch (error) {
      if (disabledNoteEl) {
        disabledNoteEl.hidden = false;
        disabledNoteEl.textContent = error.message || "Could not save the AI mode.";
        disabledNoteEl.classList.add("is-error");
      }
      await loadStatus(); // revert the radio to the actually-saved value
    }
  }

  async function handleSave() {
    if (!saveStatusEl) return;
    saveStatusEl.classList.remove("is-error", "is-success");
    saveStatusEl.textContent = "Saving…";
    try {
      await Api.updateCloudSettings(baseUrlInput.value, modelInput.value, apiKeyInput.value);
      apiKeyInput.value = "";
      saveStatusEl.textContent = "Saved.";
      saveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      saveStatusEl.textContent = error.message || "Could not save.";
      saveStatusEl.classList.add("is-error");
    }
  }

  async function handleClearKey() {
    if (!saveStatusEl) return;
    try {
      await Api.clearCloudApiKey();
      apiKeyInput.value = "";
      saveStatusEl.textContent = "Key cleared.";
      saveStatusEl.classList.remove("is-error");
      saveStatusEl.classList.add("is-success");
      await loadStatus();
    } catch (error) {
      saveStatusEl.textContent = error.message || "Could not clear the key.";
      saveStatusEl.classList.remove("is-success");
      saveStatusEl.classList.add("is-error");
    }
  }

  async function handleTestConnection() {
    if (!testConnectionResultEl) return;
    testConnectionResultEl.classList.remove("is-error", "is-success");
    testConnectionResultEl.textContent = "Testing…";
    try {
      const result = await Api.testCloudConnection(baseUrlInput.value, modelInput.value, apiKeyInput.value);
      if (result.ok) {
        testConnectionResultEl.textContent = "OK";
        testConnectionResultEl.classList.add("is-success");
      } else {
        const statusPart = result.status != null ? ` (${result.status})` : "";
        testConnectionResultEl.textContent = `${result.error}${statusPart}`;
        testConnectionResultEl.classList.add("is-error");
      }
    } catch (error) {
      testConnectionResultEl.textContent = error.message || "Could not test the connection.";
      testConnectionResultEl.classList.add("is-error");
    }
  }

  localRadio?.addEventListener("change", () => {
    if (localRadio.checked) handleModeChange("local");
  });
  cloudFirstRadio?.addEventListener("change", () => {
    if (cloudFirstRadio.checked) handleModeChange("cloud_first");
  });
  saveBtn?.addEventListener("click", handleSave);
  clearKeyBtn?.addEventListener("click", handleClearKey);
  testConnectionBtn?.addEventListener("click", handleTestConnection);

  loadStatus();
})();
