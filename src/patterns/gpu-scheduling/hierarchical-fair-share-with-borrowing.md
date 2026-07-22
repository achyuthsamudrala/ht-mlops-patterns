# Hierarchical Fair-Share with Borrowing

> **One-liner:** Static per-team GPU quotas either strand idle capacity or leave one team perpetually under-served; work-conserving borrowing lets idle share flow to demand without giving up guaranteed minimums.

## Symptom

- A team's unused GPU quota sits idle while another team's jobs queue for capacity,
  even though the idle team would happily have lent it out if there were a mechanism
  to do so.
- A team that borrowed idle capacity from another team's unused quota experiences a
  sudden, disruptive preemption the moment the owning team's own demand returns.
- Static, fixed per-team quotas set at cluster provisioning time become badly
  mismatched to actual usage as team sizes and workloads evolve, with no natural
  mechanism to rebalance them.
- Aggregate cluster utilization is well below 100% even though individual teams
  report being capacity-constrained, because the unused capacity belongs to teams that
  aren't currently using it and can't easily lend it to teams that need more.

## Mechanism

A cluster shared across multiple teams needs some allocation policy, and the two
naive extremes both fail in predictable ways. **Static, isolated quotas** (each team
gets a fixed slice, period) guarantee predictability but waste capacity whenever a
team isn't using its full allocation — that idle capacity simply isn't available to
anyone else, regardless of how much other teams might need it at that moment. **Pure
first-come-first-served, no-quota sharing** maximizes utilization (nothing sits idle
if any team wants it) but provides no guarantee — a team can be starved entirely by
other teams' demand, with no floor on what it can count on.

**Hierarchical fair-share with borrowing** resolves this by giving each team (or
sub-team, in a hierarchy) a guaranteed minimum share, while allowing any currently-
unused share to be borrowed by other teams with excess demand. This is
**work-conserving**: idle capacity doesn't sit unused just because it "belongs" to a
team not currently using it. The critical property that makes this safe rather than
just a return to unbounded first-come-first-served is that borrowing is *reversible*:
when the owning team's own demand returns, borrowed capacity is reclaimed (typically
via preemption — see
[Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md)),
restoring the owner's guaranteed minimum.

This reversibility is exactly what makes the mechanism trustworthy for the lending
team (their guarantee is never actually violated, just temporarily lent out) while
still capturing most of the utilization benefit of full sharing (idle capacity rarely
sits unused for long). The real design tension is in how quickly and gracefully
reclamation happens — instantaneous, ungraceful reclamation imposes the same
lost-progress cost on the borrowing team that ungated preemption does generally (see
[Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md)),
while overly generous reclamation grace periods delay the owning team's access to
their own guaranteed capacity.

Hierarchical structure extends this beyond a flat team-to-team relationship: quotas
and borrowing can nest (an organization's total capacity divided among divisions, each
division's capacity divided among teams, each team's capacity divided among
individuals or projects), letting idle capacity flow to demand at whatever level of
the hierarchy actually has it, rather than only within a single flat pool.

## Real-world sightings

Apache Hadoop YARN's Fair Scheduler and Capacity Scheduler both implement exactly this
hierarchical, work-conserving quota-with-borrowing model, and their documentation
explicitly frames the design around avoiding both the static-quota-waste problem and
the no-guarantee-starvation problem — this is one of the longest-standing, most
mature implementations of this general pattern in distributed systems scheduling.

Kubernetes-native tools built for ML/batch workload scheduling (Kueue's
`ClusterQueue`/`Cohort` hierarchy, Run:ai's quota management) implement analogous
hierarchical, borrowing-capable quota models specifically for GPU cluster
multi-tenancy, reflecting that this general pattern — proven in YARN for CPU-based
Hadoop clusters — transfers directly to GPU scheduling for ML, with the added
complication that GPU capacity is typically far scarcer and more expensive per unit
than the CPU capacity YARN was originally designed to manage.

## Mitigations

### Hierarchical quota configuration matching organizational structure

**What it is:** Configure guaranteed minimum shares and borrowing relationships that
mirror the actual organizational structure and relative priority of teams, rather
than a flat, undifferentiated pool.

**Cost:** Requires ongoing governance to keep the hierarchy and quota values aligned
with actual organizational structure and priority as both evolve.

**How it backfires:** A hierarchy configured once and left unrevisited becomes
increasingly mismatched to actual team sizes and priorities over time, and because the
mismatch degrades gradually rather than breaking obviously, it's easy to defer
revisiting it indefinitely.

### Checkpoint-gated, graceful reclamation of borrowed capacity

**What it is:** When reclaiming borrowed capacity for the owning team's returning
demand, use the same checkpoint-gating and grace-period logic described in
[Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md)
rather than instantaneous, ungraceful eviction.

**Cost:** Delays the owning team's actual access to their reclaimed capacity by
however long the grace period takes.

**How it backfires:** The same tradeoffs described for checkpoint-gated preemption
generally apply here directly — too generous a grace period undermines the owning
team's guarantee, too short doesn't give the borrowing job a fair chance to save
progress.

### Monitoring borrowing patterns as a signal for quota rebalancing

**What it is:** Track how often and how much each team borrows versus lends, using
sustained borrowing patterns as an explicit, data-driven signal that a team's
guaranteed quota may need to be increased (or a chronic lender's decreased).

**Cost:** Requires instrumentation and a governance process to act on the signal,
rather than just observing it passively.

**How it backfires:** Rebalancing based purely on recent borrowing patterns can
overfit to a temporary spike or lull rather than a genuine, durable shift in a team's
actual capacity needs, producing quota churn that itself becomes a source of
instability if acted on too reactively.

## Interactions

- [Preemption & Checkpoint-Gated Interruption](preemption-and-checkpoint-gated-interruption.md) —
  the mechanism that makes borrowing safely reversible; without it, borrowing risks
  becoming a one-way transfer rather than a genuinely temporary loan.
- [Gang Scheduling for Distributed Jobs](gang-scheduling-for-distributed-jobs.md) —
  fair-share allocation has to account for gang-scheduling atomicity, since a job
  can't be "partially" granted its fair share if it needs all-or-nothing placement.
- [Utilization vs. Researcher Velocity](utilization-vs-researcher-velocity.md) — the
  broader tension this pattern's specific mechanism is one concrete way of navigating.

## References

- Apache Hadoop Documentation. *Fair Scheduler* and *Capacity Scheduler*. Describes
  hierarchical, work-conserving quota allocation with borrowing for shared clusters.
- Kubernetes SIG Scheduling. *Kueue Documentation — Cohorts*. Describes hierarchical
  quota borrowing specifically for Kubernetes-native batch/ML scheduling.
- Ghodsi, A. et al. *Dominant Resource Fairness: Fair Allocation of Multiple Resource
  Types*. NSDI 2011. Foundational treatment of fair-share allocation across multiple,
  heterogeneous resource dimensions relevant to GPU-plus-other-resource scheduling.
