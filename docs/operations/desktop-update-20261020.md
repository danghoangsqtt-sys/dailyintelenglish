# Desktop update — Phase 53 (2026-10-20)

Owner request: build and install the Desktop EXE with the Phase 53 fix (BUG-049) using the install procedure with backups, then push.

| Step | Result |
|---|---|
| Build | `scripts/build_exe.ps1 -OutputRoot data/tmp/phase53-exe-stage`; source `456e2c1`, `source_dirty: false`, built 2026-10-20T08:07:48Z |
| Rehearsal on a data copy | `verify_desktop_upgrade.py --stage …`: 5/5 profiles with 29 native / 21 front slots, 21 strict prompts, 47 voices; 13 projects, 209 character assets; original rows preserved, 436 native files preserved; 2 restarts; no page errors |
| Install | `scripts/install_desktop.ps1`: idle-job check passed; `app.before-upgrade.db`, `app.at-exit.db`, previous app folder and shortcut kept in `data/backups/desktop-20261020-151033-570/` |
| Running build | `/api/system/build`: build `ab087f7b68b5…`, commit `456e2c1`, packaged; same data `instance_id` as before |
| Installed UI | `verify_desktop_upgrade.py --installed`: 5/5 profiles as above; served `character_profiles.js` contains the per-card refusal reason |

Version label stays 1.4.0-rc.1; the GitHub release ZIP is unchanged. Rollback: close Studio, restore the folder and the matching DB pair from the backup above.

Pending: owner retries Lina's `gesture-count-1` / `gesture-count-2` uploads on this build.
