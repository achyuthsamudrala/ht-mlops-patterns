#!/usr/bin/env python3
"""
All-reduce time vs. GPU count, fast vs. slow interconnect.

Shows how distributed training's per-step communication time scales with GPU
count under a fast (RDMA/EFA/InfiniBand) vs. slow (standard Ethernet, no
GPUDirect) interconnect, and where each crosses over from compute-bound to
communication-bound.

Usage:
    python sim.py --out ../../src/figures/interconnect_scaling_curve

Output:
    interconnect_scaling_curve.svg — step time vs. GPU count, two fabrics
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Interconnect scaling curve")
    parser.add_argument("--out", type=Path, default=Path("../../src/figures/interconnect_scaling_curve"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    style = Path(__file__).parent.parent / "style.mplstyle"
    plt.style.use(style)

    gpu_count = np.arange(8, 2049, 8)

    # Compute time per step: roughly constant per GPU (perfect scaling assumption).
    compute_time_ms = np.full_like(gpu_count, 120, dtype=float)

    # Ring all-reduce communication cost scales with data volume / bandwidth,
    # and roughly with log(N) to linear(N) depending on topology depth; here
    # modeled simply as a per-GPU-count function reflecting increasing hops
    # and contention as the ring grows, at two different effective bandwidths.
    fast_fabric_ms = 8 + 0.09 * gpu_count       # RDMA/EFA/InfiniBand + GPUDirect
    slow_fabric_ms = 30 + 0.9 * gpu_count        # standard Ethernet, no GPUDirect

    fast_step_ms = compute_time_ms + fast_fabric_ms
    slow_step_ms = compute_time_ms + slow_fabric_ms

    fig, ax = plt.subplots()

    ax.plot(gpu_count, compute_time_ms, color="gray", linestyle=":", linewidth=1.5,
            label="Compute time (roughly constant per GPU)")
    ax.plot(gpu_count, fast_step_ms, color="#0072B2", linewidth=2.2,
            label="Step time — fast fabric (RDMA/EFA/InfiniBand)")
    ax.plot(gpu_count, slow_step_ms, color="#D55E00", linewidth=2.2,
            label="Step time — slow fabric (standard Ethernet)")

    # Mark crossover points where communication exceeds compute.
    fast_cross_idx = np.argmax(fast_fabric_ms > compute_time_ms)
    slow_cross_idx = np.argmax(slow_fabric_ms > compute_time_ms)

    ax.annotate(
        f"Slow fabric becomes\ncommunication-bound\nat ~{gpu_count[slow_cross_idx]} GPUs",
        xy=(gpu_count[slow_cross_idx], slow_step_ms[slow_cross_idx]),
        xytext=(gpu_count[slow_cross_idx] + 150, slow_step_ms[slow_cross_idx] + 300),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )
    ax.annotate(
        f"Fast fabric stays\ncompute-bound far longer",
        xy=(1800, fast_step_ms[np.searchsorted(gpu_count, 1800)]),
        xytext=(900, fast_step_ms[np.searchsorted(gpu_count, 1800)] + 250),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
    )

    ax.set_xlabel("GPU Count")
    ax.set_ylabel("Per-Step Time (ms, relative)")
    ax.set_title("Distributed Training Step Time: Fast vs. Slow Interconnect")
    ax.legend(loc="upper left", fontsize=9)

    out_path = args.out / "interconnect_scaling_curve.svg"
    fig.savefig(out_path, format="svg")
    print(f"Wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
