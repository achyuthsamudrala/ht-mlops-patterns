# Online Serving Systems

These patterns address serving models under real traffic, where latency, GPU utilization, and cost cannot all be simultaneously maximized — the inference trilemma most serving decisions are actually resolving.

## Reading order

[Serving Mode Selection](serving-mode-selection.md) first — it determines which of the other patterns in this family are even relevant to a given workload.

## Patterns in this section

- [Serving Mode Selection](serving-mode-selection.md)
- [Continuous & Dynamic Batching](continuous-and-dynamic-batching.md)
- [Cold Starts vs. Warm Pools](cold-starts-vs-warm-pools.md)
- [Quantization & Compiled Runtimes](quantization-and-compiled-runtimes.md)
- [Multi-Region GPU Capacity Failover](multi-region-gpu-capacity-failover.md)
- [Serving Protocol Standardization](serving-protocol-standardization.md)
- [Tiered SLOs for Mixed Traffic](tiered-slos-for-mixed-traffic.md)
