# Focused audit — missing character voices and front21 UI

Date:2026-10-16, Asia/Bangkok. Requested via vp-audit. Scope: the running Desktop instance, bundled UI, staged build, existing-profile compatibility evidence and current feature documentation. This is a focused audit, not a new full-codebase certification.

## Finding

The user is opening the installed pre-Phase48/49 application. Its served character page has neither the per-character voice picker nor the front21 tab. The latest source and staged distribution contain both. This explains the missing controls independently of which existing profile is selected.

| Evidence | Installed/running | Latest stage/source |
|---|---|---|
| EXE | `dist/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe` | `data/tmp/phase49-exe-stage/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe` |
| Build date |2026-10-15|2026-10-16|
| Build-info source |`f8f76753b9c3d81edd179006c626fde985dc79d7`, clean|`3c4cfced979b03f5201652cf9898666050463874`, dirty worktree build; verified implementation persisted later as`c517eca`|
| Version label |1.4.0-rc.1|1.4.0-rc.1 source trial; not a newly published release|
| `profile-voice-picker` in bundled HTML |absent|present|
| `profile-view-front` in bundled HTML |absent|present: Presenter ·21 pictures|

Direct `GET http://localhost:8000/characters` returned200 with both markers absent. The actual listening process was PID30048, executable under`dist/`, on port8000. The Desktop shortcut `C:/Users/Admin/Desktop/Daily Beyond English Studio.lnk` points to that installed EXE.

`backend/desktop_launcher.py:62–67` opens the existing URL and returns whenever its port is already occupied. Consequently launching the staged EXE on the default port while the old server remains active opens the old UI again. Closing only a browser tab does not replace the serving process. There is no build-identity check in this branch.

## Tier1 — current state consistency

Current HANDOFF/TRACKER/ROADMAP/Phase49 state agree: Phase48 and49.1–49.9 technically verified;49.10 implementation/package checks verified but real-art V49 acceptance pending. Four technical49.6–49.9 tags exist; Phase49 is not falsely marked owner-accepted. Worktree was clean before audit output, HEAD`b659fb1`, upstream divergence0/0. Historical checkpoints are not interpreted as current installed capabilities.

## Tier2 — documentation drift

Re-detected BUG-044 after the later Phase49 implementation: `.viepilot/ARCHITECTURE.md` still caps verified Solo scope at49.5; `.viepilot/PROJECT-META.md` still says49.6–49.10 are planned; `renderer/README.md` still calls layout/Player/render extensions planned. These contradict the current Phase49 state and code. Prior BUG-044 resolution was valid at its earlier checkpoint; these later additions require another refresh. Append to the existing request instead of creating a duplicate.

The user guide correctly says the published/installed EXE is separate from source additions. However, the previous staged-EXE handoff is insufficient operationally because its default-port launcher can reopen the older instance. The same version label on both builds also does not distinguish feature availability for the user.

## Tier3 — runtime correctness / delivery gap

High-priority BUG-045: Desktop still serves the old bundle and the single-instance branch masks the new staged bundle. Scope: installed distribution/shortcut, `backend/desktop_launcher.py`, `scripts/install_desktop.ps1`, release/build identity and installation instructions. This audit found no evidence that the existing profile itself causes these controls to disappear.

Existing-profile support is already exercised in the source evidence for49.3: isolated copied Hoang profile, native29 preservation, voice UI and21 front cards. The later frozen trial verified Player/front21 and no-audio editor twice against disposable data. These checks do not mean the current Desktop installation was updated.

## Recommended correction and guardrails

1. Preserve the existing profile/project database and assets. Make an online SQLite backup before the new build's first migration; verify integrity/FK and test migration against a disposable copy if needed. Keep installed1.4.0-rc.1 and its shortcut backed up for rollback.
2. At the local installation step, stop only the identified Studio instance after checking active work, install the verified complete staged folder via `scripts/install_desktop.ps1 -StageDirectory data/tmp/phase49-exe-stage/DailyIntelEnglishStudio`, and relaunch from the Desktop icon. This is a local application update, not a GitHub release or V49 acceptance.
3. Verify the live port-owning process path/build and actual served UI, then open an existing profile: voice picker visible, Conversation29 intact, Presenter21 with per-action prompts/upload controls. Confirm existing voices/assets and project data remain available after restart.
4. Prevent recurrence with explicit build identity/availability in diagnostics and a build-aware existing-instance check. Do not silently terminate another running build or redirect the user without identifying it. Refresh the three stale documentation files under BUG-044.

No production code, installed EXE, shortcut, running owner process, profile, voice or owner database was changed by this audit. No migration/installation/release was executed. Audit artifacts are the report and auto-logged requests.

Requests: [BUG-045](../requests/BUG-045.md), [BUG-044 re-detected](../requests/BUG-044.md). Suggested next implementation route: vp-evolve BUG-045 BUG-044, then vp-auto.


## Follow-up implementation — Phase51

The observations above describe the pre-fix audit. Under the subsequent explicit owner `vp-auto xử lý bug`, BUG-045 local Desktop/build identity recovery and recurring BUG-044 docs were implemented and verified. Local Desktop now serves Build468f9f7ce4b4; all5 old profiles expose47 voices and29/21 slots/prompts, owner rows/289 native files preserved. Full1884 passed in787.66s. [Resolution report](../../docs/operations/desktop-recovery-20261016.md). Published release and real-art/V49 acceptance remain unchanged/pending.
