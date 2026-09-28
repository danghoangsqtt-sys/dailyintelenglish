"""Build the T6 report's speed benchmark chart from existing Gate B evidence.

Reads real Gate B-8 (local baseline, 2026-09-23) and Gate B-11 (cloud_first,
2026-09-26) evidence JSON. Both were real end-to-end runs of the same B1 8-min
script generation pipeline against the actual Ollama qwen3.5:9b (local) and
Gemini 3.1 Flash-Lite / OpenRouter chain (cloud_first) — nothing mocked, same
topic ("How small daily habits shape long-term health"), same DIE_AI_MODE
enforcement, same 5-run protocol.

Produces:
  - docs/report/benchmark-chart.png (bar chart, 5 runs per mode + median line)
  - docs/report/benchmark-summary.csv (raw numbers for the slide + audit trail)
  - stdout: median/mean/min/max/speedup summary for slide copy-paste

Usage:
    venv\\Scripts\\python scripts\\build_report_benchmark_chart.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

# Force UTF-8 for cp1252 Windows terminals
sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_EVIDENCE = REPO_ROOT / "data/quality_reviews/phase15/gate-b8/gate-b8-20260923T105330Z.json"
CLOUD_EVIDENCE = REPO_ROOT / "data/quality_reviews/phase15/gate-b11/gate-b11-20260926T042435Z.json"
OUTPUT_DIR = REPO_ROOT / "docs/report"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_runs(path: Path) -> list[float]:
    """Return the total_seconds list for the 5 B1 8-min primary runs."""
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = data.get("b1_eight_minute_runs") or []
    return [r["total_seconds"] for r in runs if r.get("total_seconds") is not None]


def stats(runs: list[float]) -> dict[str, float]:
    return {
        "n": len(runs),
        "min": min(runs),
        "median": statistics.median(runs),
        "mean": statistics.mean(runs),
        "max": max(runs),
        "stdev": statistics.stdev(runs) if len(runs) > 1 else 0.0,
    }


def main() -> None:
    local_runs = load_runs(LOCAL_EVIDENCE)
    cloud_runs = load_runs(CLOUD_EVIDENCE)
    local = stats(local_runs)
    cloud = stats(cloud_runs)

    speedup_median = local["median"] / cloud["median"]
    speedup_mean = local["mean"] / cloud["mean"]

    # CSV audit trail
    csv_path = OUTPUT_DIR / "benchmark-summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mode", "run_index", "total_seconds", "source_evidence"])
        for i, s in enumerate(local_runs, 1):
            w.writerow(["local", i, s, LOCAL_EVIDENCE.name])
        for i, s in enumerate(cloud_runs, 1):
            w.writerow(["cloud_first", i, s, CLOUD_EVIDENCE.name])

    # Chart
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[warn] matplotlib not installed; skipping PNG. CSV written to", csv_path)
        _print_summary(local, cloud, speedup_median, speedup_mean)
        return

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x_local = [i - 0.18 for i in range(1, 6)]
    x_cloud = [i + 0.18 for i in range(1, 6)]

    bars_local = ax.bar(x_local, local_runs, width=0.34, color="#EF4444",
                        label=f"Local (qwen3.5:9b, RTX 3060) — median {local['median']:.1f}s")
    bars_cloud = ax.bar(x_cloud, cloud_runs, width=0.34, color="#22C55E",
                        label=f"Cloud-first (Gemini→OpenRouter→local) — median {cloud['median']:.1f}s")

    # Median reference lines
    ax.axhline(local["median"], color="#EF4444", linestyle=":", linewidth=1, alpha=0.5)
    ax.axhline(cloud["median"], color="#22C55E", linestyle=":", linewidth=1, alpha=0.5)

    # Value labels on top of each bar
    for bar in list(bars_local) + list(bars_cloud):
        h = bar.get_height()
        ax.annotate(f"{h:.0f}s", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(range(1, 6)))
    ax.set_xticklabels([f"Run {i}" for i in range(1, 6)])
    ax.set_ylabel("Script generation wall time (seconds)")
    ax.set_title(f"Daily Intel English — AI script speed: {speedup_median:.2f}× faster with cloud-first\n"
                 f"5 real end-to-end runs per mode · same B1 8-min topic · nothing mocked")
    ax.set_ylim(0, max(max(local_runs), max(cloud_runs)) * 1.15)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    ax.grid(axis="y", alpha=0.25)

    footer = (f"Source: Gate B-8 local baseline (2026-09-23) + Gate B-11 cloud-first (2026-09-26). "
              f"Topic: 'How small daily habits shape long-term health'. "
              f"Local: Ollama qwen3.5:9b on RTX 3060. "
              f"Cloud chain: Gemini 3.1 Flash-Lite → Gemini Flash-Lite latest → OpenRouter (Nemotron/Gemma/Dots3) → local qwen fallback.")
    fig.text(0.5, -0.02, footer, ha="center", va="top", fontsize=7, color="#666")

    png_path = OUTPUT_DIR / "benchmark-chart.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"[ok] chart: {png_path}")
    print(f"[ok] csv:   {csv_path}")
    _print_summary(local, cloud, speedup_median, speedup_mean)


def _print_summary(local: dict, cloud: dict, spd_med: float, spd_mean: float) -> None:
    print()
    print("=== Speed benchmark summary (for slide copy-paste) ===")
    print()
    print("Local (Gate B-8, 2026-09-23, qwen3.5:9b on RTX 3060):")
    print(f"  n={local['n']}  min={local['min']:.1f}s  median={local['median']:.1f}s"
          f"  mean={local['mean']:.1f}s  max={local['max']:.1f}s  stdev={local['stdev']:.1f}s")
    print()
    print("Cloud-first (Gate B-11, 2026-09-26, Gemini→OpenRouter→qwen fallback):")
    print(f"  n={cloud['n']}  min={cloud['min']:.1f}s  median={cloud['median']:.1f}s"
          f"  mean={cloud['mean']:.1f}s  max={cloud['max']:.1f}s  stdev={cloud['stdev']:.1f}s")
    print()
    print(f"Speed-up: {spd_med:.2f}x median, {spd_mean:.2f}x mean")
    print(f"Best cloud run ({cloud['min']:.1f}s) vs. worst local run ({local['max']:.1f}s): "
          f"{local['max']/cloud['min']:.2f}x")


if __name__ == "__main__":
    main()
