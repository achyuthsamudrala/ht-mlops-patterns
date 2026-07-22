# Topology-Aware Placement

> **One-liner:** Placing a distributed job's workers without regard to rack, switch, or NVLink-domain boundaries can quietly cap its achievable throughput regardless of how much compute it was allocated.

## Symptom

- Two runs of the identical distributed training job, on the identical GPU count and
  type, show meaningfully different step times, with the only difference being which
  specific nodes the scheduler happened to place the job on.
- A job's workers are spread across many different racks or network segments, and its
  achievable throughput is well below what the same GPU count would achieve if packed
  within a single fast network domain.
- Profiling attributes a large fraction of step time to cross-node communication, even
  though the cluster's interconnect is nominally fast end-to-end.
- Requesting the same resources twice in quick succession produces very different
  placements (and very different performance) depending on which specific nodes
  happened to be free at request time.

## Mechanism

A gang-scheduled job (see [Gang Scheduling for Distributed Jobs](gang-scheduling-for-distributed-jobs.md))
guarantees that all of a job's workers are placed simultaneously, but says nothing
about *where relative to each other* they're placed. As described in
[GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md),
collective communication performance is sensitive to network topology — workers
spread across distant racks or switch boundaries see worse effective bandwidth and
higher latency than workers packed within a single fast network domain, purely as a
function of the extra hops and shared-link contention involved, independent of the
job's own configuration.

A scheduler that satisfies gang-scheduling atomicity but places workers wherever
capacity happens to be free — potentially scattered across many racks — can produce a
technically valid, fully-atomic placement that performs substantially worse than an
equally-sized, topology-aware placement using the same total GPU count. This is a
distinct failure mode from the gang-scheduling problem itself: the job *starts* and
*runs*, it just runs slower than it should, which is a harder problem to notice and
diagnose than an outright scheduling failure, since nothing looks obviously broken —
the job simply underperforms relative to its theoretical capability.

Topology-aware scheduling addresses this by making the scheduler explicitly aware of
the physical or logical network hierarchy (which nodes share a rack, which racks
share a spine switch, which GPUs share an NVLink domain) and preferring placements
that minimize the network "distance" between a job's workers — packing a job as
tightly as possible within the fastest available network domain, rather than treating
all free capacity as interchangeable.

## Real-world sightings

Kubernetes' own scheduling framework documentation describes extension points
(PreFilter, Filter, Score) specifically designed to let custom scheduler plugins
implement exactly this kind of topology-preference logic — the framework provides the
mechanism, but topology-awareness itself has to be implemented as a plugin, since
vanilla scheduling has no built-in concept of network locality beyond basic
node/zone affinity.

NCCL's own documentation on topology detection describes how it automatically probes
and adapts its collective communication algorithm choice to the detected physical
topology at runtime — this is a complementary, job-level mechanism (NCCL adapting to
whatever topology it finds itself placed on) rather than a scheduling-level one (the
scheduler choosing a good topology to place the job on in the first place), and both
layers matter: a well-placed job still benefits from NCCL's topology-aware algorithm
selection, and a poorly-placed job can't fully recover its lost performance through
NCCL's adaptation alone.

## Mitigations

### Rack/switch-aware scheduler plugins

**What it is:** Implement or adopt a scheduler plugin that scores candidate placements
based on network locality — preferring placements that pack a job's workers within
the smallest number of racks or switch domains that can hold them.

**Cost:** Requires the scheduler to have accurate, up-to-date topology information
about the cluster, which itself has to be maintained and kept synchronized with actual
physical or logical network changes.

**How it backfires:** Aggressively optimizing for topology locality can increase
placement fragmentation — packing every job as tightly as possible can leave
oddly-shaped gaps of free capacity that don't fit the next job's requirement well,
trading topology efficiency for utilization efficiency in a way that needs to be
balanced, not maximized unilaterally.

### Provisioning cluster capacity in topology-coherent blocks

**What it is:** Physically or logically organize cluster capacity so that
commonly-requested job sizes fit naturally within single fast-network domains, rather
than having job-size and network-domain-size be unrelated, independently-chosen
numbers.

**Cost:** Requires capacity planning to account for network topology alongside raw
GPU count, adding a dimension to infrastructure provisioning decisions.

**How it backfires:** A cluster provisioned around today's typical job sizes can
become a poor fit if job sizes grow (larger models needing more GPUs than any single
fast-network domain can hold), forcing exactly the cross-domain placement this
mitigation was meant to avoid.

### Exposing topology information to job submitters

**What it is:** Let job submitters (or the platform's job-submission tooling)
express affinity preferences based on topology, rather than treating topology
awareness as purely the scheduler's internal concern.

**Cost:** Adds complexity to the job submission interface and requires submitters to
understand enough about topology to express meaningful preferences.

**How it backfires:** Submitter-expressed preferences can conflict with the
scheduler's own topology-optimization goals, or can be based on stale assumptions
about cluster topology that have since changed, producing worse placements than
letting the scheduler decide autonomously.

## Interactions

- [GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md) —
  the foundational mechanism that makes topology-aware placement matter at all.
- [Gang Scheduling for Distributed Jobs](gang-scheduling-for-distributed-jobs.md) —
  topology-aware placement is a refinement layered on top of gang scheduling's
  atomicity guarantee, not a substitute for it.
- [Interconnect-Bound Distributed Training](../pretraining-infrastructure/interconnect-bound-distributed-training.md) —
  the training-side symptom that a poor topology-unaware placement produces.

## References

- Kubernetes Documentation. *Scheduling Framework*. Describes the extension points
  (Filter, Score) used to implement custom topology-aware scheduling logic.
- NVIDIA NCCL Documentation. *Topology Detection*. Describes runtime adaptation to
  detected physical network topology for collective operations.
- Jeon, M. et al. *Analysis of Large-Scale Multi-Tenant GPU Clusters for DNN Training
  Workloads*. USENIX ATC 2019. Discusses placement and locality effects on training
  job performance in real production clusters.
