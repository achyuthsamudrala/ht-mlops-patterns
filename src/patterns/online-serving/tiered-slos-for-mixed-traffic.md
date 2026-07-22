# Tiered SLOs for Mixed Traffic

> **One-liner:** Serving latency-critical and best-effort traffic under one undifferentiated SLO forces every request to pay for the most expensive tier's guarantees.

## Symptom

- A serving system provisioned to meet a strict latency SLO for its most demanding
  traffic applies that same expensive provisioning (warm pools, aggressive batching
  windows, premium capacity) uniformly to all traffic, including requests that would
  have tolerated much looser latency.
- Best-effort or exploratory traffic (a background analytics job, a non-urgent batch
  request) competes for the same capacity and provisioning as latency-critical
  production traffic, with no mechanism to deprioritize it appropriately.
- Cost review reveals that a large fraction of expensively-provisioned serving
  capacity is actually serving traffic that never needed that level of guarantee in
  the first place.
- Adding a new, less latency-sensitive traffic source to an existing serving endpoint
  either degrades the latency-critical traffic's performance (if unprioritized) or
  requires expensive over-provisioning to protect it (if naively isolated by just
  scaling everything up).

## Mechanism

Not all traffic hitting a serving endpoint has the same latency requirements, and
provisioning a single, undifferentiated SLO across genuinely heterogeneous traffic
means the provisioning has to satisfy whichever traffic has the *strictest*
requirement — every request, including ones that would have been fine with a much
looser guarantee, ends up paying (in provisioned capacity cost) for a guarantee it
didn't actually need.

**Tiered SLOs** address this by explicitly classifying traffic into latency/priority
tiers and provisioning and scheduling each tier according to its actual requirement,
rather than treating all traffic uniformly. A latency-critical tier gets warm pools
(see [Cold Starts vs. Warm Pools](cold-starts-vs-warm-pools.md)), tight batching
windows (see [Continuous & Dynamic Batching](continuous-and-dynamic-batching.md)), and
priority access to capacity under contention. A best-effort tier can tolerate cold
starts, longer batching windows for better throughput-per-cost, and can be
preempted or delayed under contention without violating any guarantee, because no
strict guarantee was ever made for it.

This is the serving-layer instance of the general fair-share and priority principles
described in [Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md)
and [Gang Scheduling vs. Bin-Packing](../../foundations/gang-scheduling-vs-bin-packing.md):
rather than provisioning a single pool sized for the worst case across all
traffic, segment traffic by actual requirement and provision each segment to its own
requirement — capturing most of the cost efficiency of shared infrastructure while
still protecting the traffic that genuinely needs strict guarantees.

The design challenge is accurate traffic classification: tiering only works if
traffic is correctly and reliably classified into the right tier, and misclassifying
genuinely latency-critical traffic as best-effort (or the reverse) either produces an
SLO violation for the misclassified traffic or wastes premium provisioning on traffic
that didn't need it — the tiering mechanism itself doesn't fail, but its benefit
entirely depends on correct classification upstream of it.

## Real-world sightings

Cloud serving platforms' documentation on request priority classes (various
providers' inference endpoint priority/QoS features) explicitly frame tiered
provisioning as a cost-optimization mechanism, allowing best-effort workloads to
share infrastructure with latency-critical ones without requiring uniform,
worst-case provisioning across both.

The general priority-tiering pattern is directly analogous to Kubernetes' own API
Priority and Fairness mechanism (see
[API Priority and Fairness](../control-plane-at-scale/api-priority-and-fairness.md)) —
both are instances of the same underlying principle (differentiate service quality by
actual requirement rather than uniform treatment) applied at different layers of the
stack, request-serving versus apiserver request handling.

## Mitigations

### Explicit, accurate traffic classification into latency tiers

**What it is:** Classify incoming traffic into latency/priority tiers based on its
actual requirements, as accurately and automatically as possible, rather than
treating classification as a one-time, static assignment prone to becoming stale.

**Cost:** Requires building and maintaining classification logic (whether by client
identity, request metadata, or another signal), which is additional platform
complexity beyond a single undifferentiated serving path.

**How it backfires:** Misclassification in either direction defeats the entire
purpose: latency-critical traffic classified as best-effort experiences SLO
violations it shouldn't, while best-effort traffic classified as latency-critical
wastes premium provisioning for no benefit.

### Separate provisioning per tier

**What it is:** Provision distinct capacity pools (warm-pool sizing, batching window
configuration, priority scheduling) for each latency tier, rather than a single pool
trying to serve every tier's requirements simultaneously.

**Cost:** Adds operational complexity — multiple pools to monitor, scale, and
maintain — compared to a single, simpler (if less cost-efficient) undifferentiated
pool.

**How it backfires:** Separate pools sized independently can each individually be
under- or over-provisioned relative to their tier's actual demand, and rebalancing
capacity across tiers as their relative demand shifts requires ongoing attention that
a single unified pool wouldn't have needed.

### Work-conserving capacity sharing across tiers under low contention

**What it is:** Allow best-effort traffic to opportunistically use latency-critical
tier capacity when it's idle, reclaiming it (via preemption) when latency-critical
demand returns — the same work-conserving borrowing principle described in
[Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md).

**Cost:** Requires preemption logic and, ideally, checkpoint-aware handling for any
best-effort work interrupted by reclaimed capacity, adding implementation complexity.

**How it backfires:** Best-effort traffic that isn't actually safely preemptible
(no checkpointing or equivalent progress-preservation mechanism) loses work when
preempted, which may be an acceptable cost for genuinely best-effort traffic but needs
to be an explicit, accepted tradeoff rather than an unexamined side effect.

## Interactions

- [Cold Starts vs. Warm Pools](cold-starts-vs-warm-pools.md) — warm-pool sizing is
  naturally a per-tier decision, with latency-critical tiers justifying warm capacity
  that best-effort tiers may not need.
- [Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md) —
  the general work-conserving, tiered-priority principle this pattern applies
  specifically to serving traffic rather than GPU scheduling for training jobs.
- [API Priority and Fairness](../control-plane-at-scale/api-priority-and-fairness.md) —
  a conceptually analogous mechanism differentiating traffic priority, applied to
  Kubernetes apiserver requests rather than model-serving requests.

## References

- Kubernetes Documentation. *API Priority and Fairness*. Describes the analogous
  priority-tiering mechanism at the apiserver request-handling layer.
- Google Cloud Documentation. *Vertex AI Prediction — Priority and Quality of
  Service*. Describes tiered provisioning concepts for mixed-priority inference
  traffic.
- Dean, J. and Barroso, L. A. *The Tail at Scale*. Communications of the ACM, 2013.
  Foundational discussion of latency variance and tail-latency management in
  large-scale systems, relevant to why differentiated SLO tiers matter for mixed
  traffic.
