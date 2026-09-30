"""Task 20.1 (PM card D20.1-a) -- three-way free-VRAM probe on the owner's GPU.

The PM card asks for a real side-by-side comparison of three ways to read free VRAM,
taken while Ollama's qwen is loaded **in a separate process**:
- `nvidia-smi` (what `app/core/system_checks.get_gpu_memory` uses);
- `torch.cuda.mem_get_info()`;
- pynvml (`nvidia-ml-py`).
The question it decides is whether each method sees memory held by *another* process.

Runs in `venv-image/`, which already has CUDA torch. The runbook installs `nvidia-ml-py`
there just for this probe; the main app gains no dependency. Prints one JSON object.
A method that is unavailable reports its error instead of failing the whole probe.

    venv-image\\Scripts\\python scripts\\probe_vram.py --label idle
    venv-image\\Scripts\\python scripts\\probe_vram.py --label qwen_loaded
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

MIB = 1024 * 1024


def _nvidia_smi() -> dict[str, Any]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.splitlines()[0]
        used, free, total = (int(v.strip()) for v in out.split(","))
        return {"used_mib": used, "free_mib": free, "total_mib": total}
    except Exception as exc:  # noqa: BLE001 -- report, never abort the probe
        return {"error": f"{type(exc).__name__}: {exc}"}


def _torch() -> dict[str, Any]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"error": "torch.cuda.is_available() is False", "torch": torch.__version__}
        free, total = torch.cuda.mem_get_info()
        # Creating the CUDA context itself costs VRAM; that is reported so the reader can
        # tell "seen as used" from "used by this probe".
        return {"free_mib": free // MIB, "total_mib": total // MIB, "torch": torch.__version__,
                "this_process_reserved_mib": torch.cuda.memory_reserved() // MIB}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def _pynvml() -> dict[str, Any]:
    try:
        import pynvml

        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            processes = []
            for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle):
                used = getattr(proc, "usedGpuMemory", None)
                processes.append({"pid": proc.pid, "used_mib": (used // MIB) if isinstance(used, int) else None})
            return {"used_mib": info.used // MIB, "free_mib": info.free // MIB, "total_mib": info.total // MIB,
                    "compute_processes": processes}
        finally:
            pynvml.nvmlShutdown()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Three-way free-VRAM probe (Task 20.1 D20.1-a)")
    parser.add_argument("--label", required=True, help="e.g. idle / qwen_loaded")
    args = parser.parse_args(argv)
    # nvidia-smi and pynvml are read BEFORE torch creates a CUDA context in this process,
    # then nvidia-smi once more after, so the probe's own context cost is visible.
    report = {"label": args.label, "nvidia_smi": _nvidia_smi(), "pynvml": _pynvml(), "torch": _torch()}
    report["nvidia_smi_after_torch_context"] = _nvidia_smi()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
