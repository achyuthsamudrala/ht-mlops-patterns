# Operator Reconciliation Idempotency

> **One-liner:** A controller that isn't safe to replay, restart, or run concurrently with itself will eventually corrupt the state it's supposed to manage.

## Symptom

- A controller restart (deployment, crash-and-recover, or leader election handoff)
  produces duplicate side effects — an external resource created twice, a
  notification sent twice — for work that should have happened exactly once.
- Two replicas of a controller, briefly both believing themselves to be leader during
  a leader-election transition, take conflicting actions on the same managed
  resource.
- A reconciliation loop that's interrupted partway through a multi-step external
  operation (create resource A, then B, then C) leaves the managed resource in an
  inconsistent state if resumed from the beginning rather than from where it actually
  left off.
- Manually re-triggering reconciliation for an object (a common debugging step)
  produces a different, unwanted outcome instead of safely re-confirming the already-
  correct state.

## Mechanism

Kubernetes' controller pattern is built entirely on the assumption that a
reconciliation function will be called repeatedly, unpredictably, and sometimes
concurrently — not just when something changes, but on every periodic resync (see
[Controller Reconciliation Storms](../control-plane-at-scale/controller-reconciliation-storms.md)),
after every restart, and potentially by more than one replica briefly during a
leader-election transition. A reconciliation function that isn't safe to be called
this way — one that assumes it's being called exactly once, in order, by exactly one
process — will eventually violate that assumption and produce incorrect behavior,
because the platform genuinely does call it this way in the normal course of
operation, not just as an edge case.

**Idempotency** is the core property that makes this safe: calling reconciliation
again, with the same observed state, should produce the same result as calling it
once — not a duplicated side effect, not a conflicting action. The standard way to
achieve this is to make reconciliation compute a desired state from the current spec,
compare it against currently observed actual state, and only take action on the
*difference* — rather than unconditionally executing a sequence of steps every time
it's invoked. A reconciliation function structured this way naturally tolerates
replay: if actual state already matches desired state, there's nothing to do, and
calling it again is a safe no-op.

**Concurrency safety** is a related but distinct requirement: during a leader-election
transition, there's a brief window where two replicas might both believe themselves to
be the active leader (this is generally avoided by design, but transiently possible
under certain failure and timing conditions), and a reconciliation function that
assumes single-writer exclusivity can produce conflicting actions if genuinely invoked
concurrently. Using optimistic concurrency (resource version checks) on writes, so a
stale-state write is rejected rather than silently overwriting a newer one, is the
standard defense here — the same mechanism etcd's own Raft-based consistency (see
[Raft Consensus for Cluster State](../control-plane-at-scale/raft-consensus-for-cluster-state.md))
is built on, applied at the application layer.

**Partial-failure safety** requires that a reconciliation function interrupted mid-way
through a multi-step operation leave the system in a state from which the *next*
invocation can correctly determine what's still needed — not assume it's starting
fresh, and not assume the prior invocation's partial work is either fully complete or
fully absent. This usually means each step's completion needs to be independently
observable (in the resource's own status, or in the state of the external resources
themselves) rather than tracked only in the controller process's own transient memory.

## Real-world sightings

Kubernetes' own documentation on writing controllers explicitly frames idempotent,
level-triggered reconciliation (react to current state, not to the specific event
that triggered the call) as the fundamental design principle controllers should
follow, explicitly contrasting it with edge-triggered designs that assume exactly-once,
in-order event delivery — a contrast the documentation makes precisely because the
platform doesn't actually provide that guarantee.

The kubebuilder book (the standard practical guide to building Kubernetes operators)
devotes substantial attention to idempotent reconciliation design and optimistic
concurrency via resource versions, reflecting that this is one of the most common
sources of subtle correctness bugs in real-world operator implementations —
common enough to warrant dedicated, explicit guidance rather than being treated as an
obvious or automatic property of any reconciliation loop.

## Mitigations

### Structuring reconciliation as desired-vs-actual-state diffing

**What it is:** Compute the difference between desired state (from spec) and observed
actual state on every invocation, acting only on that difference, rather than
executing an unconditional sequence of steps.

**Cost:** Requires the ability to actually observe current state accurately (querying
external systems where relevant), which is more implementation work than simply
executing a fixed sequence of actions.

**How it backfires:** If observed "actual state" is itself unreliable or stale (a
cached or eventually-consistent view of an external system), diffing against it can
produce incorrect decisions — this mitigation's correctness depends on the actual-state
observation being trustworthy.

### Optimistic concurrency via resource version checks

**What it is:** Condition writes on the resource version last observed, so a write
based on stale state is rejected rather than silently succeeding and overwriting a
concurrent, newer change.

**Cost:** Requires handling write conflicts explicitly (typically by re-reading
current state and retrying), adding complexity compared to unconditional writes.

**How it backfires:** A retry loop for handling version conflicts that isn't bounded
or backed off appropriately can itself become a source of load, particularly under
the kind of synchronized reconciliation storm described in
[Controller Reconciliation Storms](../control-plane-at-scale/controller-reconciliation-storms.md).

### Making multi-step progress independently observable

**What it is:** Record each step's completion in a way the next reconciliation
invocation can independently verify (via status fields, or by directly checking the
state of external resources), rather than relying on in-memory tracking within a
single controller process invocation.

**Cost:** Adds status-tracking overhead (more fields to maintain, more writes to
persist progress) compared to a simpler, non-resumable implementation.

**How it backfires:** Status fields that are updated but not actually consulted by
the next reconciliation pass provide the illusion of resumability without the
substance — this mitigation only works if the tracked progress is actually read and
acted on, not just recorded.

## Interactions

- [Controller Reconciliation Storms](../control-plane-at-scale/controller-reconciliation-storms.md) —
  the resync mechanism that makes idempotent reconciliation a hard requirement rather
  than a nice-to-have, since resync guarantees repeated invocation under normal
  operation.
- [Idempotent Incremental Enrichment](../training-data-platforms/idempotent-incremental-enrichment.md) —
  the same reconcile-observed-against-desired-state pattern applied to ML data
  enrichment rather than Kubernetes cluster resources.
- [Owner References & Garbage Collection](owner-references-and-garbage-collection.md) —
  correct owner reference management depends on idempotent reconciliation to avoid
  creating duplicate owned resources on replay.

## References

- Kubernetes Documentation. *Writing Controllers*. Describes level-triggered,
  idempotent reconciliation as the fundamental controller design principle.
- The Kubebuilder Book. *Designing an API*. Discusses idempotent reconciliation and
  optimistic concurrency practices for custom operators.
- Ongaro, D. and Ousterhout, J. *In Search of an Understandable Consensus Algorithm
  (Extended Version)*. USENIX ATC 2014. The optimistic-concurrency-adjacent
  consistency reasoning this pattern's resource-version mechanism echoes at the
  application layer.
