#!/usr/bin/env python3
"""
apiserver/etcd write latency vs. cluster size, at different watch counts.

Shows how write-path latency grows with cluster size (object count as a
proxy), and how that growth is steeper the more active watches are
subscribed to the affected resource types (watch fan-out cost).

Usage:
    python sim.py --out ../../src/figures/etcd_watch_fanout_latency

Output:
    etcd_watch_fanout_latency.svg — write latency vs. object count, by watch count
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="etcd watch fan-out latency")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/etcd_watch_fanout_latency"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    object_count_k = np.linspace(1, 200, 400)  # thousands of objects

    base_latency_ms = 2.0

    # Write latency grows with object count (larger keyspace, more index
    # overhead) and, separately, with watch fan-out: each write has to
    # notify every active watcher on the affected resource type.
    def latency(watch_count):
        write_path = base_latency_ms + 0.015 * object_count_k
        fanout = 0.02 * watch_count * np.sqrt(object_count_k)
        return write_path + fanout

    low_watch = latency(watch_count=2)
    med_watch = latency(watch_count=15)
    high_watch = latency(watch_count=50)

    fig, ax = plt.subplots()

    ax.plot(object_count_k, low_watch, color="#0072B2", linewidth=2.2,
            label="Few watchers (2 controllers)")
    ax.plot(object_count_k, med_watch, color="#E69F00", linewidth=2.2,
            label="Moderate watchers (15 controllers)")
    ax.plot(object_count_k, high_watch, color="#D55E00", linewidth=2.2,
            label="Many watchers (50 controllers/operators)")

    ax.annotate(
        "Same object count, same node count —\nwatch fan-out alone drives\nthe latency difference",
        xy=(150, high_watch[np.searchsorted(object_count_k, 150)]),
        xytext=(60, 220),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("Object Count (thousands)")
    ax.set_ylabel("Write-Path Latency (ms, relative)")
    ax.set_title("Write Latency vs. Object Count, by Active Watch Count")
    ax.legend(loc="upper left", fontsize=9)

    out_path = args.out / "etcd_watch_fanout_latency.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
