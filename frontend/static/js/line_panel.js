/* global Api */
/**
 * Phase 91.3 (D131/D133): the spoken lines of a video whose visuals have their own editor (solo explainers, the
 * conversation storyboard). Edit one line and save it alone; only the lines whose voice no longer matches get a new
 * voice ("Make the voice again (N)": synthesize them, then mix); then the caller refreshes its preview.
 */
const LinePanel = (() => {
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function mount(container, projectId, { onVoice } = {}) {
    const state = { lines: [], busy: false };
    container.innerHTML = `<details class="line-panel" open><summary><strong>Spoken lines</strong></summary>
      <p class="section-hint">Edit a line and save it: only the lines you change get a new voice. Then generate the video.</p>
      <div class="line-panel-bar"><span class="line-panel-status" aria-live="polite"></span>
        <button type="button" class="btn btn-primary btn-sm" data-act="voice" hidden>Make the voice again</button></div>
      <ol class="line-panel-list"></ol></details>`;
    const $ = (selector) => container.querySelector(selector);
    const status = (text) => { $(".line-panel-status").textContent = text; };

    function render() {
      $(".line-panel-list").innerHTML = state.lines.map((line, at) => `<li class="line-panel-item">
        <span class="line-panel-who">${at + 1}. ${escape(line.speaker)}${line.audio_ok ? "" : ' <span class="beat-voice-dot" title="Its voice must be made again">●</span>'}</span>
        <textarea rows="2" data-at="${at}" aria-label="Line ${at + 1}">${escape(line.text)}</textarea>
        <button type="button" class="btn btn-ghost btn-sm" data-act="save" data-at="${at}" disabled>Save</button></li>`).join("");
      const stale = state.lines.filter((line) => !line.audio_ok).length;
      const voice = $("[data-act='voice']");
      voice.hidden = !stale; voice.textContent = `Make the voice again (${stale})`;
    }
    async function reload() { state.lines = await Api.getBeatLines(projectId); render(); }

    container.addEventListener("input", (event) => {
      const box = event.target.closest("textarea[data-at]"); if (!box) return;
      const at = Number(box.dataset.at);
      container.querySelector(`[data-act='save'][data-at='${at}']`).disabled = box.value.trim() === state.lines[at].text || !box.value.trim();
    });
    container.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-act]"); if (!button || state.busy) return;
      if (button.dataset.act === "save") {
        const at = Number(button.dataset.at), text = container.querySelector(`textarea[data-at='${at}']`).value.trim();
        button.disabled = true; status("Saving…");
        try { await Api.saveBeatText(projectId, state.lines[at].id, text); await reload(); status("Saved · make the voice again for this line"); }
        catch (error) { status(`Not saved: ${error.message || error}`); button.disabled = false; }
      }
      if (button.dataset.act === "voice") {
        state.busy = true; button.disabled = true;
        try {
          const stale = state.lines.filter((line) => !line.audio_ok);
          for (const [at, line] of stale.entries()) {
            status(`Making the voice ${at + 1}/${stale.length}…`);
            await Api.previewTtsLine(projectId, line.id, { reuse_cached: true });
          }
          status("Mixing the audio…");
          let music = null;
          try { music = (await Api.getAudioStatus(projectId))?.background_music || null; } catch { music = null; }
          await Api.generateAudio(projectId, music);
          await reload(); status("Voice made · generate the video when you are done");
          if (onVoice) await onVoice();
        } catch (error) { status(`The voice could not be made: ${error.message || error}`); }
        finally { state.busy = false; button.disabled = false; }
      }
    });
    await reload();
    return { reload };
  }
  return { mount };
})();
window.LinePanel = LinePanel;
