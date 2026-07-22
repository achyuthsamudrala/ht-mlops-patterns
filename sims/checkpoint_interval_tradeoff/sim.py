#!/usr/bin/env python3
"""
Young-Daly optimal checkpoint interval: overhead vs. expected lost work.

Shows total effective cost (checkpoint overhead + expected lost work from
failure) as a function of checkpoint interval, for a given checkpoint cost
and system MTBF, with the Young-Daly optimal interval marked.

Usage:
    python sim.py --out ../../src/figures/checkpoint_interval_tradeoff

Output:
    checkpoint_interval_tradeoff.svg — total cost vs. checkpoint interval
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Checkpoint interval tradeoff")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/checkpoint_interval_tradeoff"))
    parser.add_argument("--checkpoint-cost-min", type=float, default=5.0, help="delta, in minutes")
    parser.add_argument("--mtbf-hours", type=float, default=12.5, help="M, in hours")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    delta_min = args.checkpoint_cost_min
    M_hours = args.mtbf_hours
    M_min = M_hours * 60

    tau = np.linspace(1, 300, 600)  # checkpoint interval, minutes

    # Overhead fraction of time spent checkpointing: delta / (tau + delta)
    overhead_fraction = delta_min / (tau + delta_min)

    # Expected lost work per interval ~ tau/2 (average progress lost on
    # failure within an interval), amortized over the interval's own MTBF risk:
    # expected lost-work fraction ~ tau / (2 * M)
    lost_work_fraction = tau / (2 * M_min)

    total_cost_fraction = overhead_fraction + lost_work_fraction

    # Young-Daly optimal interval: sqrt(2 * delta * M)
    tau_opt = np.sqrt(2 * delta_min * M_min)

    fig, ax = plt.subplots()

    ax.plot(tau, overhead_fraction * 100, color="#0072B2", linewidth=2.0,
            linestyle="--", label="Checkpoint overhead (%)")
    ax.plot(tau, lost_work_fraction * 100, color="#D55E00", linewidth=2.0,
            linestyle="--", label="Expected lost work (%)")
    ax.plot(tau, total_cost_fraction * 100, color="black", linewidth=2.4,
            label="Total effective cost (%)")

    ax.axvline(tau_opt, color="#009E73", linestyle=":", linewidth=1.5)
    min_cost = np.interp(tau_opt, tau, total_cost_fraction) * 100
    ax.annotate(
        f"Young-Daly optimal:\nτ ≈ {tau_opt:.0f} min\n(δ={delta_min:.0f} min, M={M_hours:.1f} hr)",
        xy=(tau_opt, min_cost), xytext=(tau_opt + 40, min_cost + 8),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Checkpoint Interval τ (minutes)")
    ax.set_ylabel("Effective Cost (% of training time)")
    ax.set_title("Checkpoint Interval Tradeoff: Overhead vs. Expected Lost Work")
    ax.set_xlim(0, 300)
    ax.set_ylim(0, 40)
    ax.legend(loc="upper right", fontsize=9)

    out_path = args.out / "checkpoint_interval_tradeoff.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
