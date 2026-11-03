/** Phase 93 (Tasks 93.4/93.5/93.7, D138): an area's pages as tabs at the top of the page -- Channel (plan, automation),
 *  Library (characters, scenes and pictures, music, voices and brand) and Create video (templates, many Shorts). Each tab
 *  is its own page, so every feature keeps its address, IDs and script. */
(() => {
  const AREAS = [
    [["/channel", "Publishing plan"], ["/automation", "Automation"]],
    [["/characters", "Characters"], ["/activities", "Scenes and pictures"], ["/music", "Music"], ["/library", "Voices and brand"]],
    [["/create", "Templates"], ["/shorts-batch", "Many Shorts at once"]],
  ];
  const here = location.pathname.replace(/\/$/, "") || "/";
  const area = AREAS.find((tabs) => tabs.some(([path]) => path === here));
  const main = document.querySelector("main");
  if (!area || !main) return;
  const nav = document.createElement("nav");
  nav.className = "e-tabs area-tabs";
  nav.setAttribute("aria-label", "Pages of this area");
  area.forEach(([path, label]) => {
    const link = document.createElement("a");
    link.href = path;
    link.textContent = label;
    if (path === here) link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  main.prepend(nav);
})();
