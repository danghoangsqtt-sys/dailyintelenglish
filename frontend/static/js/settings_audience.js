/** Phase 72 (ENH-054): Settings -> General -> Channel audience (international / Vietnamese / both). */
(() => {
  const status = document.getElementById("channel-audience-status");
  const inputs = [...document.querySelectorAll("input[name=channel-audience]")];
  const show = (value) => inputs.forEach((input) => { input.checked = input.value === value; });
  Api.getChannelAudience().then((data) => show(data.audience)).catch((error) => { status.textContent = error.message; });
  inputs.forEach((input) => input.addEventListener("change", async () => {
    if (!input.checked) return;
    try {
      show((await Api.setChannelAudience(input.value)).audience);
      status.textContent = "Saved. New videos follow it; a rendered video shows it after its next render.";
    } catch (error) {
      status.textContent = error.message;
    }
  }));
})();
