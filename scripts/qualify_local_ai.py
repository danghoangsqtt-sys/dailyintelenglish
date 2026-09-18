"""Qualify a loopback Ollama model for Phase 13 Gate A.

This is an operational runner, not a pytest. It calls the real Ollama HTTP API,
validates three nested structured responses, samples GPU/RAM use, probes failure and
cancellation behavior, unloads the model, and writes redacted JSON evidence under the
already-gitignored ``data/quality_reviews`` tree.

Usage:
    venv\\Scripts\\python.exe scripts\\qualify_local_ai.py
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "quality_reviews" / "phase13" / "gate-a"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
EXPECTED_SCHEMA_RUNS = 3
MIN_FREE_VRAM_MIB = 1536
MIN_FREE_RAM_MIB = 4096


class OutlineSection(BaseModel):
    """One nested section used to exercise real schema-constrained generation."""

    index: int = Field(ge=1, le=2)
    objective: str = Field(min_length=8)
    target_words: int = Field(ge=40, le=200)
    speakers: list[str] = Field(min_length=2, max_length=2)


class EpisodeOutline(BaseModel):
    """Small but nested output representative of the Phase 13 outline stage."""

    title: str = Field(min_length=5)
    sections: list[OutlineSection] = Field(min_length=2, max_length=2)


class MemoryStatusEx(ctypes.Structure):
    """Windows MEMORYSTATUSEX structure used without adding psutil."""

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def parse_args() -> argparse.Namespace:
    """Parse operational-run options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--num-ctx", type=int, default=16_384)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def validate_loopback_url(base_url: str) -> str:
    """Reject credentials, non-HTTP schemes, paths, and non-loopback hosts."""
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError("Ollama URL must use HTTP on a loopback host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Ollama URL cannot contain credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("Ollama base URL cannot contain a path")
    if parsed.port is None:
        raise ValueError("Ollama base URL must include an explicit port")
    return base_url.rstrip("/")


def run_command(command: list[str], timeout: float = 30.0) -> str:
    """Run a read-only diagnostic command and return normalized stdout."""
    completed = subprocess.run(
        command,
        capture_output=True,
        check=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def gpu_sample() -> dict[str, Any]:
    """Read the first NVIDIA GPU's stable identification and memory counters."""
    output = run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ]
    )
    parts = [part.strip() for part in output.splitlines()[0].split(",")]
    if len(parts) != 5:
        raise RuntimeError(f"Unexpected nvidia-smi output field count: {len(parts)}")
    return {
        "name": parts[0],
        "driver_version": parts[1],
        "memory_total_mib": int(parts[2]),
        "memory_used_mib": int(parts[3]),
        "memory_free_mib": int(parts[4]),
    }


def free_ram_mib() -> int:
    """Return available physical RAM in MiB on Windows."""
    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return int(status.ullAvailPhys / (1024 * 1024))


def listener_rows(port: int) -> list[dict[str, Any]]:
    """Inspect Windows TCP listeners without changing firewall/network state."""
    script = (
        f"$rows=Get-NetTCPConnection -State Listen -LocalPort {port} "
        "-ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess; "
        "if ($rows) {$rows | ConvertTo-Json -Compress} else {'[]'}"
    )
    raw = run_command(["powershell", "-NoProfile", "-Command", script])
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return [parsed]
    return parsed


async def sample_resources(stop: asyncio.Event, samples: list[dict[str, Any]]) -> None:
    """Poll GPU and available RAM once per second during real inference."""
    while not stop.is_set():
        try:
            samples.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "gpu": await asyncio.to_thread(gpu_sample),
                    "free_ram_mib": free_ram_mib(),
                }
            )
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            samples.append({"sample_error": type(exc).__name__})
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except TimeoutError:
            pass


def find_model(tags: dict[str, Any], requested: str) -> dict[str, Any]:
    """Find the exact requested tag in Ollama's local model inventory."""
    for model in tags.get("models", []):
        names = {str(model.get("name", "")), str(model.get("model", ""))}
        if requested in names:
            return model
    raise RuntimeError(f"Required local model is missing: {requested}")


def duration_seconds(value: Any) -> float | None:
    """Convert an Ollama nanosecond metric to rounded seconds."""
    if not isinstance(value, int):
        return None
    return round(value / 1_000_000_000, 3)


async def structured_run(
    client: httpx.AsyncClient,
    model: str,
    num_ctx: int,
    run_number: int,
) -> dict[str, Any]:
    """Run and validate one real nested JSON Schema request."""
    prompt = (
        "Create a two-section B1 English interview outline about remote work and city "
        "life. Use both speakers Alex and Maya in every section. Keep the result concise "
        "and follow the supplied JSON schema exactly."
    )
    started = time.perf_counter()
    response = await client.post(
        "/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": EpisodeOutline.model_json_schema(),
            "options": {"num_ctx": num_ctx, "temperature": 0},
            "keep_alive": "5m",
        },
    )
    response.raise_for_status()
    payload = response.json()
    parsed = EpisodeOutline.model_validate_json(payload["response"])
    indexes = [section.index for section in parsed.sections]
    if indexes != [1, 2]:
        raise ValueError(f"section indexes must be [1, 2], got {indexes}")
    if any(set(section.speakers) != {"Alex", "Maya"} for section in parsed.sections):
        raise ValueError("each schema probe section must contain Alex and Maya")
    eval_count = payload.get("eval_count")
    eval_duration = payload.get("eval_duration")
    tokens_per_second = None
    if isinstance(eval_count, int) and isinstance(eval_duration, int) and eval_duration > 0:
        tokens_per_second = round(eval_count / (eval_duration / 1_000_000_000), 3)
    return {
        "run": run_number,
        "schema_valid": True,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "total_seconds": duration_seconds(payload.get("total_duration")),
        "load_seconds": duration_seconds(payload.get("load_duration")),
        "prompt_eval_count": payload.get("prompt_eval_count"),
        "eval_count": eval_count,
        "tokens_per_second": tokens_per_second,
        "done": payload.get("done"),
        "done_reason": payload.get("done_reason"),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


async def probe_missing_model(client: httpx.AsyncClient, num_ctx: int) -> dict[str, Any]:
    """Confirm a nonexistent tag returns a recognizable non-success response."""
    response = await client.post(
        "/api/generate",
        json={
            "model": "phase13-model-that-does-not-exist:invalid",
            "prompt": "health probe",
            "stream": False,
            "options": {"num_ctx": num_ctx},
        },
    )
    return {"status_code": response.status_code, "detected": response.status_code >= 400}


async def probe_closed_port() -> dict[str, Any]:
    """Confirm connection failure is bounded on a known-unused loopback port."""
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:11435", timeout=2.0) as client:
            await client.get("/api/version")
    except httpx.HTTPError as exc:
        return {
            "detected": True,
            "error_type": type(exc).__name__,
            "wall_seconds": round(time.perf_counter() - started, 3),
        }
    return {"detected": False, "wall_seconds": round(time.perf_counter() - started, 3)}


async def probe_stream_close(
    client: httpx.AsyncClient, model: str, num_ctx: int
) -> dict[str, Any]:
    """Close a real streaming generation early and verify the server stays healthy."""
    started = time.perf_counter()
    received = False
    async with client.stream(
        "POST",
        "/api/generate",
        json={
            "model": model,
            "prompt": "Write a long numbered discussion of one hundred city policy ideas.",
            "stream": True,
            "think": False,
            "options": {"num_ctx": num_ctx, "temperature": 0.2},
            "keep_alive": "5m",
        },
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line:
                received = True
                break
    await asyncio.sleep(1.0)
    health = await client.get("/api/version")
    return {
        "stream_chunk_received": received,
        "connection_closed_early": True,
        "server_healthy_after_close": health.is_success,
        "wall_seconds": round(time.perf_counter() - started, 3),
    }


async def unload_model(client: httpx.AsyncClient, model: str) -> dict[str, Any]:
    """Ask Ollama to unload the model immediately and capture the resulting ps output."""
    response = await client.post(
        "/api/generate",
        json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
    )
    response.raise_for_status()
    await asyncio.sleep(1.0)
    ps_output = await asyncio.to_thread(run_command, ["ollama", "ps"])
    return {"requested": True, "ollama_ps": ps_output}


async def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the full real Gate A qualification sequence."""
    base_url = validate_loopback_url(args.base_url)
    parsed = urlparse(base_url)
    listeners = listener_rows(parsed.port or 11434)
    listener_addresses = {str(row.get("LocalAddress")) for row in listeners}
    listener_loopback_only = bool(listeners) and listener_addresses <= {"127.0.0.1", "::1"}
    if not listener_loopback_only:
        raise RuntimeError(f"Ollama listener is absent or not loopback-only: {sorted(listener_addresses)}")

    baseline_gpu = gpu_sample()
    baseline_ram = free_ram_mib()
    resource_samples: list[dict[str, Any]] = []
    stop_sampling = asyncio.Event()
    sampler = asyncio.create_task(sample_resources(stop_sampling, resource_samples))
    try:
        timeout = httpx.Timeout(args.timeout, connect=10.0)
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            version_response = await client.get("/api/version")
            version_response.raise_for_status()
            version = version_response.json().get("version")
            tags_response = await client.get("/api/tags")
            tags_response.raise_for_status()
            local_model = find_model(tags_response.json(), args.model)
            await unload_model(client, args.model)
            runs = [
                await structured_run(client, args.model, args.num_ctx, run_number)
                for run_number in range(1, EXPECTED_SCHEMA_RUNS + 1)
            ]
            ps_loaded = await asyncio.to_thread(run_command, ["ollama", "ps"])
            missing_model = await probe_missing_model(client, args.num_ctx)
            stream_close = await probe_stream_close(client, args.model, args.num_ctx)
            closed_port = await probe_closed_port()
            unload = await unload_model(client, args.model)
    finally:
        stop_sampling.set()
        await sampler

    valid_samples = [sample for sample in resource_samples if "gpu" in sample]
    if not valid_samples:
        raise RuntimeError("No valid GPU/RAM samples were captured")
    peak_vram_used = max(sample["gpu"]["memory_used_mib"] for sample in valid_samples)
    minimum_free_vram = min(sample["gpu"]["memory_free_mib"] for sample in valid_samples)
    minimum_free_ram = min(sample["free_ram_mib"] for sample in valid_samples)
    schema_passes = sum(bool(run["schema_valid"]) for run in runs)
    full_gpu = "100% GPU" in ps_loaded
    gate_checks = {
        "listener_loopback_only": listener_loopback_only,
        "schema_runs_3_of_3": schema_passes == EXPECTED_SCHEMA_RUNS,
        "full_gpu_offload": full_gpu,
        "free_vram_at_least_1536_mib": minimum_free_vram >= MIN_FREE_VRAM_MIB,
        "free_ram_at_least_4096_mib": minimum_free_ram >= MIN_FREE_RAM_MIB,
        "model_missing_detected": bool(missing_model["detected"]),
        "server_down_detected": bool(closed_port["detected"]),
        "stream_close_detected": bool(stream_close["stream_chunk_received"])
        and bool(stream_close["server_healthy_after_close"]),
        "model_unloaded": args.model not in unload["ollama_ps"],
    }
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "platform": {"system": platform.system(), "release": platform.release()},
        "configuration": {
            "base_url": base_url,
            "model": args.model,
            "num_ctx": args.num_ctx,
            "max_loaded_models": os.environ.get("OLLAMA_MAX_LOADED_MODELS"),
            "num_parallel": os.environ.get("OLLAMA_NUM_PARALLEL"),
            "max_queue": os.environ.get("OLLAMA_MAX_QUEUE"),
            "no_cloud": os.environ.get("OLLAMA_NO_CLOUD"),
        },
        "runtime": {
            "ollama_api_version": version,
            "model_name": local_model.get("name") or local_model.get("model"),
            "model_digest": local_model.get("digest"),
            "model_size_bytes": local_model.get("size"),
            "model_details": local_model.get("details", {}),
            "listeners": listeners,
        },
        "resources": {
            "baseline_gpu": baseline_gpu,
            "baseline_free_ram_mib": baseline_ram,
            "peak_vram_used_mib": peak_vram_used,
            "minimum_free_vram_mib": minimum_free_vram,
            "minimum_free_ram_mib": minimum_free_ram,
            "sample_count": len(valid_samples),
            "ollama_ps_loaded": ps_loaded,
        },
        "structured_runs": runs,
        "failure_probes": {
            "missing_model": missing_model,
            "closed_port": closed_port,
            "stream_close": stream_close,
        },
        "unload": unload,
        "gate_checks": gate_checks,
        "gate_a_pass": all(gate_checks.values()),
    }


async def async_main() -> int:
    """Run qualification, persist redacted evidence, and return gate status."""
    args = parse_args()
    evidence = await qualify(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = args.output_dir / f"ollama-{timestamp}.json"
    output_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Gate A pass: {evidence['gate_a_pass']}")
    print(f"Evidence: {output_path}")
    print(json.dumps(evidence["gate_checks"], indent=2, sort_keys=True))
    return 0 if evidence["gate_a_pass"] else 1


def main() -> int:
    """Synchronous entry point."""
    if sys.platform != "win32":
        raise RuntimeError("Gate A runner currently targets the supported Windows workstation")
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
