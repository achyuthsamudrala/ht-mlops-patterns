#!/usr/bin/env python3
"""
Cluster utilization vs. job size mix: gang scheduling (no backfill) vs.
gang scheduling with backfill vs. pure bin-packing.

Shows how a rigid gang-scheduling policy leaves capacity idle while waiting
for large jobs, how backfill recovers most of that utilization, and how
pure bin-packing risks partial-allocation deadlock for large jobs (modeled
here as an effective utilization penalty from stalled large jobs).

Usage:
    python sim.py --out ../../src/figures/gang_scheduling_fragmentation

Output:
    gang_scheduling_fragmentation.svg — utilization vs. fraction of large jobs
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Gang scheduling fragmentation")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/gang_scheduling_fragmentation"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    # X-axis: fraction of cluster demand that comes from large, gang-scheduled jobs.
    large_job_fraction = np.linspace(0, 1, 200)

    # Pure bin-packing: high utilization at low large-job fraction, but
    # effective utilization collapses as large-job fraction grows because
    # partial allocations stall without completing useful work.
    bin_packing = 95 - 55 * large_job_fraction**1.6

    # Rigid gang scheduling, no backfill: reserves full capacity for the next
    # large job while waiting, so utilization drops as reservation waiting
    # time grows with large-job fraction.
    gang_no_backfill = 90 - 45 * large_job_fraction

    # Gang scheduling with backfill: small jobs fill reserved gaps, recovering
    # most of the utilization loss from rigid reservation.
    gang_with_backfill = 90 - 12 * large_job_fraction

    fig, ax = plt.subplots()

    ax.plot(large_job_fraction * 100, bin_packing, color="#D55E00", linewidth=2.2,
            label="Pure bin-packing (no gang awareness)")
    ax.plot(large_job_fraction * 100, gang_no_backfill, color="#E69F00", linewidth=2.2,
            linestyle="--", label="Gang scheduling, no backfill")
    ax.plot(large_job_fraction * 100, gang_with_backfill, color="#0072B2", linewidth=2.2,
            label="Gang scheduling + backfill")

    ax.annotate(
        "Partial allocations stall as\nlarge-job share grows",
        xy=(70, bin_packing[np.searchsorted(large_job_fraction*100, 70)]),
        xytext=(35, 20),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )
    ax.annotate(
        "Backfill recovers most of the\nutilization rigid reservation loses",
        xy=(80, gang_with_backfill[np.searchsorted(large_job_fraction*100, 80)]),
        xytext=(30, 65),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Large (Gang-Scheduled) Jobs as % of Cluster Demand")
    ax.set_ylabel("Effective Cluster Utilization (%)")
    ax.set_title("Gang Scheduling and Backfill vs. Pure Bin-Packing")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower left", fontsize=9)

    out_path = args.out / "gang_scheduling_fragmentation.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
