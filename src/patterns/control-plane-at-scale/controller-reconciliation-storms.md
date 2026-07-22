# Controller Reconciliation Storms

> **One-liner:** A shared resync period across many controllers or objects synchronizes their reconciliation into bursts, producing a thundering herd against the apiserver at a predictable cadence.

## Symptom

- apiserver request volume shows a clear, repeating periodicity — sharp spikes at
  regular intervals rather than smoothly distributed load — that doesn't correlate
  with any external event or user activity.
- Cluster responsiveness degrades briefly but predictably at a fixed interval (often
  matching a common default resync period, such as every 30 seconds or every several
  minutes), then recovers until the next occurrence.
- Adding more objects of a given custom resource type makes the periodic spike
  proportionally worse, since more objects mean more simultaneous reconciliation work
  at each resync tick.
- Two independently-developed controllers, each individually well-behaved in
  isolation, produce a combined load spike when their resync periods happen to align,
  even though neither was obviously misbehaving on its own.

## Mechanism

Kubernetes controllers built on the standard controller-runtime pattern use informers
with a periodic **resync period** — in addition to reacting to actual watched events
(an object created, updated, or deleted), the informer periodically re-delivers every
currently-known object to the controller's reconciliation loop, ensuring the
controller re-evaluates its desired-vs-actual state check even if it somehow missed
or mishandled an earlier event. This is a legitimate and important correctness
mechanism — controllers should be robust to missed events, not solely dependent on
never missing one.

The problem is what happens when many controllers, or many objects within one
controller, share the same or closely-aligned resync period: every object's periodic
re-reconciliation fires at the same synchronized moment, producing a burst of
apiserver requests — reads to check current state, potentially writes to reconcile any
drift — all landing within the same narrow time window rather than being smoothly
distributed. This is a **thundering herd**: individually reasonable, low-frequency
work becomes a synchronized spike purely because of shared timing, not because any
individual controller is misbehaving.

This compounds directly with [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md):
a reconciliation storm's burst of reads and writes lands on etcd all at once, and
etcd's write throughput ceiling (bounded by disk fsync latency and Raft replication)
doesn't scale up just because the load arrived in a burst rather than smoothly — the
burst has to be absorbed within etcd's actual capacity, and a large enough
synchronized burst can exceed that capacity even if the same total volume of work,
spread evenly over time, would have been comfortably within it.

## Real-world sightings

controller-runtime's own documentation describes the resync period mechanism and its
correctness rationale explicitly, and Kubernetes community discussions and
troubleshooting guides on control-plane load spikes frequently identify synchronized
resync periods across many controllers or many objects of a custom resource as a
concrete, diagnosable root cause of periodic apiserver load spikes — distinguishable
from genuine, sustained load by their regular, predictable periodicity.

Kubernetes' own core controllers historically jitter their resync periods
specifically to avoid this synchronization problem — adding randomized variation to
the nominal resync interval so that, in aggregate, reconciliation load is smoothed
rather than clustered at fixed synchronized moments, an explicit design response to
the thundering-herd risk of naive fixed-interval resync.

## Mitigations

### Jittering resync periods to desynchronize reconciliation timing

**What it is:** Add randomized variation around a nominal resync interval, so that
many controllers or many objects don't all resync at exactly the same moment, spreading
load smoothly over time instead of clustering it into bursts.

**Cost:** Requires the controller framework or custom controller code to actually
implement jitter, rather than using a fixed interval — not every controller
implementation does this by default.

**How it backfires:** Jitter reduces but doesn't guarantee elimination of
synchronization — with enough independently-jittered controllers, some fraction will
still randomly align at any given moment, so jitter reduces the *severity* and
*frequency* of storms without making them impossible.

### Lengthening resync periods where correctness tolerates it

**What it is:** Increase resync interval for controllers where the correctness
benefit of frequent re-reconciliation is low relative to its load cost, reducing how
often the periodic burst occurs at all.

**Cost:** A longer resync period means a missed or mishandled event takes longer to
be caught and corrected by the next periodic re-reconciliation, trading
responsiveness to drift for reduced load.

**How it backfires:** For a controller managing state where drift correction latency
genuinely matters (a security-relevant reconciliation, for instance), lengthening the
resync period to reduce load can leave a real correctness or security gap open for
longer than acceptable.

### Rate-limiting and request coalescing within the controller itself

**What it is:** Have controllers batch or rate-limit their own outgoing requests
during a reconciliation pass, rather than issuing every object's request
simultaneously and unthrottled.

**Cost:** Adds latency to a single controller's own reconciliation pass, since it's
now deliberately pacing its request rate rather than processing as fast as possible.

**How it backfires:** Rate-limiting tuned too conservatively can make a controller's
own reconciliation pass take so long that it's still processing the current resync
cycle when the next one begins, effectively falling permanently behind.

## Interactions

- [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md) — the underlying
  resource whose throughput ceiling a reconciliation storm's burst load can exceed,
  even when average load is well within capacity.
- [API Priority and Fairness](api-priority-and-fairness.md) — APF's fair-queuing can
  contain a reconciliation storm's cluster-wide blast radius, though it doesn't
  eliminate the storm itself.
- [Operator Reconciliation Idempotency](../cluster-services/operator-reconciliation-idempotency.md) —
  the resync mechanism this pattern describes is precisely what makes idempotent
  reconciliation robust to missed events in the first place.

## References

- Kubernetes SIG API Machinery. *controller-runtime Documentation*. Describes the
  informer resync period mechanism and its correctness rationale.
- Kubernetes Documentation. *Writing Controllers*. Discusses resync period
  configuration and jittering practices for well-behaved controllers.
- Kubernetes Documentation. *API Priority and Fairness*. Describes the complementary
  mechanism for containing the blast radius of synchronized request bursts.
