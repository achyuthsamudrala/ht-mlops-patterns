# Raft Consensus for Cluster State

> **One-liner:** etcd's use of Raft for leader election and log replication is what gives Kubernetes cluster state its consistency guarantee, at the cost of availability during a partition.

## Symptom

- An etcd cluster with an even number of replicas tolerates fewer simultaneous
  failures than expected, or behaves worse under a network split than an odd-sized
  cluster with the same total replica count minus one.
- A network partition that splits etcd replicas into two groups causes the entire
  cluster's write path to stall, not just the minority side — including the majority
  side, until it can re-establish a stable leader.
- etcd leader election, following a leader failure, introduces a brief but measurable
  window during which no writes are accepted anywhere in the cluster.
- Deploying etcd across an even split of availability zones (e.g., exactly half the
  replicas in each of two zones) produces worse partition tolerance than an
  odd-numbered, unevenly-distributed deployment.

## Mechanism

Raft is the consensus algorithm etcd uses to keep multiple replicas agreeing on a
single, ordered sequence of state changes despite individual replica failures or
network issues. Raft works by electing a single leader among the replica set; the
leader is the only replica that accepts client writes, and it replicates each write to
follower replicas, considering the write committed only once a **majority** (quorum)
of the full replica set has durably acknowledged it.

This majority requirement is what gives Raft — and by extension etcd, and by further
extension Kubernetes cluster state — its core safety property: at most one leader can
ever believe it has majority support at any given time, because any two majorities out
of the same replica set must overlap in at least one replica, and that overlapping
replica can't simultaneously support two different leaders. This is precisely what
prevents the split-brain scenario described in
[Consensus & the CAP Tradeoff for Cluster State](../../foundations/consensus-and-the-cap-tradeoff.md):
two independent leaders making conflicting decisions.

The direct, sometimes counterintuitive consequence of requiring a strict majority: a
replica set split evenly by a network partition has **no side** with a majority — both
halves stall, unable to elect a leader or accept writes, until the partition heals.
This is why an *odd* number of replicas is standard practice rather than an arbitrary
convention: an odd-sized replica set can never be split into two exactly equal
halves, so any partition necessarily leaves one side with a genuine majority (even if
just by one replica) while the other has a definite minority — a 5-replica cluster
split 3-2 has a working majority side; a hypothetical 6-replica cluster split 3-3 has
none. Adding an even-numbered replica beyond an already-odd count doesn't improve
fault tolerance at all — it strictly costs more (write latency, replication
overhead) for no additional majority-side guarantee, which is why odd counts (3, 5)
are the standard, not even ones.

Leader election itself, triggered whenever the current leader becomes unreachable
(detected via missed heartbeats), takes a nonzero amount of time — followers have to
detect the leader's absence, hold an election, and reach a new majority agreement on
the new leader — during which no writes can be accepted anywhere in the cluster,
because there's temporarily no leader to accept them. This produces the brief
write-stall window observed after any etcd leader failure, a direct and expected
consequence of the protocol's design, not a bug.

## Real-world sightings

The Raft paper (Ongaro and Ousterhout, "In Search of an Understandable Consensus
Algorithm," USENIX ATC 2014) is the foundational reference for the leader-election
and majority-replication protocol described above, explicitly designed (as its title
suggests) to be more understandable than prior consensus algorithms like Paxos while
providing equivalent safety guarantees.

etcd's own documentation and operational guidance consistently recommends odd-numbered
replica counts (3 or 5, rarely more) and explicitly explains the majority-quorum
reasoning behind this recommendation, along with guidance on distributing replicas
across failure domains (availability zones) in a way that preserves majority
availability under the most likely failure scenarios (a single zone becoming
unreachable).

## Mitigations

### Standardizing on odd-numbered etcd replica counts

**What it is:** Deploy etcd with an odd number of replicas (typically 3 or 5),
never an even number, since even counts add cost without improving fault tolerance.

**Cost:** More replicas (5 versus 3) increases write latency, since more
acknowledgments are needed per write, and increases infrastructure cost.

**How it backfires:** Over-provisioning replica count (5 or more, when 3 would
suffice for the cluster's actual availability requirements) trades away write
latency for a fault-tolerance margin that may not be needed, without the tradeoff
being explicitly evaluated.

### Distributing replicas across failure domains asymmetrically for majority preservation

**What it is:** Place etcd replicas across availability zones or failure domains such
that no single zone failure can take out a majority — e.g., a 3-replica cluster with
replicas in three distinct zones, or a 5-replica cluster distributed so that any
single zone's loss still leaves a majority among the remaining zones.

**Cost:** Requires understanding the actual failure-domain topology available and
designing placement deliberately, rather than defaulting to an arbitrary or
convenient distribution.

**How it backfires:** A placement designed around a specific, understood set of
failure domains can become miscalibrated if the underlying infrastructure's actual
failure-domain boundaries change (a cloud provider's zone topology shifts) without a
corresponding review of etcd replica placement.

### Monitoring leader election frequency as a health signal

**What it is:** Track how often etcd leader elections occur as an operational metric,
since frequent elections indicate either genuine instability (flapping network,
overloaded leader) or a leader-election-timeout configuration mismatched to actual
network characteristics.

**Cost:** Requires etcd-specific monitoring beyond generic cluster health metrics.

**How it backfires:** None specific — the absence of this monitoring means leader
election instability is discovered only through its downstream symptom (periodic
write stalls), which is a noisier, less directly diagnostic signal than tracking
election frequency itself.

## Interactions

- [Consensus & the CAP Tradeoff for Cluster State](../../foundations/consensus-and-the-cap-tradeoff.md) —
  the foundational framing this pattern's specific protocol mechanics are an instance
  of.
- [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md) — Raft's majority-
  replication requirement is the direct mechanism setting etcd's write throughput
  ceiling.
- [Failure as the Steady State at Fleet Scale](../../foundations/failure-as-the-steady-state.md) —
  the general principle that motivates designing explicitly for partition and leader
  failure scenarios rather than assuming they're rare enough to ignore.

## References

- Ongaro, D. and Ousterhout, J. *In Search of an Understandable Consensus Algorithm
  (Extended Version)*. USENIX ATC 2014. The foundational Raft consensus paper.
- etcd Documentation. *Failure Modes* and *Clustering Guide*. Describes majority-
  quorum requirements and replica count/placement recommendations.
- Kubernetes Documentation. *Operating etcd Clusters for Kubernetes*. Discusses
  etcd deployment topology considerations specific to Kubernetes control planes.
