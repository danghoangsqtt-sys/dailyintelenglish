/** Phase 93 (Task 93.4): Step 1 opened from Create video or Home picks the chosen kind and topic for a new project
 *  (`?mode=shorts&template=grammar`, `?mode=vox`, `?topic=...`). An existing project (`project_id`) is left alone. */
(() => {
  const params = new URLSearchParams(location.search);
  if (params.get("project_id")) return;
  // Step 1 wires its cards after its own data loads, so the choice is retried until the page shows it as chosen.
  const chosen = (selector) => document.querySelector(selector)?.getAttribute("aria-checked") === "true";
  function choose(selector, tries = 40) {
    return new Promise((resolve) => {
      const attempt = (left) => {
        const node = document.querySelector(selector);
        if (node && !chosen(selector)) node.click();
        if (chosen(selector) || left <= 0) resolve(chosen(selector));
        else setTimeout(() => attempt(left - 1), 150);
      };
      attempt(tries);
    });
  }
  window.addEventListener("load", async () => {
    const mode = params.get("mode");
    const template = params.get("template");
    const topic = params.get("topic");
    if (mode) await choose(`.type-card[data-mode="${CSS.escape(mode)}"]`);
    if (template) await choose(`#shorts-templates [data-template="${CSS.escape(template)}"]`);
    const field = document.getElementById("topic");
    if (topic && field && !field.value) {
      field.value = topic;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
})();
