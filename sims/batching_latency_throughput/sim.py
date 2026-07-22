#!/usr/bin/env python3
"""
Batching window vs. throughput and p99 latency tradeoff.

Shows how increasing the dynamic batching window improves throughput
(larger batches, better GPU utilization) at the direct cost of added
per-request latency.

Usage:
    python sim.py --out ../../src/figures/batching_latency_throughput

Output:
    batching_latency_throughput.svg — throughput and p99 latency vs. batch window
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Batching latency/throughput tradeoff")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/batching_latency_throughput"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    batch_window_ms = np.linspace(0, 100, 400)

    # Throughput rises with batching window as more requests get batched
    # together, with diminishing returns as batches approach a max size cap.
    max_throughput = 100.0
    throughput = max_throughput * (1 - np.exp(-batch_window_ms / 25))

    # p99 latency = base inference time + up to the full batch window (worst
    # case: a request arrives right after the window starts accumulating).
    base_latency_ms = 15.0
    p99_latency = base_latency_ms + batch_window_ms

    fig, ax1 = plt.subplots()

    ax1.plot(batch_window_ms, throughput, color="#0072B2", linewidth=2.2,
             label="Throughput (relative)")
    ax1.set_xlabel("Batching Window (ms)")
    ax1.set_ylabel("Throughput (% of max)", color="#0072B2")
    ax1.tick_params(axis="y", labelcolor="#0072B2")
    ax1.set_ylim(0, 105)

    ax2 = ax1.twinx()
    ax2.plot(batch_window_ms, p99_latency, color="#D55E00", linewidth=2.2,
             linestyle="--", label="p99 latency (ms)")
    ax2.set_ylabel("p99 Latency (ms)", color="#D55E00")
    ax2.tick_params(axis="y", labelcolor="#D55E00")
    ax2.grid(False)

    op_idx = np.searchsorted(batch_window_ms, 25)
    ax1.axvline(25, color="gray", linestyle=":", linewidth=1.0)
    ax1.annotate(
        f"At 25ms window:\n{throughput[op_idx]:.0f}% throughput,\n{p99_latency[op_idx]:.0f}ms p99",
        xy=(25, throughput[op_idx]), xytext=(38, 45),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax1.set_title("Batching Window: Throughput Gain vs. Latency Cost")
    fig.tight_layout()

    out_path = args.out / "batching_latency_throughput.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
