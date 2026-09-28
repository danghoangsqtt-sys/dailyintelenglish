/**
 * Report-UX-1: shared elapsed-time + ETA overlay for a generation-in-progress banner.
 * Same component shape as StepNav/KeyboardShortcuts/SaveIndicator -- pure UI-state glue,
 * no network/business logic of its own.
 *
 * `mount()` builds its own persistent child DOM once and returns a controller. Callers on a
 * poll loop (Step 2/3) must call `mount()` exactly once per job lifecycle and then only
 * `setProgress()` on every subsequent poll tick -- if the caller instead rebuilds the
 * mounted element's `innerHTML` on every poll (as Step 2/3's own banner does today for the
 * surrounding text), the elapsed timer's DOM node gets destroyed and recreated, visibly
 * resetting the counter to 0:00. See task-report-ux-1.md's design doc for the full finding.
 */
(() => {
  function formatElapsed(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  /**
   * @param {Object} opts
   * @param {HTMLElement} opts.element - empty container this owns exclusively.
   * @param {number} opts.baselineSec - hardcoded per-page ETA baseline (Gate B-11 numbers).
   * @param {string|null} [opts.startedAtIso] - real job start time (ai_generation_jobs.started_at,
   *   ISO-8601 with UTC offset). Falls back to `Date.now()` for pages with no durable job
   *   (Step 4/5) or no value yet. Anchoring to the real start time means a page refresh
   *   mid-generation (AiJob.resume()) shows true elapsed, not a reset-to-0:00 clock.
   * @param {boolean} [opts.showEta] - Step 5's 1s baseline makes an ETA string pure noise
   *   (it would flip between "left" and "wrapping up" within the same second); default true.
   */
  function mount({ element, baselineSec, startedAtIso, showEta = true }) {
    element.innerHTML =
      '<span class="generation-status-stage"></span>' +
      '<span class="generation-status-elapsed"></span>' +
      (showEta ? '<span class="generation-status-eta"></span>' : "");
    const stageEl = element.querySelector(".generation-status-stage");
    const elapsedEl = element.querySelector(".generation-status-elapsed");
    const etaEl = showEta ? element.querySelector(".generation-status-eta") : null;

    const startedAtMs = startedAtIso ? new Date(startedAtIso).getTime() : Date.now();
    let stopped = false;
    let timerId = null;

    function tick() {
      if (stopped) return;
      const elapsedSec = (Date.now() - startedAtMs) / 1000;
      elapsedEl.textContent = etaEl ? `· ${formatElapsed(elapsedSec)} ` : `· ${formatElapsed(elapsedSec)}`;
      if (etaEl) {
        const remaining = baselineSec - elapsedSec;
        etaEl.textContent = remaining > 0 ? `· ~${Math.ceil(remaining)}s left` : "· wrapping up…";
      }
    }

    tick();
    timerId = setInterval(tick, 1000);

    /**
     * @param {Object} progress
     * @param {string|null} [progress.stageLabel]
     * @param {number|null} [progress.progressPercent]
     * @param {boolean} [progress.done] - stops the timer; the frozen final elapsed value
     *   stays visible (DRUX-a: no artificial hide -- callers decide whether/when to remove
     *   this element from the DOM entirely, since that decision differs by page).
     */
    function setProgress({ stageLabel, progressPercent, done } = {}) {
      if (stageLabel != null && progressPercent != null) {
        stageEl.textContent = `${stageLabel} (${progressPercent}%) `;
      } else if (stageLabel != null) {
        stageEl.textContent = `${stageLabel} `;
      } else {
        stageEl.textContent = "";
      }
      if (done && !stopped) {
        stopped = true;
        clearInterval(timerId);
      }
    }

    function destroy() {
      stopped = true;
      if (timerId) clearInterval(timerId);
    }

    return { setProgress, destroy };
  }

  window.GenerationStatus = Object.freeze({ mount });
})();
