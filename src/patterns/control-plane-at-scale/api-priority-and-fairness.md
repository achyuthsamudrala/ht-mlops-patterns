# API Priority and Fairness

> **One-liner:** Without APF, a single misbehaving client can starve the apiserver for every other client sharing it, regardless of that client's actual priority.

## Symptom

- A single controller or client, misbehaving (a tight reconciliation loop, an
  unbounded retry without backoff) or simply issuing an unusually high volume of
  requests, degrades apiserver responsiveness for every other client in the cluster,
  including ones that should have been unaffected.
- Critical, high-priority controllers (the scheduler, core system controllers)
  experience request timeouts or delays caused by contention from lower-priority,
  less-important clients issuing high request volume.
- apiserver request queue depth grows unboundedly under load, with no mechanism
  differentiating which requests should be prioritized when capacity is exceeded.
- Enabling API Priority and Fairness changes which requests get rejected or delayed
  under load, in a way that requires re-tuning flow-schema configuration to match
  actual traffic patterns.

## Mechanism

Without any request-level prioritization, the apiserver treats all incoming requests
as equally deserving of processing capacity, up to whatever concurrency limit it's
configured with. Under contention — more concurrent requests than the apiserver can
handle — this means capacity is allocated essentially by arrival order and volume, not
by importance: a client issuing requests at high volume (whether legitimately busy or
genuinely misbehaving) can consume a disproportionate share of available capacity,
starving other clients regardless of how important their requests actually are to
overall cluster health.

**API Priority and Fairness (APF)** addresses this by classifying incoming requests
into priority levels and applying fair-queuing *within* each level, so that: requests
at a higher configured priority level are serviced ahead of lower-priority ones under
contention, and within a given priority level, no single client can monopolize that
level's share of capacity — fairness is enforced per-client within each priority
tier, not just globally. This directly protects critical system components (the
scheduler, core controllers) from being starved by less-critical or misbehaving
clients, by ensuring their requests are classified into a priority level insulated
from lower-priority traffic's volume.

The mechanism is a request-admission control system: rather than accepting every
request and hoping capacity suffices, APF makes an explicit admission and
prioritization decision per request, rejecting or queuing lower-priority requests
under contention rather than letting an undifferentiated first-come-first-served
queue degrade service for everyone uniformly (or, worse, disproportionately for
whichever client happens to be least aggressive about retrying).

## Real-world sightings

Kubernetes' own documentation for API Priority and Fairness explicitly describes its
motivation as protecting the apiserver from being overwhelmed by any single client or
controller, and documents the default flow-schema configuration that separates
system-critical traffic (leader election, node heartbeats) from general workload
traffic specifically to prevent exactly the starvation scenario described above.

Kubernetes Enhancement Proposal (KEP) documentation for APF traces its motivation
directly to production incidents where a single misbehaving or high-volume client
degraded apiserver responsiveness cluster-wide, providing a first-party account of
the operational problem APF was built to solve, rather than a purely theoretical
concern.

## Mitigations

### Enabling and correctly configuring APF flow schemas

**What it is:** Ensure APF is enabled (it's on by default in modern Kubernetes
versions) and that flow-schema/priority-level configuration correctly classifies
critical system traffic into protected priority tiers, separate from general
workload traffic.

**Cost:** Default flow-schema configuration may not correctly classify all of a
specific cluster's critical traffic, requiring custom configuration to properly
protect cluster-specific critical controllers or operators.

**How it backfires:** A flow-schema misconfiguration that incorrectly classifies
important traffic into a low-priority tier (or vice versa) can produce the opposite
of its intended effect — actively starving traffic that was supposed to be protected,
in a way that's hard to diagnose because APF itself is functioning correctly, just
against the wrong classification.

### Monitoring per-flow-schema request rejection and queuing metrics

**What it is:** Track APF's own exposed metrics (request rejections and queuing per
priority level and flow schema) as a first-class operational signal, distinguishing
"the apiserver is generally overloaded" from "a specific client is being
appropriately rate-limited by design."

**Cost:** Requires familiarity with APF's specific metrics and configuration model,
which is more operational surface area than a simpler, undifferentiated request
model would require.

**How it backfires:** Without this monitoring, it's easy to misattribute APF-induced
request rejection (working as intended, protecting the cluster) to a general cluster
health problem, leading to unnecessary escalation or misdirected remediation effort.

### Addressing root-cause misbehaving clients, not just mitigating their symptoms

**What it is:** Investigate and fix clients whose request patterns are unusually
aggressive (missing backoff on retries, overly tight reconciliation loops) rather
than relying solely on APF to contain their impact.

**Cost:** Requires identifying and often coordinating a fix with whichever team owns
the misbehaving client, which is slower than simply relying on APF's containment.

**How it backfires:** Relying purely on APF containment without fixing the
underlying misbehaving client means that client continues wasting capacity within its
allotted priority tier — APF prevents it from starving *other* tiers, but doesn't
prevent it from degrading its own tier's fair share for its legitimate peers.

## Interactions

- [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md) — APF protects
  the apiserver's own request-handling capacity, but doesn't directly address etcd
  write-throughput limits, which is a distinct bottleneck further down the request
  path.
- [Controller Reconciliation Storms](controller-reconciliation-storms.md) — a
  reconciliation storm is exactly the kind of high-volume, synchronized request
  pattern APF's fairness mechanism is designed to contain the blast radius of.
- [Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md) —
  a conceptually related fairness mechanism applied to GPU resource scheduling rather
  than apiserver request handling.

## References

- Kubernetes Documentation. *API Priority and Fairness*. Describes the flow-schema and
  priority-level configuration model and its default protections for system-critical
  traffic.
- Kubernetes Enhancement Proposals (KEP). *API Priority and Fairness*. Documents the
  design rationale and motivating production incidents.
- Kubernetes Documentation. *Considerations for Large Clusters*. Discusses apiserver
  request-handling scaling considerations alongside etcd-related limits.
