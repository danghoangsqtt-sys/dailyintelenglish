/**
 * Shared durable-AI-job lifecycle: create-or-resume, poll with hidden-tab
 * backoff, terminal-state resolution (Phase 13, Task 13.6). Same component
 * shape as StepNav/KeyboardShortcuts/SaveIndicator — pure UI-state glue, no
 * business logic of its own. The calling page supplies the actual API calls
 * (createFn/activeFn/getFn/cancelFn) and owns rendering via onStateChange.
 */
(() => {
  const VISIBLE_POLL_MS = 2000;
  const HIDDEN_POLL_MULTIPLIER = 4; // "hidden-window backoff" per the controlling plan
  const TERMINAL_STATUSES = new Set(["complete", "error", "cancelled", "stale"]);

  function run({ createFn, activeFn, getFn, cancelFn, onStateChange }) {
    let jobId = null;
    let timerId = null;
    let stopped = false;
    let settled = false;
    let resolvePromise;
    let rejectPromise;
    const promise = new Promise((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });

    function settle(job, err) {
      if (settled) return;
      settled = true;
      if (err) rejectPromise(err);
      else if (job.status === "complete") resolvePromise(job);
      else rejectPromise(Object.assign(new Error(`ai job ended with status: ${job.status}`), { job }));
    }

    function stop() {
      stopped = true;
      if (timerId) {
        clearTimeout(timerId);
        timerId = null;
      }
    }

    function scheduleNext() {
      if (stopped) return;
      const interval = document.visibilityState === "hidden" ? VISIBLE_POLL_MS * HIDDEN_POLL_MULTIPLIER : VISIBLE_POLL_MS;
      timerId = setTimeout(poll, interval);
    }

    async function poll() {
      if (stopped) return;
      let job;
      try {
        job = await getFn(jobId);
      } catch (err) {
        stop();
        settle(null, err);
        return;
      }
      onStateChange(job);
      if (TERMINAL_STATUSES.has(job.status)) {
        stop();
        settle(job, null);
        return;
      }
      scheduleNext();
    }

    function onVisibilityChange() {
      // Do one immediate poll on becoming visible again, rather than waiting
      // out whatever's left of the (longer, hidden-tab) interval.
      if (document.visibilityState === "visible" && !stopped && jobId) {
        if (timerId) clearTimeout(timerId);
        poll();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    // start()/resume() deliberately do NOT return `promise` themselves: an
    // `async function` that returns a Promise value has its own returned
    // promise transparently chain onto it (standard JS promise-flattening),
    // so `await instance.start()` would silently block until the whole job
    // finishes instead of just until it's been created/found. Callers await
    // `start()`/`resume()` for the fast "is a job now underway" answer, and
    // await the separate `promise` property (returned by `run()` below)
    // whenever they actually want to wait for completion.

    /** Create a brand-new job (Generate button) and start polling it. */
    async function start() {
      try {
        const job = await createFn();
        jobId = job.id;
        onStateChange(job);
        if (TERMINAL_STATUSES.has(job.status)) {
          stop();
          settle(job, null);
        } else {
          scheduleNext();
        }
      } catch (err) {
        stop();
        settle(null, err);
      }
    }

    /**
     * Check for an already-active job (page load / refresh) and, if one
     * exists, reattach polling to it. Returns `true` if a job was found
     * (whether still active or already terminal -- either way, `promise`
     * will settle appropriately), `false` if there was nothing to resume or
     * the check itself failed (resuming is best-effort; a caller always
     * falls back to the normal idle/Generate state rather than a false error).
     */
    async function resume() {
      let active;
      try {
        active = await activeFn();
      } catch {
        return false;
      }
      if (!active) return false;
      jobId = active.id;
      onStateChange(active);
      if (TERMINAL_STATUSES.has(active.status)) {
        stop();
        settle(active, null);
      } else {
        scheduleNext();
      }
      return true;
    }

    /** Idempotent server-side already; keeps polling until it reaches `cancelled`. */
    async function cancel() {
      if (!jobId) return;
      await cancelFn(jobId);
    }

    function destroy() {
      stop();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    }

    return { start, resume, cancel, destroy, promise };
  }

  window.AiJob = Object.freeze({ run });
})();
