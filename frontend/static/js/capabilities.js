/**
 * Phase 71 (ENH-053): show or hide the local AI picture features (class `needs-local-gpu`) for this computer.
 * The last answer is applied at once from sessionStorage, then refreshed from /api/system/capabilities.
 * On Settings it also runs the "AI pictures on this computer" switch.
 */
(() => {
  const KEY = "dbe.localImageAi";
  const apply = (shown) => { document.documentElement.dataset.localImageAi = shown ? "on" : "off"; };
  try {
    const last = sessionStorage.getItem(KEY);
    if (last) apply(last === "on");
  } catch { /* storage may be blocked */ }

  function remember(data) {
    apply(data.local_image_ai);
    try { sessionStorage.setItem(KEY, data.local_image_ai ? "on" : "off"); } catch { /* keep going */ }
    window.dispatchEvent(new CustomEvent("dbe:capabilities", { detail: data }));
  }

  async function call(method, body) {
    const response = await fetch("/api/system/capabilities", {
      method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined,
    });
    const envelope = await response.json();
    if (!response.ok || !envelope.success) throw new Error(envelope.error?.message || "The setting could not be read.");
    return envelope.data;
  }

  function settingsCard(data) {
    const status = document.getElementById("local-image-ai-status");
    if (!status) return;
    document.querySelectorAll("input[name=local-image-ai]").forEach((input) => { input.checked = input.value === data.choice; });
    const edition = data.edition === "lite" ? "Lite edition" : "Full edition";
    status.textContent = `${edition} · ${data.local_image_ai ? "Shown" : "Hidden"}: ${data.reason}.`;
  }

  window.addEventListener("dbe:capabilities", (event) => settingsCard(event.detail));
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("input[name=local-image-ai]").forEach((input) => input.addEventListener("change", async () => {
      if (!input.checked) return;
      try { remember(await call("PUT", { local_image_ai: input.value })); } catch (error) {
        const status = document.getElementById("local-image-ai-status");
        if (status) status.textContent = error.message;
      }
    }));
  });
  call("GET").then(remember).catch(() => { /* keep what is shown */ });
})();
