# Owner-machine results 2026-09-30
- Pinned commit: 20086495df7500f1769a532ba6e3c5e585a7a4ee
- GPU / driver: NVIDIA GeForce RTX 3060, 616.56

## A. Tests
- pytest summary line: 1235 passed, 2 warnings in 418.90s (0:06:58)
- failures (ids only): none
- ruff: Found 1 error. scripts\run_gate_b12.py:28:8: F401 [*] `threading` imported but unused

## B. Task 21.1b StyleTTS 2
- env: not created
- run1 handshake: not run
- run1 clips: not run; mp3 present: no
- run1 per-clip wall_time_sec / rtf / duration_sec: not available
- run2 handshake: not run
- errors: `Error: [Errno 13] Permission denied: 'D:\\DataAdmin\\Daily_Intel_English\\venv-styletts2\\Scripts\\python.exe'`
- unavailable evidence: B_env.txt, B_gpu_states.txt, B_run1_idle.json, B_run1_idle.err, B_run2_qwen.json, B_run2_qwen.err, B_run1_worker.log, B_run2_worker.log, spike_comparison_styletts2.mp3

## C. Task 20.2 images (+ 20.1 evidence)
- env: 2.11.0+cu128 12.8 True
- VRAM probe idle: nvidia_smi.free_mib=9748, pynvml.free_mib=9747, torch.free_mib=11250
- VRAM probe qwen_loaded: nvidia_smi.free_mib=3379, pynvml.free_mib=3378, torch.free_mib=11250
- OOM rerun needed: no (the reported error was OS error 1455, not `OutOfMemoryError` or `CUDA out of memory`)
- base: load_sec, watermark_active, per-image wall_time_sec, peak_vram_allocated_mb, peak_vram_reserved_mb, rss_mb: unavailable; C_idle.json is empty
- lightning: load_sec, watermark_active, per-image wall_time_sec, peak_vram_allocated_mb, peak_vram_reserved_mb, rss_mb: unavailable; C_idle.json is empty
- ip_adapter (each candidate): load vram_added_mb, per-scene wall_time_sec and peak_vram_allocated_mb: unavailable; C_idle.json is empty
- lease (each candidate, both runs): min_free_mb, free_mb_before, free_mb_after_eviction, evicted_models, waited_seconds: unavailable; C_idle.json is empty and warm_qwen was not run
- qwen (warm_qwen run): warm wall_sec, reload_after_eviction wall_sec: not run
- gpu_snapshots (warm_qwen run): not run
- errors: `SpikeError: lightning load failed: OSError: The paging file is too small for this operation to complete. (os error 1455)`
- unavailable evidence: C_warm_qwen.json, C_warm_qwen.err, C_idle_vaetiling.json, C_idle_vaetiling.err, sheet_ep1.png through sheet_ep5.png, sheet_ip_adapter.png
- D2 footprint command failed: `An empty pipe element is not allowed.`; sizes.txt was not created

## Owner decisions (LEAVE EMPTY -- the owner fills this in, not the agent)
