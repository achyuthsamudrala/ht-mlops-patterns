# Service Discovery at Fleet Scale

> **One-liner:** DNS-based service discovery that works fine at moderate scale can become a cluster-wide single point of failure once query volume or record churn grows enough.

## Symptom

- DNS resolution latency for in-cluster service lookups rises noticeably as cluster
  size (pod count, service count) grows, even though the DNS service's own resource
  allocation looks adequate.
- A DNS service overload event causes cascading failures across seemingly unrelated
  workloads, because every one of them depends on DNS resolution for their own
  upstream dependencies.
- High pod churn (frequent scaling events, rolling deployments) produces a
  corresponding spike in DNS query volume and cache invalidation, straining the DNS
  service specifically during exactly the periods when cluster activity is already
  elevated.
- Client-side DNS caching configuration (or its absence) produces wildly different
  query loads on the cluster DNS service for functionally similar workloads.

## Mechanism

Kubernetes' default service discovery mechanism resolves service names to IP
addresses via cluster-internal DNS (CoreDNS, in modern clusters), and virtually every
workload depends on this resolution path to reach any other service — which means the
DNS service, however unglamorous and rarely thought about, is genuinely
load-bearing infrastructure for the entire cluster, not a peripheral concern.

At moderate scale, this works comfortably: DNS query volume is low relative to the
service's capacity, and caching (both client-side and within CoreDNS itself)
absorbs most of the repeat-query load. At larger scale, several factors compound: raw
query volume grows with pod and service count; cache effectiveness can degrade if
TTLs are short relative to actual query frequency, or if client-side caching isn't
configured at all (forcing every lookup to hit the cluster DNS service fresh); and pod
churn (frequent scale events, rolling updates) both increases query volume (new pods
resolving their dependencies on startup) and increases the *rate* of cache
invalidation, since DNS records for churning pods and services change frequently.

The failure mode this produces is disproportionately severe precisely because DNS is
so universally depended upon: a DNS service that becomes overloaded or slow doesn't
just fail its own requests, it degrades or breaks every workload's ability to reach
any dependency, producing what looks like a broad, mysterious cluster-wide outage
rather than an obviously-attributable single-component failure — the actual root
cause (DNS) can be non-obvious precisely because its failure manifests everywhere at
once rather than in one identifiable place.

**eBPF-based service discovery** (as implemented by Cilium and similar CNIs) offers an
alternative to the traditional DNS-plus-kube-proxy path: routing decisions can be made
directly in the kernel's networking path via eBPF programs, without necessarily
requiring a DNS lookup and separate proxy hop for every connection, which can reduce
both the load on the DNS service and the latency of the service-discovery path
itself. This isn't a universal replacement for DNS-based discovery (DNS is still
usually involved for the initial name resolution), but it changes the performance
characteristics and scaling behavior of the overall service-connectivity path.

## Real-world sightings

CoreDNS's own documentation and operational guidance explicitly discuss caching
configuration, autoscaling (the `cluster-proportional-autoscaler` pattern, which
scales CoreDNS replica count proportionally to cluster node count), and query-volume
capacity planning as first-class operational concerns — reflecting that DNS scaling
at cluster size is a well-recognized, non-trivial operational problem rather than a
"set it and forget it" default.

Cilium's documentation on "Kubernetes Without kube-proxy" and its eBPF-based
datapath explicitly frames its design around reducing the latency and scaling
limitations of the traditional iptables/DNS-based service discovery and routing path,
citing scaling problems with iptables rule proliferation and connection tracking at
large cluster sizes as direct motivation.

## Mitigations

### Autoscaling DNS service capacity proportional to cluster size

**What it is:** Scale the number of DNS service replicas based on cluster size
(node count, or a similar proxy) rather than a fixed replica count, using something
like the cluster-proportional-autoscaler pattern.

**Cost:** Requires deploying and maintaining the autoscaling mechanism itself, and
choosing an appropriate scaling ratio requires understanding actual query-volume
growth relative to cluster size for the specific workload mix in use.

**How it backfires:** A scaling ratio tuned for typical query patterns can be
insufficient for workloads with unusually high per-pod query volume (frequent,
uncached lookups), since proportional scaling by node count doesn't directly account
for actual query rate.

### Configuring effective client-side and CoreDNS caching

**What it is:** Ensure client-side DNS caching is properly configured (many
language runtimes and container base images have suboptimal defaults) and CoreDNS
cache TTLs are tuned to actual record change frequency, reducing repeat-query load on
the DNS service.

**Cost:** Longer cache TTLs trade DNS service load for staleness — a cached, stale DNS
record can point to a since-removed or since-changed service endpoint for up to the
TTL duration.

**How it backfires:** Aggressive caching tuned to minimize DNS load can mask or delay
detection of legitimate service topology changes (a service migrating, a pod being
replaced), producing connection failures to stale endpoints that persist longer than
expected.

### eBPF-based service routing to reduce dependence on the DNS hot path

**What it is:** Adopt an eBPF-based CNI (Cilium or equivalent) that can handle some
service routing decisions in the kernel networking path, reducing load on and latency
through the traditional DNS-plus-proxy path.

**Cost:** Requires migrating to a specific CNI implementation, which is a
significant infrastructure change with its own operational learning curve and
migration risk.

**How it backfires:** eBPF-based routing changes the failure and debugging model
compared to traditional iptables/DNS-based routing — operators familiar with the
traditional model need to learn new tooling and mental models to debug connectivity
issues in the new system, and that learning curve itself is a real transition cost.

## Interactions

- [etcd as the Hidden Bottleneck](../control-plane-at-scale/etcd-as-the-hidden-bottleneck.md) —
  DNS record updates (from service/endpoint changes) ultimately trace back to etcd
  writes and watches, connecting DNS scaling concerns to the broader control-plane
  scaling picture.
- [Graceful Degradation for Invisible Infrastructure](graceful-degradation-for-invisible-infrastructure.md) —
  DNS is the canonical example of infrastructure every workload depends on invisibly,
  making graceful degradation under load especially important for it specifically.
- [Controller Reconciliation Storms](../control-plane-at-scale/controller-reconciliation-storms.md) —
  a synchronized burst of pod churn (a mass rolling deployment) drives simultaneous
  spikes in both control-plane load and DNS query/invalidation load.

## References

- CoreDNS Documentation. *Scaling CoreDNS* and *Caching Plugin*. Describes
  proportional autoscaling and cache tuning for cluster DNS service capacity.
- Cilium Documentation. *Kubernetes Without kube-proxy*. Describes eBPF-based service
  routing and its motivation relative to traditional DNS/iptables-based discovery.
- Kubernetes Documentation. *DNS for Services and Pods*. Describes the default
  service discovery mechanism and its scaling considerations.
