/** Shared resizable workspace shell. Presentation only: it never owns app data or API calls. */
window.WorkspaceShell = (function () {
  function setPaneWidth(pane, width) {
    pane.style.flexBasis = `${width}px`;
  }

  function makeVerticalResizer(handle, pane, { min, max, side }) {
    let dragging = false;
    let startX = 0;
    let startWidth = 0;

    function clamp(width) {
      return Math.min(max, Math.max(min, width));
    }

    function finishDrag() {
      if (!dragging) return;
      dragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    handle.addEventListener("pointerdown", (event) => {
      dragging = true;
      startX = event.clientX;
      startWidth = pane.getBoundingClientRect().width;
      handle.setPointerCapture(event.pointerId);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });
    handle.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const delta = side === "left" ? event.clientX - startX : startX - event.clientX;
      const width = clamp(startWidth + delta);
      if (width > min) pane.classList.remove("collapsed");
      setPaneWidth(pane, width);
    });
    handle.addEventListener("pointerup", finishDrag);
    handle.addEventListener("pointercancel", finishDrag);
    handle.addEventListener("lostpointercapture", finishDrag);
    handle.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 40 : 12;
      const current = pane.getBoundingClientRect().width;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const direction = event.key === "ArrowLeft" ? -1 : 1;
      const signedStep = side === "left" ? direction * step : -direction * step;
      const width = clamp(current + signedStep);
      if (width > min) pane.classList.remove("collapsed");
      setPaneWidth(pane, width);
    });
  }

  function makeHorizontalResizer(handle, pane, { min, max }) {
    let dragging = false;
    let startY = 0;
    let startHeight = 0;

    function finishDrag() {
      if (!dragging) return;
      dragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    handle.addEventListener("pointerdown", (event) => {
      dragging = true;
      startY = event.clientY;
      startHeight = pane.getBoundingClientRect().height;
      handle.setPointerCapture(event.pointerId);
      document.body.style.cursor = "row-resize";
      document.body.style.userSelect = "none";
    });
    handle.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const height = Math.min(max(), Math.max(min, startHeight + startY - event.clientY));
      pane.style.flexBasis = `${height}px`;
    });
    handle.addEventListener("pointerup", finishDrag);
    handle.addEventListener("pointercancel", finishDrag);
    handle.addEventListener("lostpointercapture", finishDrag);
  }

  function init(config) {
    const { sidebar, inspector, timeline, resizerLeft, resizerRight, resizerTop, collapseBtn } = config;
    if (resizerLeft && sidebar) makeVerticalResizer(resizerLeft, sidebar, { min: 56, max: 420, side: "left" });
    if (resizerRight && inspector) makeVerticalResizer(resizerRight, inspector, { min: 260, max: 480, side: "right" });
    if (resizerTop && timeline) makeHorizontalResizer(resizerTop, timeline, { min: 110, max: () => window.innerHeight * 0.7 });
    if (collapseBtn && sidebar) {
      collapseBtn.addEventListener("click", () => {
        const collapsed = sidebar.classList.toggle("collapsed");
        collapseBtn.setAttribute("aria-expanded", String(!collapsed));
        collapseBtn.textContent = collapsed ? "»" : "« Collapse";
      });
    }
  }

  return Object.freeze({ init });
})();
