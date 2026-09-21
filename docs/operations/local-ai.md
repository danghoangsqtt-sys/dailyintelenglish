# Local AI Runtime Operations — Ollama / Qwen (Phase 13)

This document covers the local inference runtime that Phase 13 (Local-First AI
Reliability) qualifies as a candidate primary provider for script and learning
generation. The controlling contract is
`docs/implementation/phase-13-local-first-ai-reliability.md`; the architecture
decision is `docs/architecture/adr-001-local-first-ai.md`.

## 1. Install / version / model location

- **Runtime:** official Ollama for Windows, installed via `winget install Ollama.Ollama`.
- **Installed version (verified live):** `0.34.2`.
- **Binary path:** `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`
  (`C:\Users\<user>\AppData\Local\Programs\Ollama\ollama.exe`). A freshly-installed
  winget package updates the User `PATH` registry value, but any shell already running
  at install time keeps its own process environment block and will not see the update
  until it restarts — resolve the exact binary path (or restart the shell) rather than
  treating `ollama: command not found` as "not installed."
- **Model:** `qwen3.5:9b`
  - Digest (verified after pull): `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
  - Size: 6,594,474,711 bytes (6.6 GB)
  - Quantization: `Q4_K_M`
  - Parameters: 9.7B, architecture `qwen35`, native context length 262,144 (Phase 13
    uses 16,384 — see §2)
- **Model storage directory:** `D:\DataAdmin\OllamaModels` (set via `OLLAMA_MODELS`,
  off the system drive by design).

## 2. Loopback / cloud-disabled / concurrency configuration

Persisted as **User**-scope Windows environment variables (`setx`, not `Process`-scope —
a shell already running when they are set will not see them until restarted; read them
via `[Environment]::GetEnvironmentVariable(name, 'User')` if you need to confirm them
from a long-lived shell without restarting it):

| Variable | Value | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `127.0.0.1:11434` | Bind loopback only — never `0.0.0.0` or a LAN address |
| `OLLAMA_MODELS` | `D:\DataAdmin\OllamaModels` | Model weight storage location |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | One model resident at a time (12 GB VRAM budget) |
| `OLLAMA_NUM_PARALLEL` | `1` | One concurrent generation, matching Phase 13's single-worker job design |
| `OLLAMA_MAX_QUEUE` | `4` | Bounded request queue, no unbounded backlog |
| `OLLAMA_NO_CLOUD` | `1` | Disables Ollama's own cloud relay; all inference stays on this machine |

Confirmed live evidence (Gate A run, 2026-09-18T23:31Z):

- Windows listener: `127.0.0.1:11434` only (`Get-NetTCPConnection -State Listen`),
  never a `0.0.0.0`/LAN address.
- Server log lines: `OLLAMA_NO_CLOUD:true`, `Ollama cloud disabled: true`,
  `Listening on 127.0.0.1:11434 (version 0.34.2)`.
- The application's own `qualify_local_ai.py` runner additionally rejects any
  non-loopback, non-HTTP, credentialed, or pathed base URL before issuing a single
  request (`validate_loopback_url`) — this is the same rule Phase 13's gateway
  enforces for the product code, not just this diagnostic script.

The port is never opened in Windows Firewall for inbound LAN access, and no reverse
proxy/tunnel/CORS origin is configured — loopback-only is enforced at the OS listener
level, not only by application-side URL validation.

## 3. Start / restart / health / pull / update / unload / uninstall

All commands below use the resolved binary path in case the current shell's `PATH`
predates installation:

```powershell
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

# Start (winget installs Ollama as a Windows service/tray app that starts automatically;
# this starts it manually if it is not already running)
& $ollama serve

# Health / version
Invoke-RestMethod http://127.0.0.1:11434/api/version
& $ollama list
& $ollama ps

# Pull / re-pull the qualified model (about 6.6 GB)
& $ollama pull qwen3.5:9b

# Inspect the exact local digest/quantization/size after any pull
& $ollama show qwen3.5:9b

# Unload the model immediately (frees VRAM without stopping the server)
Invoke-RestMethod -Method Post http://127.0.0.1:11434/api/generate `
  -Body (@{ model = "qwen3.5:9b"; prompt = ""; stream = $false; keep_alive = 0 } | ConvertTo-Json) `
  -ContentType "application/json"

# Restart the server (Task Manager / Services, or restart the tray app)
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
& $ollama serve

# Update (winget re-runs the same official installer)
winget upgrade Ollama.Ollama

# Uninstall
winget uninstall Ollama.Ollama
# Model weights under OLLAMA_MODELS are not removed by uninstall; delete
# D:\DataAdmin\OllamaModels manually if reclaiming disk space is required.
```

`GET /api/ai/health` (application endpoint, Task 13.6; payload revised in Task 14.7)
reports AI mode, Ollama reachability, model presence/digest, and `cloud_enabled`
(always `false` unless `DIE_AI_ALLOW_CLOUD=true`) to the app itself — it never exposes
any key, and its absence never fails application startup. Since Phase 14 (ADR-001 A2)
**Ollama is the only supported AI runtime**: the app still starts without it, but Step 2
(script) and Step 3 (learning) disable their generate buttons and show install/pull
guidance until `ollama_reachable` and `model_present` are both true.

## 4. Runtime auto-update / digest-change requalification

Ollama for Windows can auto-update. Because Gate A qualifies one exact runtime version
and one exact model digest, **any observed change to either value invalidates the Gate A
result and requires requalification**, not just noting the change:

- Compare `ollama --version` / `/api/version` against the digest recorded in this
  document and in the Gate A evidence file before trusting local mode after any
  Windows or Ollama update.
- Compare `ollama show qwen3.5:9b`'s digest against
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`. A different
  digest (including a silent upstream re-tag of `qwen3.5:9b`) means re-run
  `scripts\qualify_local_ai.py` before relying on the result again.
- The application should treat a runtime/digest mismatch as a health warning, not a
  silent pass-through (Task 13.6 surfaces this in Settings/health).

## 5. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `ollama: command not found` in a shell | Shell's `PATH` predates install | Use the exact binary path above, or open a new shell |
| `GET /api/version` connection refused | Ollama not running | `& $ollama serve`, or check Task Manager for a stuck process holding port 11434 |
| `ollama list` / `ollama show` reports the model missing | Model was never pulled, or `OLLAMA_MODELS` points elsewhere | `& $ollama pull qwen3.5:9b`; confirm `OLLAMA_MODELS` with `[Environment]::GetEnvironmentVariable('OLLAMA_MODELS','User')` |
| `ollama ps` does not show `100% GPU` | Driver too old, VRAM already consumed by another process, or model too large for free VRAM | Confirm driver ≥ Ollama's documented Windows minimum (551.61; this machine runs 616.56); close other GPU workloads; do not fall back to CPU offload silently — treat as a Gate A regression |
| Generation succeeds but VRAM/RAM headroom is thin | Concurrent GPU load from another app, or a longer context in use | Re-run `qualify_local_ai.py`; if only headroom fails, apply the plan's ordered mitigations in order and record each: (1) reduce context to 8192, (2) enable Flash Attention if the installed build supports it, (3) switch KV cache to `q8_0`. Never silently drop to `q4` KV cache or a different model. |
| App starts but Step 2/3 show "Ollama not reachable / model missing" guidance | Ollama stopped, model not pulled, or `OLLAMA_MODELS` pointing at an empty directory | Start Ollama with the full environment from §2 and confirm `/api/tags` shows digest `6488c96fa5fa…`; there is no cloud fallback since Phase 14 (ADR-001 A2). Re-enabling the dormant Gemini path requires `DIE_AI_ALLOW_CLOUD=true`, `DIE_AI_MODE=hybrid` or `gemini` and a key, and is unsupported |

## 6. Privacy

- With `OLLAMA_NO_CLOUD=1` and a loopback-only listener, prompts sent to the local
  `qwen3.5:9b` model never leave this machine and never reach Ollama's own cloud
  relay service.
- Since Phase 14 (owner decision D9, ADR-001 A2) no prompt or generated content leaves
  this machine: the Gemini cloud path is dormant and cannot be selected unless
  `DIE_AI_ALLOW_CLOUD=true` is set explicitly. If it ever is, that path is a **cloud**
  flow (prompt and content sent to Google's Gemini API) and the job records make it
  visible (`fallback_used`, `fallback_count`) rather than silent.
- Ollama requires no API key for local use. A Gemini key, if one is still stored from
  Phase 13, stays masked in the settings API and is no longer exposed in the UI.

## 7. Gate A evidence and decision

**Decision: Gate A PASS** (2026-09-18T23:31:06Z UTC). Evidence file:
`data/quality_reviews/phase13/gate-a/ollama-20260918T233107Z.json` (gitignored local
evidence, not committed — contains no secrets, but is operational-run output rather
than a tracked fixture).

| Check | Result |
|---|---|
| Listener loopback-only | ✅ `127.0.0.1:11434` only |
| Nested JSON Schema probes | ✅ 3/3 valid |
| `ollama ps` GPU offload | ✅ `100% GPU`, model `qwen3.5:9b`, digest `6488c96fa5fa`, context 16384 |
| Free VRAM at 16K steady state | ✅ minimum observed 4,370 MiB free (≥ 1,536 MiB required); peak used 7,741 MiB of 12,288 MiB total |
| Free system RAM | ✅ minimum observed 17,504 MiB free (≥ 4,096 MiB required) |
| OOM / TDR / OS-GPU instability | ✅ none observed across 75 one-second resource samples |
| Cold request | ✅ succeeds; 33.41 s load + generation, schema-valid |
| Warm requests (×2) | ✅ succeed; ~6.3 s each, schema-valid, ~48.2 tokens/sec steady state |
| Model-missing detection | ✅ HTTP 404 on an invalid tag |
| Server-down detection | ✅ `ConnectTimeout` on a known-closed loopback port, bounded at 2.0 s |
| Early stream close / cancel | ✅ chunk received, connection closed client-side, server confirmed healthy afterward via `/api/version` |
| Unload | ✅ `ollama ps` empty after a `keep_alive: 0` request |

No memory-headroom mitigation (8K context / Flash Attention / `q8_0` KV cache) was
required — Gate A passed cleanly at the plan's default 16K context and one concurrent
generation on the RTX 3060 12 GB. Driver 616.56 exceeds Ollama's documented Windows
minimum (551.61).

Baseline hardware at capture time: RTX 3060, 12,288 MiB total VRAM, 11,237 MiB free
before load; 18,989 MiB system RAM free before load.

This PASS clears Task 13.1 / Gate A only. Local-primary status is still gated on Gate B
(Task 13.9) — five consecutive real eight-minute script jobs plus one complete real
Edge TTS → audio → ffmpeg video trial — per
`docs/implementation/phase-13-local-first-ai-reliability.md` §8/§9. A Gate A pass never
substitutes for Gate B evidence.
