# Utilization vs. Researcher Velocity

> **One-liner:** Maximizing GPU utilization and minimizing a researcher's wait-for-capacity time are in direct tension, and a platform has to choose which one it's actually optimizing for.

## Symptom

- Cluster utilization dashboards look excellent (GPUs are almost always busy), but
  researcher satisfaction is low, with frequent complaints about waiting for capacity
  to run a quick experiment.
- A platform team optimizes scheduling policy purely for utilization metrics and
  discovers, belatedly, that researchers have started avoiding the platform for
  quick, interactive work in favor of ad-hoc, unmanaged capacity they've found
  elsewhere.
- An "always-on" pool of capacity reserved for interactive/debug use shows
  persistently low utilization by design, and is flagged as wasteful in a cost review
  that doesn't account for what it's actually buying.
- Two policy proposals — one maximizing utilization, one minimizing researcher wait
  time — are both individually defensible, and the platform team has no explicit,
  agreed statement of which goal takes precedence when they conflict.

## Mechanism

GPUs are the scarcest and most expensive resource in an ML platform, which creates a
strong, legitimate pull toward maximizing utilization — an idle GPU is a wasted
expense. But the JD-level goal most ML platforms actually serve is enabling
researchers to iterate quickly, and iteration speed depends on *responsiveness* —
how quickly a researcher can get capacity for a quick experiment — which is a
fundamentally different metric from utilization, and the two are not merely
independent, they actively conflict under realistic conditions.

The conflict is structural: maximizing utilization means keeping capacity as fully
occupied as possible, which means a researcher requesting capacity for a quick
experiment has to wait for something to free up (or be preempted for them, at the cost
described in
[Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md)).
Minimizing wait time means keeping some capacity available and unoccupied, ready to
absorb sudden demand — which is, by definition, capacity that isn't fully utilized at
that moment. There is no scheduling policy that simultaneously achieves 100%
utilization and zero wait time for new demand; any real policy is a specific,
deliberate point on this tradeoff, whether or not it's chosen explicitly.

This matters because the tradeoff, left implicit, tends to drift toward whichever goal
is easier to measure and report — utilization is a simple, visible dashboard number,
while "researcher iteration velocity" is diffuse, harder to quantify, and easy to
deprioritize in a cost-focused review unless someone explicitly defends it. A platform
team that optimizes what's easy to measure, without deliberately weighing it against
the harder-to-measure goal the organization actually cares about, can end up with
excellent utilization numbers and a platform researchers actively avoid — exactly the
failure mode the symptom list describes.

The practical resolution most mature platforms converge on is not choosing one goal
absolutely, but explicitly segmenting capacity by which goal it's optimizing for: a
small, always-on interactive pool (deliberately not fully utilized, buying instant
availability for quick iteration — see
[Fractional GPU Sharing](fractional-gpu-sharing.md) for how to pack it efficiently
anyway) alongside a larger batch/training pool optimized for utilization via
[Hierarchical Fair-Share with Borrowing](hierarchical-fair-share-with-borrowing.md)
and backfill scheduling. This makes the tradeoff explicit and localized rather than a
single, cluster-wide policy trying to serve both goals at once and serving neither
well.

## Real-world sightings

Published engineering accounts of large-scale ML platform design (from organizations
operating shared GPU fleets for research teams) consistently describe this exact
segmentation — a smaller, intentionally-underutilized interactive tier alongside a
utilization-optimized batch tier — as the practical resolution to this tension, framed
explicitly as "we are deliberately sacrificing some peak utilization to guarantee
researcher access," rather than as an oversight or inefficiency to be optimized away.

This is a specific instance of a broader, long-recognized tension in operations
research and queuing theory between utilization and responsiveness — queuing systems
run at very high utilization inherently produce longer wait times, a well-established
result (queue wait time grows non-linearly as utilization approaches its ceiling),
which is the mathematical underpinning for why "just run the cluster hotter" isn't a
free way to improve both metrics simultaneously.

## Mitigations

### Explicitly segmenting capacity by which goal it optimizes for

**What it is:** Maintain a small, deliberately under-utilized interactive/debug pool
for fast access, separate from a larger, utilization-optimized batch/training pool,
rather than one undifferentiated cluster trying to serve both goals.

**Cost:** The interactive pool's idle capacity is a real, ongoing cost that has to be
explicitly justified and defended as buying researcher velocity, not treated as pure
waste.

**How it backfires:** Sizing the interactive pool requires ongoing calibration against
actual researcher demand — too small and it fails to provide the fast-access guarantee
it exists for; too large and it becomes genuinely wasteful capacity that a cost review
will (correctly) flag.

### Naming the tradeoff explicitly in platform goals and reviews

**What it is:** State explicitly, in platform design documentation and cost/capacity
reviews, which goal (utilization or researcher velocity) a given policy or capacity
allocation is optimizing for, rather than letting the tradeoff remain implicit.

**Cost:** Requires the platform team to have an explicit, defensible position on
this tradeoff, rather than deferring the decision indefinitely.

**How it backfires:** None specific — the absence of this explicit framing is
precisely what allows utilization (the easier-to-measure metric) to quietly win by
default, which is the failure mode this mitigation exists to prevent.

### Fractional sharing to improve utilization within the interactive pool

**What it is:** Use fractional GPU sharing (see
[Fractional GPU Sharing](fractional-gpu-sharing.md)) to pack the interactive pool more
efficiently, partially reclaiming some utilization benefit without sacrificing the
pool's fast-access guarantee.

**Cost:** Interactive workloads sharing a GPU fractionally are subject to the
interference risks described in that pattern, which may not be acceptable for all
interactive use cases.

**How it backfires:** Over-relying on fractional sharing to justify shrinking the
interactive pool's dedicated capacity can reintroduce wait-time problems if
interference makes the shared capacity less usable than the dedicated capacity it
replaced.

## Interactions

- [Gang Scheduling vs. Bin-Packing](../../foundations/gang-scheduling-vs-bin-packing.md) —
  the foundational scheduling-mechanics version of this same utilization-versus-
  responsiveness tension.
- [Fractional GPU Sharing](fractional-gpu-sharing.md) — a concrete mechanism for
  partially reconciling the tension within the interactive-capacity segment.
- [Hierarchical Fair-Share with Borrowing](hierarchical-fair-share-with-borrowing.md) —
  the mechanism most directly responsible for utilization efficiency within the
  batch/training capacity segment.

## References

- Kleinrock, L. *Queueing Systems, Volume 1: Theory*. Foundational treatment of the
  utilization-versus-wait-time tradeoff in queuing systems generally.
- Ghodsi, A. et al. *Dominant Resource Fairness: Fair Allocation of Multiple Resource
  Types*. NSDI 2011. Discusses fairness and utilization tradeoffs in shared cluster
  scheduling.
- Jeon, M. et al. *Analysis of Large-Scale Multi-Tenant GPU Clusters for DNN Training
  Workloads*. USENIX ATC 2019. Empirical study of utilization and job-wait-time
  patterns in real, large-scale GPU clusters shared across research teams.
