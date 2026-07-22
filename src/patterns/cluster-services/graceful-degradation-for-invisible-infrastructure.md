# Graceful Degradation for Invisible Infrastructure

> **One-liner:** Cluster services that every workload depends on but nobody directly monitors need to degrade gracefully under load, because a hard failure there takes down everything at once.

## Symptom

- A cluster service almost nobody thinks about day-to-day (DNS, an admission
  webhook, an internal certificate authority) experiences an overload event, and the
  resulting outage looks like a broad, unexplained cluster-wide incident rather than a
  clearly attributable single-component failure.
- Post-incident investigation reveals the root-cause service had no dedicated
  monitoring, capacity planning, or on-call ownership, despite being a hard dependency
  for effectively every workload in the cluster.
- A service designed to fail cleanly (return an error) under overload instead fails in
  a way that cascades — clients retrying aggressively against an already-overloaded
  service, worsening rather than containing the problem.
- Capacity planning reviews consistently focus on visible, directly-owned application
  services and never surface the shared infrastructure layer as a distinct
  capacity-planning concern.

## Mechanism

Certain cluster services occupy a specific, dangerous position: they're depended upon,
transitively, by nearly every workload in the cluster, but they're rarely
*directly* used or thought about by application teams — DNS (see
[Service Discovery at Fleet Scale](service-discovery-at-fleet-scale.md)), admission
webhooks, internal certificate authorities, and similar shared infrastructure fall
into this category. Because no single team "owns" the felt experience of depending on
these services (everyone depends on them equally and indirectly), they can end up
under-monitored and under-capacity-planned relative to their actual criticality —
nobody's dashboard highlights them as a top dependency, because they don't appear as
an explicit dependency in any single team's own service map, even though they're
implicitly present in all of them.

This creates an asymmetry between a service's *actual* criticality (extremely high,
since its failure affects everything) and its *perceived* criticality (often low,
since it's invisible in day-to-day operations) — and capacity planning, monitoring
investment, and on-call ownership tend to follow perceived rather than actual
criticality unless someone deliberately corrects for the gap.

The consequence when this gap isn't corrected: these services are more likely to be
under-provisioned relative to their true load, and — because they weren't designed
with their true criticality in mind — more likely to fail in ways that cascade rather
than degrade gracefully. A service designed assuming low, well-understood load might
not implement backpressure, load shedding, or graceful error responses under overload
— it might simply become slow or start failing requests outright, and clients that
weren't designed to handle *that* dependency failing (because nobody thought of it as
a dependency they needed to handle failure for) can retry aggressively or fail in
poorly-contained ways themselves, compounding the original overload into a
cluster-wide cascading failure.

Graceful degradation for this class of service means explicitly designing for its
true, transitive criticality: capacity planned for actual (not just directly-observed)
demand, explicit load shedding or backpressure under overload rather than silent
degradation into cascading failure, and monitoring and on-call ownership assigned
deliberately rather than left as an ownership gap nobody explicitly claims.

## Real-world sightings

Google's SRE workbook and related SRE literature explicitly discuss the general
pattern of shared, transitively-depended-upon infrastructure services warranting
disproportionate reliability investment relative to their visibility, framing this as
a deliberate organizational and technical practice rather than an automatic
consequence of a service's technical design — visibility and ownership have to be
actively assigned, not assumed to follow naturally from criticality.

CoreDNS's own operational guidance (see also
[Service Discovery at Fleet Scale](service-discovery-at-fleet-scale.md)) and
Kubernetes admission webhook documentation both explicitly discuss failure-mode
configuration (fail-open versus fail-closed behavior for webhooks, in particular) as a
deliberate design choice with real tradeoffs — an explicit acknowledgment that these
services' failure behavior has to be a considered design decision, not a default left
unexamined.

## Mitigations

### Explicitly identifying and assigning ownership for transitively-depended-upon services

**What it is:** Conduct a deliberate exercise identifying which cluster services are
transitively depended upon by effectively everything, and explicitly assign
monitoring, capacity planning, and on-call ownership for each, rather than assuming
ownership emerges naturally.

**Cost:** Requires organizational effort to identify these services (they're
invisible by nature, so finding them takes deliberate investigation) and requires
someone to take on ownership responsibility for infrastructure they may not have
built themselves.

**How it backfires:** An ownership assignment made once, at a point in time, can
become stale as new shared infrastructure is introduced later without a
corresponding review — the invisibility problem this mitigation addresses can
recur for newly-introduced shared services if the identification process isn't
repeated periodically.

### Explicit load shedding and backpressure design for shared services

**What it is:** Design shared infrastructure services to explicitly shed load or
apply backpressure under overload — returning fast, clear errors or throttling
signals rather than degrading into slow, cascading failure.

**Cost:** Requires deliberate engineering investment in failure-mode design for a
service that might otherwise "just work" under normal load without this
investment being visibly necessary.

**How it backfires:** Load-shedding thresholds tuned incorrectly (too aggressive) can
cause a service to shed load and return errors under load that it could actually have
handled, trading a false-positive failure for the cascading-failure risk it was meant
to prevent — the threshold has to be genuinely well-calibrated, not just present.

### Capacity planning based on transitive, not just direct, demand

**What it is:** Size shared infrastructure capacity based on aggregate demand across
every workload that transitively depends on it, not based on whatever demand happens
to be directly visible or reported by any single team.

**Cost:** Requires visibility into cluster-wide, aggregate demand patterns, which is
more work to establish than capacity planning based on a single team's own reported
usage.

**How it backfires:** Capacity planned for today's aggregate transitive demand can
still be outpaced by growth if the planning process isn't repeated regularly — this
is the same "static plan, growing demand" failure mode that recurs across many
patterns in this guide, applied here to invisible shared infrastructure specifically.

## Interactions

- [Service Discovery at Fleet Scale](service-discovery-at-fleet-scale.md) — the
  canonical, concrete example of a transitively-critical, often under-monitored
  shared service this pattern generalizes from.
- [etcd as the Hidden Bottleneck](../control-plane-at-scale/etcd-as-the-hidden-bottleneck.md) —
  another example of infrastructure whose criticality is much higher than its typical
  day-to-day visibility would suggest.
- [Backpressure in GPU Batch Inference](../offline-inference/backpressure-in-gpu-batch-inference.md) —
  the general principle of explicit backpressure over silent degradation, applied here
  at the shared-infrastructure layer rather than a specific batch pipeline.

## References

- Google. *The Site Reliability Engineering Workbook*. Discusses reliability
  investment allocation for shared, transitively-depended-upon infrastructure.
- Kubernetes Documentation. *Admission Webhooks — Failure Policy*. Discusses explicit
  fail-open versus fail-closed design tradeoffs for shared admission infrastructure.
- CoreDNS Documentation. *Operational Considerations*. Discusses capacity planning
  and failure-mode design for cluster-wide DNS infrastructure.
