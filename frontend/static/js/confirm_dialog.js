/**
 * Walkthrough 2026-10-14: an in-page confirmation instead of the browser's native window.confirm(). Some hosts block
 * native dialogs (an embedded browser pane, some webviews, "prevent this page from creating more dialogs"): confirm()
 * then returns false at once and the button looks dead ("Regenerate thumbnails" did nothing). This dialog always shows.
 *
 *   if (!(await ConfirmDialog.ask("Delete this clip?", { confirmLabel: "Delete", danger: true }))) return;
 *
 * Enter confirms, Escape or a click outside cancels; focus moves to the confirm button and back afterwards.
 */
(() => {
  let open = null; // the dialog being shown: while it is up, another ask() (a double click) answers "no"

  function build(message, { title, confirmLabel, cancelLabel, danger }) {
    const backdrop = document.createElement("div");
    backdrop.className = "confirm-backdrop";
    backdrop.style.cssText = "position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;"
      + "background:rgba(0,0,0,.45);padding:16px;";
    const box = document.createElement("div");
    box.className = "card confirm-dialog";
    box.setAttribute("role", "alertdialog");
    box.setAttribute("aria-modal", "true");
    box.style.cssText = "max-width:440px;width:100%;padding:20px 22px;background:var(--surface-2,#fff);color:var(--text,#111);"
      + "border:1px solid var(--surface-border,#ccc);border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.3);";
    const heading = document.createElement("h2");
    heading.id = `confirm-title-${Date.now()}`;
    heading.textContent = title;
    heading.style.cssText = "margin:0 0 8px;font-size:17px;";
    const text = document.createElement("p");
    text.id = `${heading.id}-text`;
    text.textContent = message;
    text.style.cssText = "margin:0 0 18px;line-height:1.45;white-space:pre-line;";
    box.setAttribute("aria-labelledby", heading.id);
    box.setAttribute("aria-describedby", text.id);
    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;justify-content:flex-end;gap:10px;";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "btn btn-ghost";
    cancel.dataset.confirm = "cancel";
    cancel.textContent = cancelLabel;
    const ok = document.createElement("button");
    ok.type = "button";
    ok.className = danger ? "btn btn-danger" : "btn btn-primary";
    ok.dataset.confirm = "ok";
    ok.textContent = confirmLabel;
    actions.append(cancel, ok);
    box.append(heading, text, actions);
    backdrop.append(box);
    return { backdrop, box, ok, cancel };
  }

  async function ask(message, options = {}) {
    if (open) return false;
    const settings = { title: "Please confirm", confirmLabel: "Continue", cancelLabel: "Cancel", danger: false, ...options };
    const previousFocus = document.activeElement;
    const { backdrop, box, ok, cancel } = build(String(message), settings);
    let finish;
    const answer = new Promise((resolve) => { finish = resolve; });
    open = answer;
    const close = (value) => {
      document.removeEventListener("keydown", onKey, true);
      backdrop.remove();
      open = null;
      if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus();
      finish(value);
    };
    const onKey = (event) => {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(false); }
      else if (event.key === "Enter" && document.activeElement !== cancel) { event.preventDefault(); event.stopPropagation(); close(true); }
      else if (event.key === "Tab") { // keep focus inside the dialog
        event.preventDefault();
        (document.activeElement === ok ? cancel : ok).focus();
      }
    };
    ok.addEventListener("click", () => close(true));
    cancel.addEventListener("click", () => close(false));
    backdrop.addEventListener("click", (event) => { if (!box.contains(event.target)) close(false); });
    document.addEventListener("keydown", onKey, true);
    document.body.append(backdrop);
    ok.focus();
    return answer;
  }

  window.ConfirmDialog = Object.freeze({ ask });
})();
