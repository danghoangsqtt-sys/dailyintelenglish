# PLAN — Phase 55: Solo stage look (ENH-037)

Status: execution_authorized 2026-10-21 — owner asked for the change and answered the three design questions. Replaces the Solo look; the conversation video is unchanged.

| Task | Scope | Depends on |
|---|---|---|
| [55.1](tasks/task-55.1.md) | Schema + proposal: per-segment `scene`, visual kind `activity`; prompt lists scenes/activities; source fingerprint + approval pin plate/activity hashes | — |
| [55.2](tasks/task-55.2.md) | Layout rules v2: waist-up stage framing, card panel opposite the presenter, proof against head/torso; 16:9 and 9:16 | 55.1 |
| [55.3](tasks/task-55.3.md) | Renderer: scene plate background (crossfade + slow zoom), activity insert reveal, translucent card, large presenter, bottom shade; Player preview rebuilt | 55.1, 55.2 |
| [55.4](tasks/task-55.4.md) | Media bridge + editor: stage plates/activities for preview/render, activity usage records, Step 5 scene/activity pickers and new placement ranges | 55.1–55.3 |
| [55.5](tasks/task-55.5.md) | Verification: full tests, Desktop rebuild/install with backups, re-propose and re-render Lina's test video, frames to owner | all |

Sequential (shared schema/geometry contract), one session. No version bump; CHANGELOG `[Unreleased]`.

Compatibility: plans with `rules_version` 1 stay readable; approval/render require re-arranging to v2 (existing "outdated layout" path). Old Solo renders stay on disk.

Risks: front pictures are full-body 1280×1536; waist-up means a figure about twice the frame height with the lower half off-frame, so hands of wide gestures may pass in front of a card (allowed: the presenter is drawn above the card; the proof protects the card from the head and torso, not from hands). Scene plates are generic places; the activity insert is the only per-idea picture.
