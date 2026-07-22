# Consensus & the CAP Tradeoff for Cluster State

> **Kubernetes' control plane deliberately chooses consistency over availability
> during a network partition, and nearly every control-plane failure mode in this
> guide is a consequence of that one design choice.** Understanding why etcd uses
> Raft, and what Raft actually guarantees, explains far more about cluster behavior
> under stress than memorizing individual failure symptoms would.

## What etcd's consensus protocol guarantees

etcd, the key-value store backing Kubernetes' entire cluster state, uses the Raft
consensus algorithm to keep multiple etcd replicas agreeing on a single, consistent
sequence of state changes even as individual replicas fail or the network between them
degrades. Raft works by electing a leader among the replicas; the leader accepts
writes, replicates them to a majority of replicas before acknowledging success, and a
new leader is elected if the current one becomes unreachable.

The critical guarantee this produces: a write is only considered committed once a
majority (quorum) of replicas has durably recorded it. This means etcd can tolerate
losing a minority of replicas without losing any committed data or electing two
conflicting leaders simultaneously — but it also means that if a network partition
splits replicas such that no side has a majority, etcd stops accepting writes
entirely on both sides, rather than risking two independent leaders making
inconsistent decisions. This is a direct, deliberate instance of the CAP theorem's
tradeoff: under a partition, etcd chooses **consistency** over **availability** — it
would rather refuse writes than risk two different, disagreeing versions of the truth.

## Why this is the right choice for cluster state specifically

Cluster state — which pods are scheduled where, which nodes exist, what a
deployment's desired replica count is — is exactly the kind of data where inconsistent,
conflicting versions are far more dangerous than temporary unavailability. Two
schedulers, each believing they have sole authority and placing pods based on a
partitioned, stale view of cluster state, could double-schedule workloads onto the
same resources or leave a workload permanently unscheduled because each side thinks
the other already handled it. Choosing to halt rather than risk this kind of
split-brain is the correct tradeoff for a system whose entire job is being the single
source of truth other components trust unconditionally.

This is different from many application-level data stores, where eventual consistency
and continued availability during a partition is the better tradeoff — the right
answer depends on what happens when two components disagree, and for cluster
orchestration state, disagreement is much more costly than a temporary write pause.

## What this predicts about control-plane failure modes

Once you know etcd trades availability for consistency, several observed behaviors
stop being surprising and start being predictable consequences: a partition that
splits a quorum causes the *entire* cluster's write path to stall, not just the
minority side — because the majority side still has to reach consensus among itself,
and any write still has to be replicated before being acknowledged, so even the
majority partition pays a latency cost proportional to how many replicas it still
needs a majority from. A cluster with an even number of control-plane replicas is
actually *worse* at surviving a split than an odd number with the same total
count, because an even split has no majority side at all — this is why etcd deployments
standardize on odd replica counts (3, 5) rather than even ones.

This foundational understanding is also what explains why [etcd as the Hidden
Bottleneck](../patterns/control-plane-at-scale/etcd-as-the-hidden-bottleneck.md) and
[Raft Consensus for Cluster State](../patterns/control-plane-at-scale/raft-consensus-for-cluster-state.md)
treat etcd's write throughput, not the apiserver's own processing capacity, as the
usual ceiling on cluster scale: every write, no matter which component initiated it,
ultimately has to clear this same consensus protocol before it's durable.

## Connections to other foundations

[Failure as the Steady State at Fleet Scale](failure-as-the-steady-state.md) applies a
parallel logic to the workload layer rather than the control plane: both foundations
are really instances of the same broader principle, that distributed systems have to
make an explicit, deliberate choice about what happens under partial failure, and the
wrong choice (silently allowing inconsistency, or refusing all progress under any
partial degradation) is worse than either extreme applied thoughtfully.
