#!/usr/bin/env python3
"""
Reprocessing cost vs. corpus size, with and without content-addressed skip.

Shows how naive full-corpus reprocessing cost grows linearly (and
repeatedly, per model update) with corpus size, while content-addressed,
lineage-scoped reprocessing stays bounded to only what actually changed.

Usage:
    python sim.py --out ../../src/figures/backfill_cost_explosion

Output:
    backfill_cost_explosion.svg — reprocessing cost vs. corpus size
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Backfill cost explosion")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/backfill_cost_explosion"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    corpus_size_m = np.linspace(0.1, 50, 400)  # millions of items

    cost_per_item = 0.02  # relative GPU-cost unit per item

    # Naive: every model update reprocesses the entire corpus.
    naive_full_reprocess = corpus_size_m * cost_per_item

    # Content-addressed: only genuinely new/changed content needs
    # processing; assume ~8% of corpus is net-new content per update cycle
    # regardless of total corpus size.
    content_addressed = corpus_size_m * 0.08 * cost_per_item

    # Lineage-scoped: a model update typically affects only one of several
    # independent enrichment outputs, further reducing scope.
    lineage_scoped = corpus_size_m * 0.08 * cost_per_item * 0.3

    fig, ax = plt.subplots()

    ax.plot(corpus_size_m, naive_full_reprocess, color="#D55E00", linewidth=2.2,
            label="Naive: full corpus reprocessed per update")
    ax.plot(corpus_size_m, content_addressed, color="#E69F00", linewidth=2.2,
            label="Content-addressed: only new/changed content")
    ax.plot(corpus_size_m, lineage_scoped, color="#0072B2", linewidth=2.2,
            label="+ Lineage-scoped: only affected outputs")

    at_20m = np.searchsorted(corpus_size_m, 20)
    ax.annotate(
        f"At 20M items:\nnaive = {naive_full_reprocess[at_20m]:.1f}\nlineage-scoped = {lineage_scoped[at_20m]:.2f}\n(~{naive_full_reprocess[at_20m]/lineage_scoped[at_20m]:.0f}x cheaper)",
        xy=(20, lineage_scoped[at_20m]), xytext=(25, 0.55),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Corpus Size (millions of items)")
    ax.set_ylabel("Reprocessing Cost per Model Update (relative GPU-cost)")
    ax.set_title("Backfill Cost per Model Update: Naive vs. Scoped Reprocessing")
    ax.legend(loc="upper left", fontsize=9)

    out_path = args.out / "backfill_cost_explosion.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
