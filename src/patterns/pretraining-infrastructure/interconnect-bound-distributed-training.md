# Interconnect-Bound Distributed Training

> **One-liner:** Collective communication operations like all-reduce are only as fast as the slowest link in the fabric, and a slow cross-node network stalls every GPU regardless of its own compute speed.

## Symptom

- Adding more GPUs to a training job increases wall-clock time per step, or improves
  it far less than the added compute should suggest — scaling efficiency degrades as
  GPU count grows.
- GPU compute utilization (measured via profiler) shows large gaps corresponding to
  time spent waiting on collective communication (all-reduce, all-gather) rather than
  actual matrix multiplication.
- The same model and batch size train noticeably faster on a cluster advertised as
  having "GPUDirect" or "EFA-enabled" networking than on one without, despite
  otherwise similar hardware.
- Profiling shows most communication time attributable to cross-node hops, with
  intra-node (NVLink) communication comparatively fast and not the bottleneck.

## Mechanism

As described in [GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md),
distributed data-parallel training requires every GPU to participate in a collective
all-reduce operation once per step to synchronize gradients, and a collective
operation's completion time is bounded by its slowest participant — including the
network hop between any two participants that happens to be on the critical path.

This produces a specific, diagnosable pattern: as GPU count grows, the *compute*
portion of each training step stays roughly constant per GPU (assuming reasonable
per-GPU utilization), but the *communication* portion grows, because there's more data
to synchronize across more participants and, depending on the collective algorithm's
implementation, more hops or more contention on the interconnect. At some GPU count,
communication time exceeds compute time, and the job becomes fundamentally
communication-bound — adding more GPUs beyond this point yields diminishing, and
eventually negative, returns, because the added communication overhead outweighs the
added compute capacity.

![Distributed training step time: fast vs. slow interconnect](../../figures/interconnect_scaling_curve/interconnect_scaling_curve.svg)

(See also [GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md)
for the foundational version of this figure.) A slow fabric crosses into
communication-bound territory at a far lower GPU count than a fast one — the same
model, the same GPU count, scaling very differently depending on what connects them.

Cross-node interconnect quality determines exactly where this crossover happens.
Purpose-built training fabrics (RDMA over InfiniBand with GPUDirect, AWS's EFA) bypass
the CPU and standard networking stack, letting GPUs exchange data with much lower
latency and higher effective bandwidth than they would over standard Ethernet-based
networking. A cluster without this fabric hits the communication-bound crossover at a
much lower GPU count, meaning its effective, useful scale-out ceiling is far below its
nominal GPU count.

## Real-world sightings

NVIDIA's NCCL (NVIDIA Collective Communications Library) documentation describes ring
and tree all-reduce algorithm implementations and their sensitivity to underlying
network topology and bandwidth, forming the basis for why cluster network design
directly determines achievable distributed training scaling efficiency — this is
explicit, first-party guidance from the vendor whose library implements the collective
operations nearly every major training framework relies on.

Cloud providers' own documentation for GPU-optimized networking (AWS's EFA, GCP's and
Azure's GPUDirect-RDMA-over-InfiniBand offerings) explicitly frames these products as
solving exactly this problem — enabling distributed training to scale efficiently
across many nodes — and their marketing and technical documentation both describe
measurable scaling efficiency improvements attributable specifically to bypassing
standard networking stack overhead for collective operations.

## Mitigations

### Provisioning purpose-built training interconnect

**What it is:** Use RDMA-capable networking with GPUDirect (InfiniBand or equivalent)
or a cloud-specific offering (AWS EFA) rather than standard Ethernet networking for
any cluster intended for genuinely large-scale distributed training.

**Cost:** Purpose-built training fabric is more expensive than standard networking and
may require specific instance types or cluster configurations to actually enable.

**How it backfires:** Provisioning a fast fabric but placing a job's workers without
topology awareness (see [Topology-Aware Placement](../gpu-scheduling/topology-aware-placement.md))
squanders much of the fabric's benefit, since the fabric being fast in principle
doesn't help if the scheduler routes communication across more hops than necessary.

### Choosing parallelism strategy to bound communication volume

**What it is:** Select and compose parallelism strategies (see
[Composing Parallelism Strategies](composing-parallelism-strategies.md)) specifically
to bound how much data needs to cross the network per step, rather than defaulting to
pure data parallelism regardless of model size and cluster topology.

**Cost:** Alternative parallelism strategies have their own tradeoffs (memory
distribution complexity, implementation and debugging overhead) beyond pure
communication volume.

**How it backfires:** A parallelism strategy chosen to minimize communication for a
given cluster's interconnect can become suboptimal if the job is later run on
different hardware with different interconnect characteristics — the "right" strategy
is cluster-specific, not universal.

### Overlapping communication with compute

**What it is:** Structure the training loop so gradient communication for earlier
layers begins while later layers are still computing their backward pass, hiding
communication latency behind compute that would otherwise be idle time.

**Cost:** Requires framework-level support for this overlap (most modern distributed
training frameworks implement some form of this, but not all configurations enable it
by default) and doesn't help once communication volume genuinely exceeds available
compute time to hide behind.

**How it backfires:** Overlap only helps up to the point where communication time
still fits within compute time; once a job is genuinely communication-bound (the
crossover described above), no amount of overlap scheduling recovers the lost
efficiency — overlap hides communication cost, it doesn't reduce it.

## Interactions

- [GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md) —
  the foundational mechanism this pattern names as a specific, diagnosable failure
  mode.
- [Topology-Aware Placement](../gpu-scheduling/topology-aware-placement.md) — a fast
  fabric's benefit is only fully realized if the scheduler places a job's workers to
  actually exploit it.
- [Composing Parallelism Strategies](composing-parallelism-strategies.md) — the
  primary lever for controlling how much communication a given model and cluster
  combination actually needs to perform.

## References

- NVIDIA NCCL Documentation. *NCCL Collective Operations*. Describes ring/tree
  all-reduce algorithms and their topology and bandwidth sensitivity.
- Amazon Web Services Documentation. *Elastic Fabric Adapter (EFA)*. Describes
  RDMA-based, GPUDirect-enabled networking for distributed training scale-out.
- Jouppi, N. et al. *TPU v4: An Optically Reconfigurable Supercomputer for Machine
  Learning*. ISCA 2023. Discusses interconnect design as a first-order concern in
  large-scale ML training system architecture.
