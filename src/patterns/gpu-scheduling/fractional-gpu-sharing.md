# Fractional GPU Sharing

> **One-liner:** MIG partitioning and time-slicing let small jobs share a GPU efficiently, but both introduce performance interference that not every workload tolerates.

## Symptom

- A small inference or debug workload assigned a fraction of a GPU shows inconsistent,
  higher-than-expected latency that correlates with other workloads' activity on the
  same physical GPU.
- Two workloads time-sliced onto the same GPU each individually run slower than either
  would running alone on a dedicated GPU, even though their combined resource
  requirement is well under one full GPU's capacity.
- A latency-sensitive interactive workload placed on a MIG (Multi-Instance GPU)
  partition shows acceptable average latency but unacceptable tail latency, traced to
  contention with other partitions sharing the same underlying memory bandwidth.
- Provisioning fractional GPU sharing for a cluster's interactive/debug pool
  significantly improves utilization but introduces enough performance variability
  that some workloads have to be explicitly excluded from it.

## Mechanism

Many GPU workloads, especially small debug jobs, notebooks, or lightweight inference,
don't need a full GPU's compute or memory capacity, and dedicating a whole GPU to each
such workload wastes the unused remainder. Fractional GPU sharing addresses this by
letting multiple workloads share one physical GPU, via two different mechanisms with
different isolation properties.

**MIG (Multi-Instance GPU)**, available on supporting NVIDIA GPU architectures,
partitions a physical GPU into several genuinely isolated instances at the hardware
level — each instance gets a dedicated slice of compute cores, memory, and memory
bandwidth, with hardware-enforced isolation between instances. This provides much
stronger isolation than software-based sharing, but the partitioning is fixed at
configuration time (a GPU configured into a specific MIG profile has a fixed set of
instance sizes) and doesn't allow arbitrarily fine-grained or dynamically
reconfigured sharing.

**Time-slicing** (context switching multiple workloads' kernels onto the GPU in
rapid succession, giving each a slice of wall-clock time) offers much more flexible,
arbitrary sharing ratios, but with weaker isolation — workloads sharing a GPU via
time-slicing compete for the same underlying memory bandwidth and cache resources even
while nominally taking turns on compute, and a workload with unpredictable, bursty
demand can degrade a co-scheduled workload's latency unpredictably, since there's no
hardware-enforced boundary preventing one workload's memory-bandwidth-heavy phase from
affecting another's.

Both mechanisms genuinely improve utilization for workloads that don't need a full
GPU and can tolerate some performance variability — but neither eliminates
interference entirely, and the degree of tolerable interference varies enormously by
workload. A latency-sensitive interactive or serving workload is far more sensitive to
tail-latency degradation from a noisy co-tenant than a best-effort batch job is,
which is why fractional sharing is usually deployed selectively — for specific
workload classes known to tolerate the interference — rather than universally applied
across every GPU in a fleet.

## Real-world sightings

NVIDIA's own MIG documentation explicitly describes the hardware-level isolation
MIG provides (dedicated compute, memory, and bandwidth per instance) as distinct from
and stronger than time-slicing's software-based context switching, and explicitly
scopes MIG's use case to workloads that fit within a fixed partition size and don't
need the flexibility of arbitrary sharing ratios.

Kubernetes device plugin documentation and various GPU-scheduling platform
documentation (Run:ai, and Kubernetes' own GPU time-slicing support) discuss both
mechanisms' tradeoffs explicitly, generally recommending time-slicing for workloads
tolerant of variable performance (development, testing, low-priority batch) and MIG
for workloads needing predictable, isolated performance guarantees within their
allocated fraction.

## Mitigations

### Reserving fractional sharing for interference-tolerant workload classes

**What it is:** Explicitly scope fractional GPU sharing (either mechanism) to
workload classes known to tolerate performance variability — interactive debug
sessions, notebooks, low-priority batch — rather than applying it universally.

**Cost:** Requires classifying workloads by interference tolerance, which isn't
always an obvious or stable property, especially for workloads whose latency
sensitivity changes depending on context (a notebook used for quick exploration versus
one running a timed benchmark).

**How it backfires:** A workload initially classified as interference-tolerant can
later be used in a latency-sensitive context its original classification didn't
anticipate, and nothing in the scheduling system itself catches that mismatch — it
shows up only as an unexplained performance complaint.

### Preferring MIG over time-slicing for workloads needing predictability

**What it is:** Use MIG's hardware-enforced partitioning for workloads that need
predictable performance within their fractional allocation, reserving time-slicing
for workloads that genuinely don't care about performance variability.

**Cost:** MIG's fixed partition sizes are less flexible than time-slicing's arbitrary
sharing ratios, potentially leaving some capacity underutilized if workload sizes
don't align well with available MIG profiles.

**How it backfires:** A workload's actual resource needs can grow beyond what its
assigned MIG partition size provides, and because MIG partitioning is fixed at
configuration time (not dynamically resizable), accommodating this requires
reconfiguring the GPU's MIG profile, which is a more disruptive operation than simply
adjusting a time-slicing ratio would be.

### Monitoring tail latency, not just average utilization, for shared GPUs

**What it is:** Track p99/p999 latency for workloads on fractionally-shared GPUs
specifically, not just average throughput or utilization, since interference effects
show up disproportionately in tail behavior.

**Cost:** Requires latency instrumentation at a finer grain than typical utilization
dashboards provide, and requires attributing tail-latency spikes to co-tenant
interference specifically, which isn't always straightforward.

**How it backfires:** None specific — the absence of this monitoring just means
interference-related tail-latency problems are discovered through user complaints
rather than proactively, which is a slower and noisier feedback loop.

## Interactions

- [GPU-Accelerated Video Decode](../training-data-platforms/gpu-accelerated-video-decode.md) —
  NVDEC hardware decoder units are themselves a shared, finite resource per GPU that
  fractional sharing schemes need to account for alongside compute and memory.
- [Utilization vs. Researcher Velocity](utilization-vs-researcher-velocity.md) —
  fractional sharing is one of the concrete mechanisms for improving utilization
  specifically in the always-on, interactive-capacity part of that broader tradeoff.
- [Hierarchical Fair-Share with Borrowing](hierarchical-fair-share-with-borrowing.md) —
  fractional sharing and fair-share borrowing are complementary mechanisms operating
  at different granularities (within a single GPU versus across a fleet).

## References

- NVIDIA Documentation. *Multi-Instance GPU (MIG) User Guide*. Describes hardware-
  level GPU partitioning and its isolation guarantees.
- Kubernetes Documentation. *GPU Time-Slicing*. Describes software-based GPU sharing
  and its tradeoffs relative to MIG.
- Run:ai Documentation. *Fractional GPU Scheduling*. Discusses practical workload
  classification and mechanism selection for fractional GPU sharing.
