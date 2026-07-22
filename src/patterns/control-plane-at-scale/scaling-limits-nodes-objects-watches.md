# Scaling Limits: Nodes vs. Objects vs. Watches

> **One-liner:** Documented Kubernetes scaling limits are really three separate limits — node count, object count, and watch count — and the one that bites first depends on workload shape, not raw cluster size.

## Symptom

- A cluster well below its documented maximum node count still experiences
  control-plane degradation, traced to an unusually high object count (many custom
  resources, many pods per node) rather than node count itself.
- A cluster with modest node and object counts but many controllers or operators
  maintaining watches on frequently-changing resources shows control-plane strain
  that a similarly-sized cluster with fewer watchers doesn't.
- Capacity planning based solely on "we're at X% of the documented node limit"
  misses a real, active scaling problem because the actual constraint was object count
  or watch fan-out, not node count.
- Two clusters with identical node counts show very different control-plane health,
  traced to one running a workload with far more custom resources or far more active
  watches per object than the other.

## Mechanism

Kubernetes' commonly-cited scaling numbers (a maximum node count, most prominently)
suggest a single, simple ceiling, but the actual constraints are better understood as
three separate, somewhat independent limits, each stressing a different part of the
control plane, and the one that binds first for a given cluster depends entirely on
that cluster's specific workload shape rather than on node count alone.

**Node count** stresses the apiserver and kubelet-facing control loops directly —
more nodes means more heartbeats, more node-status updates, more scheduling decisions
to make. This is the most commonly cited limit, but it's specifically a limit on
*node-related* control-plane load, not a general proxy for total cluster load.

**Object count** stresses etcd's storage and write throughput (see
[etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md)) somewhat
independently of node count — a cluster with relatively few nodes but a very large
number of pods per node, or a very large number of custom resource instances, can
stress etcd's storage and query performance without stressing node-count-related
limits at all. Object count and node count are correlated in typical clusters but not
strictly coupled — workload shape determines the actual ratio.

**Watch count** stresses etcd's watch fan-out and the apiserver's watch cache
specifically — a cluster with many controllers or operators, each maintaining watches
on potentially broad sets of resources, multiplies the fan-out cost of every write to
a watched resource type. A cluster can have modest node and object counts but a large
number of controllers each watching broadly, producing watch-fan-out-driven
degradation that neither of the other two limits would predict.

Because these three limits stress different underlying mechanisms, a cluster can be
comfortably within documented node-count limits while still hitting real,
observable control-plane degradation from object count or watch count — which is
precisely why capacity planning based on a single headline number (node count)
systematically under-predicts risk for workloads whose actual bottleneck is one of
the other two dimensions.

## Real-world sightings

Kubernetes' own "Considerations for Large Clusters" documentation explicitly
enumerates multiple distinct scalability dimensions (not just node count) including
guidance on object counts and namespaces, reflecting official acknowledgment that a
single node-count number doesn't fully characterize a cluster's actual scaling
headroom.

Kubemark, a Kubernetes project component specifically built for simulating
large-scale clusters for control-plane testing without provisioning real nodes,
exists precisely because testing control-plane scaling requires exercising these
different dimensions (object count, watch count, request rate) independently of
actually provisioning proportional real compute — a project-level acknowledgment
that scaling behavior needs to be tested across multiple axes, not validated by
node count alone.

## Mitigations

### Capacity planning across all three dimensions, not node count alone

**What it is:** Track and plan capacity headroom for object count and watch count
specifically, alongside node count, rather than treating node count as a sufficient
proxy for overall cluster scaling risk.

**Cost:** Requires instrumentation and monitoring for object count (per resource
type) and active watch count, which isn't as commonly dashboarded by default as node
count and basic resource utilization.

**How it backfires:** Even with this broader tracking, the relationship between
object/watch count and actual control-plane health isn't perfectly linear or
predictable, so capacity planning based on these metrics is still an estimate, not a
guarantee — real testing under representative load remains necessary.

### Testing at representative scale using cluster simulation tooling

**What it is:** Use tooling like Kubemark to simulate large-scale object counts,
watch counts, and node counts independently, validating control-plane behavior under
realistic load shapes before those loads occur in production.

**Cost:** Requires setting up and maintaining simulation infrastructure and
representative test workloads, which is nontrivial ongoing engineering investment.

**How it backfires:** Simulated load, however carefully constructed, may not
perfectly replicate the specific request patterns and timing correlations of real
production workloads (see
[Controller Reconciliation Storms](controller-reconciliation-storms.md) for a failure
mode driven by timing correlation specifically, which is hard to simulate accurately
without knowing to model it).

### Auditing and reducing unnecessary watch breadth

**What it is:** Review controllers and operators for watches scoped broader than
necessary (watching an entire resource type cluster-wide when a narrower,
namespace-scoped or label-selected watch would suffice), reducing watch-fan-out cost
directly.

**Cost:** Requires auditing controller code and configuration across however many
controllers are deployed, and narrowing a watch's scope requires understanding
whether that controller genuinely needs the broader visibility.

**How it backfires:** A watch narrowed too aggressively can cause a controller to
miss events on resources it actually needed to react to, trading a control-plane
load problem for a correctness problem.

## Interactions

- [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md) — object count and
  watch count both stress etcd specifically, distinct from node count's stress on
  apiserver/kubelet-facing control loops.
- [Controller Reconciliation Storms](controller-reconciliation-storms.md) — a
  concrete failure mode where watch count and object count combine with timing
  correlation to produce load beyond what either metric alone would predict.
- [API Priority and Fairness](api-priority-and-fairness.md) — a mitigation that helps
  contain the *symptom* of hitting any of these three limits, without addressing
  which specific limit is actually binding.

## References

- Kubernetes Documentation. *Considerations for Large Clusters*. Enumerates multiple
  distinct scalability dimensions beyond node count.
- Kubernetes SIG Scalability. *Kubemark*. Describes cluster simulation tooling for
  testing control-plane scaling independently of real node provisioning.
- Kubernetes Documentation. *API Concepts — Efficient Detection of Changes*. Describes
  watch mechanics and their scaling implications.
