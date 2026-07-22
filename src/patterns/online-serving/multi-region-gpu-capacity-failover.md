# Multi-Region GPU Capacity Failover

> **One-liner:** GPU scarcity makes regional capacity exhaustion a real availability risk, not just a hypothetical one, which is why serving systems increasingly need multi-region failover for capacity, not just for uptime.

## Symptom

- A serving system architected for traditional multi-region failover (protecting
  against a region-level outage) still experiences availability problems when a
  single region simply runs out of available GPU capacity of the required type,
  even though the region itself hasn't "failed" in the traditional sense.
- Scaling up a serving endpoint during a demand spike fails or is significantly
  delayed, not because of a software or infrastructure fault, but because the region
  genuinely has no more of the requested GPU type available to provision.
- A capacity-exhaustion event in one region has no automated failover path to a
  different region with available capacity, because the failover architecture was
  built assuming region failures are the primary risk, not capacity exhaustion within
  an otherwise-healthy region.
- Different regions show meaningfully different GPU type availability at different
  times, and a serving architecture pinned to a single region misses opportunities to
  route around temporary capacity constraints elsewhere.

## Mechanism

Traditional multi-region architecture is built to survive a region becoming
unavailable — an outage, a natural disaster, a provider-side failure — and routes
traffic to a healthy region when this happens. GPU-backed serving introduces a
distinct, additional failure mode that this traditional model doesn't directly
address: a region can be otherwise fully healthy and available, yet still be unable
to serve additional demand because the specific GPU type required simply isn't
available in that region at that moment, due to overall demand across all of that
region's tenants exceeding available supply.

This is a meaningfully different risk profile from a region outage: it's not binary
(the region isn't "down"), it's a capacity-availability constraint that can vary over
time and by GPU type, and unlike a region outage, it can potentially be worked around
by routing to a *different* region that happens to have available capacity of the
needed type, even if the original region is otherwise perfectly healthy. A failover
architecture built purely around detecting region health and redirecting traffic on
outage doesn't naturally handle this case, because from that architecture's
perspective, an otherwise-healthy but capacity-exhausted region looks the same as a
healthy region that should keep receiving traffic.

Addressing this requires treating GPU capacity availability, per region and per GPU
type, as an explicit signal the serving architecture actively monitors and routes
around — not just region health in the traditional sense. This is a more
fine-grained and more dynamically-changing signal than simple region up/down status,
and building failover logic that correctly incorporates it requires genuinely
different monitoring and routing logic than traditional multi-region disaster
recovery architecture assumes.

## Real-world sightings

Cloud providers' own documentation on GPU capacity reservations (AWS Capacity Blocks,
GCP and Azure's reservation mechanisms) explicitly acknowledges GPU capacity as a
constrained, sometimes unavailable-on-demand resource distinct from general compute
capacity, motivating reservation mechanisms specifically because on-demand
availability of specific GPU types cannot be assumed the way general-purpose compute
availability typically can.

Published engineering accounts from organizations operating large-scale, GPU-backed
production inference describe multi-region and, in some cases, multi-cloud capacity
strategies explicitly motivated by GPU scarcity risk, distinct from and in addition to
traditional disaster-recovery motivations for multi-region architecture — reflecting
that this is a recognized, real operational concern at organizations operating at
sufficient GPU-serving scale.

## Mitigations

### Monitoring per-region, per-GPU-type capacity availability as a first-class signal

**What it is:** Track actual available capacity by region and GPU type as an
explicit operational metric, distinct from general region health monitoring, feeding
this into routing and scaling decisions.

**Cost:** Requires building or integrating capacity-availability monitoring, which
isn't typically part of standard region-health monitoring tooling.

**How it backfires:** Capacity availability can change faster than a monitoring
system's polling or reporting interval can track accurately, meaning routing
decisions based on this signal can still be acting on somewhat stale information
during rapidly-changing demand conditions.

### Multi-region routing logic incorporating capacity, not just health

**What it is:** Extend traffic routing and autoscaling logic to consider GPU
capacity availability by region and type, not just traditional region health status,
allowing traffic to route to a different region specifically when the primary
region's required capacity is constrained.

**Cost:** Requires more sophisticated routing logic than simple health-check-based
failover, and cross-region routing introduces its own latency and data-locality
considerations that pure single-region serving doesn't have to address.

**How it backfires:** Cross-region failover for capacity reasons can introduce
latency penalties (serving from a farther region) or data-locality complications
(model weights, cached state, or data dependencies not replicated to the failover
region) that a simple health-based failover to a pre-provisioned standby region
wouldn't necessarily have to contend with.

### Reserved capacity for baseline, opportunistic multi-region for burst

**What it is:** Use reserved capacity mechanisms (capacity blocks, committed-use
reservations) to guarantee baseline GPU availability in a primary region, while
relying on multi-region flexibility specifically for burst demand beyond what
reserved capacity covers.

**Cost:** Reserved capacity has its own cost structure (often requiring commitment
in exchange for guaranteed availability), and sizing the reservation correctly
requires reasonably accurate baseline demand forecasting.

**How it backfires:** A reservation sized for historical baseline demand can become
insufficient as baseline demand grows, silently increasing reliance on
opportunistic multi-region capacity for what should have been routine, reserved-
capacity-covered demand.

## Interactions

- [Cold Starts vs. Warm Pools](cold-starts-vs-warm-pools.md) — capacity exhaustion in
  a region directly compounds cold-start risk, since a cold-started scale-up event
  that can't find capacity locally has no path to complete without cross-region
  failover.
- [The Managed vs. Build Tradeoff](../../foundations/the-managed-vs-build-tradeoff.md) —
  multi-cloud capacity strategies (an extension of multi-region) trade additional
  build complexity for reduced single-provider capacity risk.
- [Hierarchical Fair-Share with Borrowing](../gpu-scheduling/hierarchical-fair-share-with-borrowing.md) —
  a related but distinct capacity-management concern, operating within a single
  region/cluster's tenant allocation rather than across regions.

## References

- Amazon Web Services Documentation. *Amazon EC2 Capacity Blocks for ML*. Describes
  GPU capacity reservation mechanisms motivated by genuine on-demand availability
  constraints.
- Google Cloud Documentation. *Reservations for Compute Engine*. Describes capacity
  reservation mechanisms for GPU and other constrained compute resources.
- Barroso, L. A., Hölzle, U., and Ranganathan, P. *The Datacenter as a Computer*.
  Discusses capacity planning and availability considerations for large-scale
  distributed infrastructure generally, applicable to the GPU-scarcity-specific case
  described here.
