#!/usr/bin/env python3
"""
Cost vs. p99 latency tradeoff as a function of warm pool size.

Shows how increasing minimum warm replica count reduces p99 latency
(fewer requests hit a cold start) at directly increasing continuous cost.

Usage:
    python sim.py --out ../../src/figures/cold_start_vs_warm_pool_cost

Output:
    cold_start_vs_warm_pool_cost.svg — cost and p99 latency vs. warm pool size
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Cold start vs warm pool cost")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/cold_start_vs_warm_pool_cost"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    warm_replicas = np.arange(0, 21)

    # Cost grows linearly with warm replica count (each replica costs the
    # same, whether serving traffic or sitting idle-but-ready).
    cost_per_replica = 5.0
    cost = warm_replicas * cost_per_replica

    # p99 latency: with zero warm replicas, essentially every request that
    # arrives after an idle period pays full cold-start cost. As warm
    # replicas increase, the probability any given request needs a fresh
    # cold start drops sharply (assuming Poisson-ish bursty arrival that a
    # given warm pool size can usually absorb).
    cold_start_ms = 90000  # ~90 seconds
    warm_latency_ms = 40
    # Probability of exhausting warm pool given typical burst size ~ decays
    # exponentially with warm pool size relative to typical burst.
    typical_burst = 4.0
    p_cold_start = np.exp(-warm_replicas / typical_burst)
    p99_latency = warm_latency_ms + p_cold_start * cold_start_ms

    fig, ax1 = plt.subplots()

    ax1.plot(warm_replicas, cost, color="#0072B2", linewidth=2.2, marker="o",
             label="Ongoing cost (relative)")
    ax1.set_xlabel("Minimum Warm Replica Count")
    ax1.set_ylabel("Ongoing Cost (relative)", color="#0072B2")
    ax1.tick_params(axis="y", labelcolor="#0072B2")

    ax2 = ax1.twinx()
    ax2.plot(warm_replicas, p99_latency / 1000, color="#D55E00", linewidth=2.2,
             linestyle="--", marker="o", label="p99 latency (seconds)")
    ax2.set_ylabel("p99 Latency (seconds, log-like scale)", color="#D55E00")
    ax2.tick_params(axis="y", labelcolor="#D55E00")
    ax2.set_yscale("log")
    ax2.grid(False)

    ax1.annotate(
        "Zero warm replicas:\nrare requests pay a\n~90 second cold start",
        xy=(0, cost[0]), xytext=(4, cost.max() * 0.6),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )
    ax1.annotate(
        "A handful of warm replicas\nabsorbs most bursts",
        xy=(8, cost[8]), xytext=(10, cost.max() * 0.25),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax1.set_title("Warm Pool Size: Cost vs. p99 Latency Tradeoff")
    fig.tight_layout()

    out_path = args.out / "cold_start_vs_warm_pool_cost.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
