# PHASE-STATE — Phase 70: library package, clean-up and release 1.5.0

- **Status:** implemented_verified 2026-10-22. Full pytest 2008 passed + the new Settings browser test, which raced once in the full run (the list reloads after the status line) and now waits for it, passing 3/3; Vitest 179.
- **Real data:** library package exported (`data/exports/handoff-1.5.0/library-20261022.zip`, 1.37 GB: 5 characters, 226 character pictures, 158 activities, 55 scenes, 13 music tracks, 804 files). Rehearsed on an empty data folder: every row and file arrived, no path missing, no API key. Found in the rehearsal and fixed: a new machine seeds the 55 built-in scenes itself (newer, no picture), so their background paths were not taken — a kept row now takes the values it lacks.
- **Clean-up on the real data (owner choice: all 15 test projects):** database backed up to `data/backups/app-before-cleanup-20261022T093056Z.db`, 15 projects deleted through the service layer (integrity and foreign keys OK); 20.9 GB of temporary stages, older app backups, render staging and deleted-project media removed, and 0.8 GB of old test backups. Kept: the newest app backup, the pre-clean-up database, the git branch bundle, the pre-Phase-33 character pictures. Seven empty, access-locked folders in `data/tmp` remain (0 MB).
- **Tasks:** 5/5.

| Task | Scope | Status |
|---|---|---|
| 70.1 | Library package service | implemented_verified |
| 70.2 | API, script, Settings section | implemented_verified |
| 70.3 | Clean-up scripts | implemented_verified |
| 70.4 | Tests | implemented_verified |
| 70.5 | Release 1.5.0 and hand-over | implemented_verified |
