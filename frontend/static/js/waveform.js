/**
 * Reusable canvas waveform renderer + seek control for an <audio> element (Task 1.10:
 * "Audio wave preview" — the one item Task 1.10's own acceptance criteria left open).
 *
 * Decodes the audio once via the Web Audio API, draws peak bars on a canvas, tints the
 * portion already played, and lets the user click the waveform to seek. Pure client-side
 * visualization — no backend changes, no new architecture. Falls back to leaving the
 * canvas blank (the native <audio> control still works) if decoding ever fails, since a
 * cosmetic feature must never break audio preview itself.
 */
const Waveform = (() => {
  const PLAYED_COLOR = "#7c3aed"; // --accent
  const UNPLAYED_COLOR = "#8b949e"; // --text-muted
  const BAR_GAP_RATIO = 0.35;

  function resolveCssColor(variableName, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    return value || fallback;
  }

  function computePeaks(audioBuffer, bucketCount) {
    const channelData = audioBuffer.getChannelData(0);
    const samplesPerBucket = Math.max(1, Math.floor(channelData.length / bucketCount));
    const peaks = new Float32Array(bucketCount);
    for (let bucket = 0; bucket < bucketCount; bucket += 1) {
      const start = bucket * samplesPerBucket;
      const end = Math.min(start + samplesPerBucket, channelData.length);
      let max = 0;
      for (let i = start; i < end; i += 1) {
        const abs = Math.abs(channelData[i]);
        if (abs > max) max = abs;
      }
      peaks[bucket] = max;
    }
    return peaks;
  }

  function draw(canvas, peaks, playedRatio) {
    const context = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    const middle = height / 2;
    const barWidth = width / peaks.length;
    const playedColor = resolveCssColor("--accent", PLAYED_COLOR);
    const unplayedColor = resolveCssColor("--text-muted", UNPLAYED_COLOR);

    context.clearRect(0, 0, width, height);
    peaks.forEach((peak, index) => {
      const barHeight = Math.max(2, peak * height);
      const x = index * barWidth;
      const isPlayed = index / peaks.length <= playedRatio;
      context.fillStyle = isPlayed ? playedColor : unplayedColor;
      context.globalAlpha = isPlayed ? 1 : 0.55;
      context.fillRect(x, middle - barHeight / 2, Math.max(1, barWidth * (1 - BAR_GAP_RATIO)), barHeight);
    });
    context.globalAlpha = 1;
  }

  /**
   * Render a waveform for `audioUrl` into `canvas`, synced to `audioElement`'s playback.
   * Safe to call even if decoding fails — errors are logged, not thrown, and the canvas
   * is simply left blank so the native <audio> control still works.
   */
  async function render(canvas, audioUrl, audioElement) {
    const cssWidth = canvas.clientWidth || 300;
    const cssHeight = canvas.clientHeight || 56;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);

    let peaks;
    try {
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const bucketCount = Math.max(20, Math.round(cssWidth / 3));
      peaks = computePeaks(audioBuffer, bucketCount);
      await audioContext.close();
    } catch (error) {
      console.error(`Failed to decode audio for waveform (${audioUrl}):`, error);
      return;
    }

    const redraw = () => {
      const ratio = audioElement.duration ? audioElement.currentTime / audioElement.duration : 0;
      draw(canvas, peaks, ratio);
    };
    redraw();
    audioElement.addEventListener("timeupdate", redraw);
    audioElement.addEventListener("seeked", redraw);

    canvas.addEventListener("click", (event) => {
      if (!Number.isFinite(audioElement.duration) || audioElement.duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
      audioElement.currentTime = ratio * audioElement.duration;
    });
  }

  return { render };
})();
