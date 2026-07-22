#!/usr/bin/env python3
"""
GPU utilization vs. data-loading prefetch/overlap depth.

Shows how GPU utilization rises as prefetch depth (number of batches
prepared ahead of consumption) increases, until data-loading throughput
itself becomes the limiting factor rather than prefetch depth.

Usage:
    python sim.py --out ../../src/figures/data_loading_gpu_utilization

Output:
    data_loading_gpu_utilization.svg — GPU utilization vs. prefetch depth
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Data loading GPU utilization")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/data_loading_gpu_utilization"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    prefetch_depth = np.arange(0, 17)

    # Fast data pipeline: utilization rises quickly and plateaus near 100%
    # once prefetch depth is enough to hide preparation latency.
    fast_pipeline_util = 100 * (1 - np.exp(-prefetch_depth / 1.5))
    fast_pipeline_util = np.clip(fast_pipeline_util, 0, 97)

    # Slow data pipeline (e.g. CPU video decode, no caching): even with deep
    # prefetch, throughput itself is capped, so utilization plateaus much lower.
    slow_pipeline_util = 100 * (1 - np.exp(-prefetch_depth / 1.5))
    slow_pipeline_util = np.clip(slow_pipeline_util, 0, 45)

    fig, ax = plt.subplots()

    ax.plot(prefetch_depth, fast_pipeline_util, color="#0072B2", marker="o",
            label="Fast pipeline (sharded, GPU decode, NVMe cache)")
    ax.plot(prefetch_depth, slow_pipeline_util, color="#D55E00", marker="o",
            label="Slow pipeline (small files, CPU decode, no cache)")

    ax.annotate(
        "More prefetch depth can't fix a\nthroughput-limited pipeline",
        xy=(10, slow_pipeline_util[10]), xytext=(6, 15),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )
    ax.annotate(
        "Fast pipeline: overlap\nhides prep behind compute",
        xy=(4, fast_pipeline_util[4]), xytext=(5.5, 60),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Prefetch Depth (batches prepared ahead)")
    ax.set_ylabel("GPU Utilization (%)")
    ax.set_title("GPU Utilization vs. Data-Loading Prefetch Depth")
    ax.set_ylim(0, 100)
    ax.legend(loc="center right", fontsize=9)

    out_path = args.out / "data_loading_gpu_utilization.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
