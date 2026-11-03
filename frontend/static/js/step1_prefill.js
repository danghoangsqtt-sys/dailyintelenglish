/** Phase 93 (Task 93.4): Step 1 opened from Create video or Home picks the chosen kind and topic for a new project
 *  (`?mode=shorts&template=grammar`, `?mode=vox`, `?topic=...`). An existing project (`project_id`) is left alone. */
(() => {
  const params = new URLSearchParams(location.search);
  if (params.get("project_id")) return;
  window.addEventListener("load", () => {
    const mode = params.get("mode");
    const template = params.get("template");
    const topic = params.get("topic");
    const click = (selector) => { const node = document.querySelector(selector); if (node) node.click(); };
    if (mode) click(`.type-card[data-mode="${CSS.escape(mode)}"]`);
    if (template) click(`#shorts-templates [data-template="${CSS.escape(template)}"]`);
    const field = document.getElementById("topic");
    if (topic && field && !field.value) {
      field.value = topic;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
})();
