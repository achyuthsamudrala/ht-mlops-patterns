#!/usr/bin/env python3
"""
Wasted compute vs. preemption frequency, checkpointed vs. not.

Shows how wasted compute (lost progress that must be redone) scales with
preemption frequency for jobs with frequent checkpoints vs. infrequent or
no checkpoints.

Usage:
    python sim.py --out ../../src/figures/preemption_wasted_work

Output:
    preemption_wasted_work.svg — wasted compute % vs. preemptions per day
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Preemption wasted work")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/preemption_wasted_work"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    preemptions_per_day = np.linspace(0, 20, 200)

    # Frequent checkpoints (e.g. every 10 min): lost work per preemption is
    # small and bounded, so wasted-compute % grows slowly and linearly.
    frequent_ckpt_loss_per_event = 0.15   # % of daily compute lost per preemption
    frequent = preemptions_per_day * frequent_ckpt_loss_per_event

    # Infrequent checkpoints (e.g. every 2 hours): each preemption risks a
    # much larger chunk of redone work.
    infrequent_ckpt_loss_per_event = 1.8
    infrequent = preemptions_per_day * infrequent_ckpt_loss_per_event
    infrequent = np.clip(infrequent, 0, 95)

    # No checkpointing at all: every preemption restarts from scratch,
    # catastrophic even at low preemption frequency.
    no_ckpt_loss_per_event = 8.0
    no_checkpoint = preemptions_per_day * no_ckpt_loss_per_event
    no_checkpoint = np.clip(no_checkpoint, 0, 100)

    fig, ax = plt.subplots()

    ax.plot(preemptions_per_day, frequent, color="#0072B2", linewidth=2.2,
            label="Frequent checkpoints (~every 10 min)")
    ax.plot(preemptions_per_day, infrequent, color="#E69F00", linewidth=2.2,
            label="Infrequent checkpoints (~every 2 hr)")
    ax.plot(preemptions_per_day, no_checkpoint, color="#D55E00", linewidth=2.2,
            label="No checkpointing")

    ax.annotate(
        "Even frequent preemption stays\ncheap with frequent checkpoints",
        xy=(15, frequent[np.searchsorted(preemptions_per_day, 15)]),
        xytext=(6, 30),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )
    ax.annotate(
        "No checkpointing: a handful of\npreemptions wastes nearly everything",
        xy=(6, no_checkpoint[np.searchsorted(preemptions_per_day, 6)]),
        xytext=(7, 75),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Preemptions per Day")
    ax.set_ylabel("Wasted Compute (% of daily throughput)")
    ax.set_title("Preemption Cost Depends Entirely on Checkpoint Frequency")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", fontsize=9)

    out_path = args.out / "preemption_wasted_work.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
