# Phase 46 — Audit bug fixes and render reliability

Date: 2026-10-15. Requests: BUG-037, BUG-038, BUG-039 and BUG-040. Released version remains 1.3.0; patch candidate 1.3.1. This records technical verification; owner visual gates B-25/B-26/B-27/B-28 are separate.

## State and documentation (46.1)

HANDOFF now records Phases 20/22–25/27–29 complete and includes Phase 26. Old in-flight narratives are retained as history, not current status. The seven phases closed by owner decision D109 have annotated local completion tags pointing at `c441f8f`, the commit that recorded D109. Pending phases have no completion tags.

Current PROJECT-META, AI-GUIDE, ARCHITECTURE and the structure map describe Qwen images, profiles/sprites/Activity Library and Remotion-only video. All three required Mermaid sidecars match the embedded diagrams. CHANGELOG records the previously omitted BUG-036 and ENH-035.

## Browser load timeouts (46.2)

The audit run had 12 Playwright timeouts, mostly waiting for `load`; two representative tests passed alone. Eleven HTML pages requested Inter through Google Fonts. A stalled stylesheet can prevent `load`: the new regression held external requests pending and the unmodified dashboard timed out in 5 seconds. This proves a failure mechanism, not that every timeout in the earlier run had the same cause.

Inter now ships as `frontend/static/fonts/Inter-Variable.ttf` with its SIL OFL license. Google Fonts links are removed and shared CSS loads the local font. Font family and weight range are preserved. Existing tests still use their normal `load` event and timeouts.

- Font source: [Google Fonts Inter](https://github.com/google/fonts/tree/main/ofl/inter).
- Font SHA256: `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031`.
- `tests/test_offline_fonts_browser.py` reaches `load` on 13 routes, loads the actual Inter font, and checks that no external requests are made.
- New regression plus all four previously affected modules: **38 passed in 34.57 seconds**.
- Load-event semantics: [Playwright navigation documentation](https://playwright.dev/python/docs/navigations).

The first full run after the font fix passed 1,614 tests and failed one Learning navigation with `net::ERR_NO_BUFFER_SPACE` (not a load timeout). The Learning module then passed 5/5 alone. Windows System event 4231 at 07:49:17 on 2026-10-15 reports failure to allocate an ephemeral TCP port during the earlier audit. A later snapshot showed 295 TIME_WAIT connections; this is not proof of the resource state at the failing instant.

The shared test fixture now retries one loopback `Page.goto` only on `ERR_NO_BUFFER_SPACE`, after a 250 ms delay, and emits a warning with the URL. It does not retry timeouts, application assertions, connection-refused errors or external navigation. A persistent buffer error fails on the second attempt. Default page `load` checks remain unchanged. Six injected-error cases and the Learning/offline-browser modules passed together (12 tests). This recovers a transient test transport allocation failure without rerunning test actions or changing Windows network settings.

Faster local page loading also exposed a real sidebar initialization race: a Studio rail was still animating from 232 to 64 px at `load` (measured 103.796875 px), violating its expected initial layout. This was reproduced in a fail-fast full run (283 passed before the failure). The sidebar now applies its saved/default state with transitions disabled, resolves the initial geometry, then enables the existing user-triggered transitions. The original width, toggle and drawer assertions are unchanged. Sidebar, transport-classification, Learning and offline-browser tests passed together: **27 passed in 21.18 seconds**.

## Remotion navigation failure (46.3)

The installed Remotion code emits `Visited "http://localhost:3000/index.html" but got no response.` when its `page.goto` result is null. The reason that happened in the original production run remains unconfirmed. Port contention and resource pressure are hypotheses, not findings.

The Python bridge now launches one fresh process for that specific loopback navigation/no-response error. Maximum two attempts share the existing **600-second** subprocess budget. Other errors and process timeouts still fail. Failed staging files are discarded; a prior published video is preserved until a new render succeeds. This is a bounded recovery for the observed failure class, not a claim that the underlying browser defect was eliminated.

Every attempt saves its verbose stdout/stderr, UTC time, command, exit status and elapsed time in `<video-name>.render-<id>.log` beside the output. The UI error includes that path when available. Input props are not explicitly written into the diagnostic record. Failure to write diagnostics is logged and does not invalidate a successful video.

- Focused media/service/API tests: **47 passed in 21.82 seconds**.
- Fault-injection regression failed before the change, then passed: first attempt returns the exact navigation error; second attempt succeeds with only 575 seconds remaining after a simulated 25-second first attempt.
- Additional checks cover repeated navigation failure, ordinary failure without retry, exhausted total budget and preservation of old output.
- Diagnostic guidance: [Remotion debugging render failures](https://www.remotion.dev/docs/troubleshooting/debug-failed-render).

## Full real render

`data/tmp/phase46/verify_full_render.py` reads the existing "Shopping at the Market" episode through SQLite `mode=ro` plus `PRAGMA query_only=ON`; `db.total_changes` stays zero. It builds the real talking-sprite composition from existing audio and assets and renders to a separate disposable destination. The test uses the default silent brand slides and makes no AI/TTS call.

| Measure | Result |
|---|---|
| Render wall time | 194.886 s, one successful attempt |
| Expected composition duration | 240.866667 s |
| MP4 duration | 240.917333 s |
| Video | 1280x720, H.264 |
| Audio | AAC; audio/video duration difference below 0.1 s |
| DB writes by verification connection | 0 |

Local evidence: `data/tmp/phase46/full-episode.mp4`, `episode-props.json`, `full-render-evidence.json` and `full-episode.render-4ae6e1b3.log`. These runtime artifacts are ignored by Git. This technical check does not accept an owner visual gate.

## Final regression gate

Ruff, TypeScript typecheck and all **72 Vitest tests** passed. The first full pytest run: **1,614 passed, one ERR_NO_BUFFER_SPACE failure in 15:28**; the extra transport recovery above was added after that evidence. Final full run after the sidebar and transport fixes: **1,621 passed, one existing dependency deprecation warning, in 871.13 s (14:31)**. The unchanged default load checks and sidebar geometry assertions all passed. Local implementation remains subject to PM acceptance; no release or exe rebuild is performed by this phase.
