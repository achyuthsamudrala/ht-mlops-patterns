# Spot-Backed Backfill Under a Budget Cap

> **One-liner:** Large backfills are ideal spot/preemptible workloads precisely because they're resumable and idempotent, letting them opportunistically fill idle capacity under a cost ceiling.

## Symptom

- A large backfill job scheduled on on-demand, guaranteed capacity competes directly
  with higher-priority production workloads for the same GPU fleet, forcing an
  uncomfortable choice between delaying the backfill or impacting production capacity.
- A backfill job that could tolerate interruption is provisioned with the same
  reliability and cost profile as latency-sensitive production inference, paying a
  cost premium for a guarantee the workload doesn't actually need.
- A team avoids running a valuable but non-urgent backfill because there's no
  established, low-friction way to run it opportunistically without competing for
  scarce guaranteed capacity.
- Spot/preemptible capacity sits unused in a cluster with plenty of eligible backfill
  work queued, because the backfill pipeline wasn't actually built to safely run on
  interruptible capacity.

## Mechanism

Spot or preemptible cloud capacity is offered at a substantial discount specifically
because it can be reclaimed by the provider on short notice — the buyer accepts
interruption risk in exchange for a much lower price. This is a poor fit for
workloads that can't tolerate interruption (a request mid-flight in a latency-
sensitive serving path), but an excellent fit for workloads that are, by construction,
safe to interrupt and resume — and content-addressed, idempotent backfill work (see
[Content-Addressed Reprocessing](content-addressed-reprocessing.md)) is exactly this
shape: an interrupted item simply hasn't been marked done yet, and resuming later
picks up exactly where the interruption left off, with no risk of duplicate or
corrupted work regardless of how many times a given unit of work gets interrupted and
retried.

This makes large backfills an unusually good match for spot capacity specifically:
the workload's total completion time is flexible (a backfill completing over a few
extra hours or days due to interruptions is usually acceptable, unlike a latency-
sensitive serving request), the cost savings from spot pricing are substantial for
workloads consuming large amounts of GPU-hours, and the correctness risk from
interruption is genuinely zero if the underlying reconciliation and content-addressing
discipline (see
[Idempotent Incremental Enrichment](../training-data-platforms/idempotent-incremental-enrichment.md))
is implemented correctly.

Running backfill this way also serves a second purpose beyond direct cost savings: it
lets backfill work opportunistically fill capacity that would otherwise sit idle —
spot capacity that other, higher-priority workloads aren't currently using — rather
than requiring dedicated capacity provisioned specifically for backfill. Combined with
an explicit budget cap (a maximum spend or maximum concurrent capacity the backfill
job is allowed to consume, even when more spot capacity is available), this lets
backfill absorb genuinely idle capacity without either competing with production
workloads for guaranteed capacity or running away with unbounded cost simply because
cheap capacity happened to be abundantly available at a given moment.

## Real-world sightings

Cloud providers' own spot/preemptible instance documentation (AWS Spot Instances,
GCP Preemptible/Spot VMs, Azure Spot VMs) explicitly frames fault-tolerant, flexible-
completion-time batch workloads as the intended use case, with interruption handling
(a notice period before reclamation) as the mechanism workloads are expected to build
around — this is first-party guidance directly describing exactly the workload shape
backfill jobs represent.

Published engineering accounts of large-scale ML data enrichment infrastructure
describe exactly this pattern — priority-tiered scheduling with new-data enrichment
at high (often on-demand) priority and full-corpus backfill work running as
lower-priority, spot-backed, budget-capped opportunistic work — as a standard cost-
optimization practice once content-addressed idempotency makes it safe to do so.

## Mitigations

### Explicit interruption handling with checkpointed progress

**What it is:** Handle the cloud provider's interruption notice explicitly (saving
in-flight progress, or relying on content-addressed idempotency to make in-flight loss
harmless) rather than assuming spot capacity behaves like guaranteed capacity.

**Cost:** Requires implementing interruption-notice handling logic, which is
additional engineering work beyond a naive implementation that assumes uninterrupted
execution.

**How it backfires:** If content-addressed idempotency (see
[Content-Addressed Reprocessing](content-addressed-reprocessing.md)) isn't correctly
implemented, relying on it to make interruption harmless is a false assumption — a
job that redoes rather than safely skips already-completed work on resume wastes
exactly the cost savings spot capacity was meant to provide.

### Explicit budget or capacity caps independent of spot availability

**What it is:** Set a maximum spend or maximum concurrent capacity for backfill work,
independent of how much spot capacity happens to be available at any given moment,
preventing an abundance of cheap capacity from producing unexpectedly large total
cost.

**Cost:** A cap set too conservatively leaves genuinely available, cheap capacity
unused, slowing backfill completion unnecessarily.

**How it backfires:** A cap that's never revisited can become miscalibrated as
backfill workload volume or corpus size grows, either unnecessarily constraining a
now-larger legitimate need or (if raised reactively without re-evaluation) drifting
toward an unbounded, unmonitored cost.

### Priority tiering separating new-data enrichment from backfill

**What it is:** Run time-sensitive, new-data enrichment work at higher (often
on-demand) priority, reserving spot-backed opportunistic capacity specifically for
non-urgent, full-corpus backfill work.

**Cost:** Requires the pipeline's scheduling and priority logic to distinguish these
two workload classes explicitly, rather than treating all enrichment work
uniformly.

**How it backfires:** A backfill misclassified as urgent (or an urgent job
misclassified as backfill) gets the wrong reliability/cost tradeoff for its actual
requirements, either overpaying for reliability it didn't need or accepting
interruption risk for work that couldn't actually tolerate it.

## Interactions

- [Content-Addressed Reprocessing](content-addressed-reprocessing.md) — the direct
  precondition that makes spot-backed backfill safe rather than merely cheap.
- [Preemption & Checkpoint-Gated Interruption](../gpu-scheduling/preemption-and-checkpoint-gated-interruption.md) —
  a closely related mechanism (checkpoint-aware interruption handling) applied to
  training jobs rather than batch inference backfills.
- [Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md) —
  the general principle of explicit priority tiering and opportunistic use of idle
  capacity under shared, finite resources, applied here specifically to backfill
  versus urgent enrichment work.

## References

- Amazon Web Services Documentation. *Amazon EC2 Spot Instances*. Describes
  interruption notice mechanics and the intended fault-tolerant, flexible-completion
  workload fit.
- Google Cloud Documentation. *Spot VMs*. Describes preemptible capacity and its
  intended use for interruption-tolerant batch workloads.
- Dean, J. and Ghemawat, S. *MapReduce: Simplified Data Processing on Large Clusters*.
  OSDI 2004. Foundational discussion of fault-tolerant batch processing that spot-
  backed backfill work directly builds on.
