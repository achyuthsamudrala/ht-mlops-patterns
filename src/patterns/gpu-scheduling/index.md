# GPU Scheduling & Multi-Tenancy

These patterns address the tension between maximizing GPU utilization and preserving researcher iteration velocity — two goals that cannot both be fully maximized on a shared, scarce fleet.

## Reading order

[Gang Scheduling for Distributed Jobs](gang-scheduling-for-distributed-jobs.md) first, then [Utilization vs. Researcher Velocity](utilization-vs-researcher-velocity.md) for the central tradeoff every other mitigation in this family is negotiating.

## Patterns in this section

- [Gang Scheduling for Distributed Jobs](gang-scheduling-for-distributed-jobs.md)
- [Topology-Aware Placement](topology-aware-placement.md)
- [Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md)
- [Hierarchical Fair-Share with Borrowing](hierarchical-fair-share-with-borrowing.md)
- [Fractional GPU Sharing](fractional-gpu-sharing.md)
- [Utilization vs. Researcher Velocity](utilization-vs-researcher-velocity.md)
