# Elastic Training vs. Hot Spares

> **One-liner:** Reshaping a distributed job after a node loss is cheap for data parallelism and expensive or infeasible for tensor/pipeline parallelism, which is why hot spares often win for large jobs.

## Symptom

- A framework's "elastic" training feature works well for a small data-parallel job
  but fails or produces degraded behavior when applied to a job using tensor or
  pipeline parallelism.
- After a node failure, a job configured for elastic recovery resumes with fewer
  workers and a correspondingly different effective batch size, subtly changing
  training dynamics (and sometimes convergence behavior) compared to the original
  configuration.
- Recovery time after a failure is dominated by waiting for replacement capacity to
  become available, rather than by the mechanics of restarting the job itself.
- A large, tensor-and-pipeline-parallel job configured with no reshape or spare
  capacity strategy simply stalls indefinitely after a node loss, waiting for the
  exact original node count to become available again.

## Mechanism

Recovering from a node failure in a distributed training job requires either
**reshaping** the job to continue with fewer resources, or **replacing** the lost
node with an equivalent one and resuming with the original topology unchanged.
Which of these is actually feasible depends heavily on which parallelism strategies
(see [Composing Parallelism Strategies](composing-parallelism-strategies.md)) the job
uses.

**Pure data parallelism** reshapes relatively gracefully: losing one data-parallel
replica just means training continues with N-1 replicas instead of N, at a
correspondingly smaller effective batch size (or the same per-replica batch size with
a smaller total batch). This is a well-defined, if not entirely consequence-free,
degradation — training can genuinely continue, just with a modified configuration.
Frameworks like torchelastic and Ray Train support this kind of elastic reshaping
specifically for data-parallel workloads.

**Tensor and pipeline parallelism** reshape far less gracefully, if at all. Tensor
parallelism splits individual layers' computation across a specific number of GPUs
(the tensor-parallel degree); losing one of those GPUs doesn't leave a smaller but
still-functional configuration — it leaves a layer that literally cannot be computed
without all its assigned shards. Pipeline parallelism similarly assigns specific
layers to specific GPUs in a fixed sequence; losing one stage breaks the pipeline
entirely, not partially. Reshaping either of these after a loss generally requires
recomputing the parallelism assignment from scratch (a different tensor-parallel
degree, a different pipeline stage assignment) — which is a nontrivial operation, not
a lightweight continuation, and for large jobs may not be practical to do
automatically at all.

This is precisely why **hot spares** — provisioning N+k nodes for a job that logically
needs N, so a failed node can be swapped for an already-warm, pre-provisioned spare
without reshaping the parallelism configuration at all — are the preferred recovery
strategy for large jobs using tensor or pipeline parallelism: the job resumes with
its *original* topology intact, using the spare in place of the failed node, restoring
from the last checkpoint (see
[Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md)) without
any parallelism-layout recomputation. The cost is paying for idle spare capacity that
sits unused unless and until a failure occurs — a real, ongoing cost, but one that's
often preferable to either the complexity of automatic reshaping for rigid parallelism
layouts or the alternative of waiting, potentially for hours, for genuinely new
capacity to become available under GPU scarcity.

## Real-world sightings

PyTorch's torchelastic documentation explicitly scopes its elastic training support
around data-parallel-style workloads that tolerate a changing world size gracefully,
and separately discusses the added complexity of elasticity for model-parallel
configurations, reflecting the same asymmetry described above.

Published large-scale training infrastructure reports from organizations training
frontier-scale models (using heavy tensor and pipeline parallelism, given model
sizes that require it) consistently describe hot-spare or standby-node strategies as
their production fault-tolerance approach for large training jobs, rather than
automatic parallelism reshaping — a design choice explicitly motivated by the rigidity
of tensor/pipeline parallelism layouts and the value of restoring the exact original
configuration quickly rather than reshaping it.

## Mitigations

### Hot spares for tensor/pipeline-parallel jobs

**What it is:** Provision additional nodes beyond a job's minimum requirement
specifically as standby replacements, so a failure can be handled by node
substitution rather than parallelism reshaping.

**Cost:** Pays for genuinely idle capacity continuously, a real and potentially
significant ongoing cost proportional to how many spares are provisioned relative to
job size.

**How it backfires:** Sizing spare capacity too conservatively (too few spares)
doesn't actually protect against correlated or multiple simultaneous failures; sizing
it too generously wastes capacity that could have run other useful work.

### Elastic reshaping for data-parallel-tolerant workloads

**What it is:** Use framework-level elastic training support (torchelastic, Ray
Train's elastic capabilities) for workloads using pure or primarily data-parallel
strategies, where continuing with fewer replicas is a well-defined, acceptable
degradation.

**Cost:** Changes effective batch size on failure, which can have real (if often
modest) effects on training dynamics and convergence behavior that need to be
understood and accepted as part of adopting this strategy.

**How it backfires:** A job that appears purely data-parallel but has any
tensor/pipeline-parallel component mixed in (common in large 3D-parallel
configurations) may not actually reshape safely, and assuming elasticity works because
"it's mostly data parallel" can produce subtle correctness or performance issues.

### Fast checkpoint-based restoration onto a hot spare

**What it is:** Combine hot spares with fast, recent checkpointing (see
[Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md)) so a
node swap restores training with minimal lost progress, not just minimal
reconfiguration effort.

**Cost:** The recovery speed this mitigation buys is only as good as the checkpoint
interval allows — a hot spare swap still loses whatever progress happened since the
last checkpoint.

**How it backfires:** If checkpoint interval and hot-spare strategy are tuned
independently rather than jointly, a job can have excellent node-substitution
mechanics but still lose a large amount of progress per failure simply because the
checkpoint interval wasn't set with the actual failure rate in mind.

## Interactions

- [Composing Parallelism Strategies](composing-parallelism-strategies.md) — the
  direct determinant of whether a job's parallelism layout tolerates reshaping at all.
- [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md) — the
  checkpoint interval sets how much progress is lost regardless of which recovery
  strategy (reshape or hot spare) is used.
- [Failure as the Steady State at Fleet Scale](../../foundations/failure-as-the-steady-state.md) —
  the foundational assumption that motivates provisioning for recovery at all, rather
  than treating failure as rare enough to handle manually.

## References

- PyTorch Documentation. *torchelastic*. Describes elastic training support and its
  scoping to data-parallel-tolerant workloads.
- Narayanan, D. et al. *Efficient Large-Scale Language Model Training on GPU Clusters
  Using Megatron-LM*. SC 2021. Discusses the rigidity of tensor/pipeline parallelism
  layouts relevant to why reshaping them is difficult.
- Jeon, M. et al. *Analysis of Large-Scale Multi-Tenant GPU Clusters for DNN Training
  Workloads*. USENIX ATC 2019. Empirical study of failure and recovery patterns in
  large-scale GPU training clusters.
