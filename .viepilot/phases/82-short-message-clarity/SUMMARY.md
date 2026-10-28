# Phase 82 summary — Shorts that carry their message

Done 2026-10-28 on `owner-runs/20261001-r9` (not pushed, not installed).

- Knowledge and news Shorts (news, text on blur, Don't say / Say, Top 5, presenter, Vox) are written for 0.95 min
  (57 s + the 2 s end card) instead of 0.75. Quick templates stay at 45 s. Step 1 offers 30 / 45 / 57 s and picks 57 s
  for a knowledge template.
- Their script follows a "message first" structure: a hook question or claim, one context sentence, two or three key
  points each with an example or fact, and a takeaway that answers the hook, then the follow line.
- Clips cut from a 16:9 episode stand on their own: a first line that replies to earlier talk pulls the start back (up
  to 3 lines, within 90 s); the episode's goodbye is always dropped (the start moves back to keep 30 s); a last line
  asking the other speaker a question takes the answer. A clip that still opens on a reply or closes on the goodbye is
  dropped. The proposal prompt states the same rule.
- Real checks in a temporary sandbox: a news Short "Why more cities are adding bike lanes" got 55.0 s of audio with
  the new structure (it then waits for fact review, by design since Phase 66). Two real clip proposals on The Office
  Startup gave clips 3-8, 10-13 and 17-18: none opens on a reply or ends on the goodbye. The first real run showed that
  a goodbye was kept when dropping it left 29.99 s; fixed in `d975e9a`.
- Full pytest: 2204 passed after updating three tests that pinned 0.75 min; `test_progressed_project_is_read_only`
  failed once while the page was still loading and passes alone (known timing flake, not Phase 82).
