/** Character profiles initialize independently in character_profiles.js. Scenes live in Activity Library. */
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("theme-toggle")?.addEventListener("click", Theme.toggle);
    if (location.hash === "#scenes") location.replace("/activities?tab=scenes");
  });
})();
