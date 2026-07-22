# Large-Scale Pretraining Infrastructure

These patterns cover the mechanics of training very large models across many GPUs — where the interconnect, the data pipeline, and the checkpointing strategy usually matter more than the model math itself.

## Reading order

[Interconnect-Bound Distributed Training](interconnect-bound-distributed-training.md) first, then [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md) since fault tolerance is what makes any of the rest economically viable at scale.

## Patterns in this section

- [Interconnect-Bound Distributed Training](interconnect-bound-distributed-training.md)
- [Composing Parallelism Strategies](composing-parallelism-strategies.md)
- [Data Loading as the Real Bottleneck](data-loading-as-the-real-bottleneck.md)
- [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md)
- [Silent Data Corruption & Stragglers](silent-data-corruption-and-stragglers.md)
- [Elastic Training vs. Hot Spares](elastic-training-vs-hot-spares.md)
- [SLURM vs. Kubernetes for Training](slurm-vs-kubernetes-for-training.md)
