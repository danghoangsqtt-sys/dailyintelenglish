# Task 46.9: README and installation requirements for another Windows PC

## Authorization / bounded plan — 2026-10-15

Owner requests the location and requirements of the installation package and a professional README. Earlier authorization to update the project's GitHub continues to apply to these documentation changes. Scope is documentation only; do not change application logic or rebuild/relabel the tested release.

### allowed_files

- README.md: Vietnamese product overview, verified download, honest linked-runtime requirements, workflow, capabilities, limitations and versioned technical references.
- docs/user/windows-installation.md (new): repeatable installation from the exact v1.4.0-rc.1 source tag and binary ZIP, external renderer/FFmpeg setup, Desktop installer, optional local AI prerequisites, diagnostics and migration caveats.
- docs/assets/logo.png (new): copy the existing application logo for a stable README asset on both branches; no artwork changes.
- This task card: plan, checks and publication evidence.
- Isolated worktree under data/tmp/readme-20261015/: publish only README, installation guide and logo as a documentation commit based on origin/main, so the repository homepage receives the requested README. Do not merge the application branch into main or change the prerelease tag/assets.

## Risks / verification

- The release is a linked-runtime ZIP, not a self-contained Setup.exe. Opening the packaged EXE does not require Python; rendering needs Node >=24, npm-installed renderer, Chrome Headless Shell, FFmpeg and ffprobe. Local Qwen image generation separately requires a compatible Python/CUDA environment and complete model cache.
- Source installation must use the release tag, because main's application code is older. Binary staging must be inside the source workspace and distinct from dist/DailyIntelEnglishStudio for the existing installer.
- Do not promise fresh-PC end-to-end installation without actually testing a clean PC. Check commands against current source/CLI, parse PowerShell examples, validate Markdown links/assets/headings and review the final diff. No application tests are needed for documentation-only edits.
- Stage explicit files, use fast-forward pushes only, verify public README and guide after publication. Preserve all running jobs, data and user configuration.

## Status

Documentation delivered on GitHub main; synchronized to the owner branch with this task record.

### Publication recovery amendment

Read-only verification on 2026-10-15 found GitHub's release-by-tag and previous release-id endpoints both return 404, and the public releases list is empty; the annotated tag still resolves to f8f7675. Earlier task-46.8 publication evidence records release 413610137 and its digests. The owner's continuing authorization to publish the Windows usage trial covers restoring the same verified ZIP/checksum at the same tag. Allow a disposable recovery publisher under data/tmp/readme-20261015/ and GitHub prerelease metadata/assets only. Verify the retained ZIP SHA-256 before upload; never move the tag, change the executable or silently substitute another build. Record the new release id and verify public download endpoints. Installation documentation must not ship broken download links.

## Delivery / verification

- Professional Vietnamese README: existing logo, compact feature/workflow tables, prominent download/install links, truthful capability requirements, episode export example, trial limitations and versioned developer references. Added detailed Windows installation, diagnostics and data migration guide.
- Documentation-only main commit **8168b1354f7141bde8de71d291660793816b823b** published. Exactly README.md, docs/user/windows-installation.md and docs/assets/logo.png changed on main; no application branch merge. The older main application source remains unchanged; installation explicitly uses the v1.4.0-rc.1 source tag.
- Public raw README, guide and logo hashes match local files. GitHub's rendered HTML checked: one H1 per document, 6/2 tables, 3/6 code blocks and developer details section. Verified 25 distinct link targets locally/versioned where applicable; all 5 PowerShell command blocks parse without executing installations. Logo is byte-identical to renderer/public/brand/logo.png. Diff whitespace checks clean.
- Restored prerelease **413640860**, published/non-draft at the original v1.4.0-rc.1 URL, with the exact retained ZIP/checksum. ZIP SHA-256 **0abdb9616593ecc983c152d00c0ee08380ee7240c4aa54e6b94d7916eed91b09**, 140,513,826 bytes, GitHub asset digest matches. Public canonical ZIP URL returns HTTP 206 and ZIP signature; checksum download matches. Existing annotated tag unchanged. Cause of the previous release disappearance is not established.
- Network recovery: initial release POST timed out after creating the draft; queried the release list and resumed that exact draft, avoiding duplicate creation. First git push returned HTTP 408 with main unchanged; a bounded HTTP/1.1 fixed-buffer retry succeeded and remote ref was verified.
- Evidence under data/tmp/readme-20261015/: validation.json, rendered README.html/windows-installation.html, public-verification.json, github-release.json and retained publisher/check scripts. Older publication evidence remains in data/tmp/exe-trial-20261015/.
- Documentation-only update: no application tests rerun, runtime/data/config modified or installed EXE replaced. Clean-PC installation remains untested and is explicitly disclosed in the guide; owner acceptance gates remain pending.
