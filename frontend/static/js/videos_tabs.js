/** Phase 93 (Task 93.6): the Videos page's two views -- the list and the production board by step. */
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const tabs = [["view-list", "videos-list"], ["view-board", "videos-board"]];
    const show = (key) => tabs.forEach(([tab, panel]) => {
      const on = tab === key;
      document.getElementById(tab).setAttribute("aria-selected", String(on));
      document.getElementById(panel).hidden = !on;
    });
    tabs.forEach(([tab]) => document.getElementById(tab).addEventListener("click", () => show(tab)));
    if (location.hash === "#board") show("view-board");
    window.addEventListener("hashchange", () => show(location.hash === "#board" ? "view-board" : "view-list"));
    // the status chips mirror the existing filter buttons' active class as aria-pressed
    document.querySelectorAll(".filter-btn").forEach((button) => button.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    }));
  });
})();
