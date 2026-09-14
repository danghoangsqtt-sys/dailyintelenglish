// Shared resizable-shell behavior for every UI Direction mockup page.
// Same pattern as this app's real frontend/static/js/*.js modules (step_nav.js,
// keyboard_shortcuts.js) — one small file, mounted the same way on every page.
window.WorkspaceShell = (function () {
  function makeVerticalResizer(handle, pane, opts) {
    const min = opts.min, max = opts.max, side = opts.side;
    let dragging = false, startX = 0, startWidth = 0;
    handle.addEventListener('pointerdown', (e) => {
      dragging = true; startX = e.clientX; startWidth = pane.getBoundingClientRect().width;
      handle.setPointerCapture(e.pointerId);
      document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none';
    });
    handle.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const delta = side === 'left' ? (e.clientX - startX) : (startX - e.clientX);
      pane.style.flexBasis = Math.min(max, Math.max(min, startWidth + delta)) + 'px';
    });
    handle.addEventListener('pointerup', () => { dragging = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; });
    handle.addEventListener('keydown', (e) => {
      const step = e.shiftKey ? 40 : 12;
      const cur = pane.getBoundingClientRect().width;
      if (e.key === 'ArrowLeft') pane.style.flexBasis = Math.max(min, cur - (side === 'left' ? step : -step)) + 'px';
      if (e.key === 'ArrowRight') pane.style.flexBasis = Math.min(max, cur + (side === 'left' ? step : -step)) + 'px';
    });
  }

  function makeHorizontalResizer(handle, pane, opts) {
    const min = opts.min, max = opts.max;
    let dragging = false, startY = 0, startHeight = 0;
    handle.addEventListener('pointerdown', (e) => {
      dragging = true; startY = e.clientY; startHeight = pane.getBoundingClientRect().height;
      handle.setPointerCapture(e.pointerId);
      document.body.style.cursor = 'row-resize'; document.body.style.userSelect = 'none';
    });
    handle.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const delta = startY - e.clientY;
      pane.style.flexBasis = Math.min(max, Math.max(min, startHeight + delta)) + 'px';
    });
    handle.addEventListener('pointerup', () => { dragging = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; });
  }

  // config: { sidebar, resizerLeft, inspector, resizerRight, timeline, resizerTop, collapseBtn }
  function init(config) {
    if (config.resizerLeft && config.sidebar) {
      makeVerticalResizer(config.resizerLeft, config.sidebar, { min: 56, max: 420, side: 'left' });
    }
    if (config.resizerRight && config.inspector) {
      makeVerticalResizer(config.resizerRight, config.inspector, { min: 260, max: 480, side: 'right' });
    }
    if (config.resizerTop && config.timeline) {
      makeHorizontalResizer(config.resizerTop, config.timeline, { min: 110, max: window.innerHeight * 0.7 });
    }
    if (config.collapseBtn && config.sidebar) {
      config.collapseBtn.addEventListener('click', (e) => {
        config.sidebar.classList.toggle('collapsed');
        e.currentTarget.textContent = config.sidebar.classList.contains('collapsed') ? '⟩⟩' : '⟨⟨ Thu gọn';
      });
    }
  }

  return { init };
})();
