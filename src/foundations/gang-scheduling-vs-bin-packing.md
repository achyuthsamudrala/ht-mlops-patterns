# Gang Scheduling vs. Bin-Packing

> **A scheduler that maximizes utilization and a scheduler that guarantees a
> distributed job gets all the resources it needs at once are solving different
> problems, and a scheduler built only for one handles the other badly.** This single
> tension explains most of the friction between "make the cluster efficient" and
> "make distributed training jobs actually runnable."

## What each approach optimizes for

**Bin-packing** schedulers (the default behavior of a vanilla Kubernetes scheduler)
place each pod independently as capacity becomes available, trying to pack workloads
efficiently onto available nodes to maximize utilization. This works well for
independent, loosely-coupled workloads — a web service's replicas don't need to start
simultaneously, and each one can be placed whenever room opens up.

**Gang scheduling** requires that a distributed job's entire set of workers be placed
simultaneously, or none of them at all. This exists because a tightly-coupled
distributed training job — one using data, tensor, or pipeline parallelism across
many GPUs — doesn't function with a partial allocation: if a job needs 256 GPUs and
only 200 are currently placed, those 200 aren't doing useful work; they're either
idle, waiting for the rest, or in the worst case, several large jobs each partially
scheduled can deadlock, each holding some resources while waiting for resources held
by another equally-partial job.

## Why a bin-packing scheduler mishandles gang-scheduling needs

A scheduler with no gang-scheduling awareness treats each pod in a distributed job as
an independent placement decision, with no knowledge that they're actually one atomic
unit. Under contention, this can produce exactly the partial-allocation problem
described above: some of a job's pods get scheduled, others don't, and the scheduled
ones sit consuming resources while contributing no progress, since the job can't
actually run until every worker is placed. Worse, without careful design, two large
jobs contending for the same capacity can each get partially scheduled and then
neither can make progress nor be scheduled to completion — a distributed-systems
analog of a resource deadlock.

## Why a naive gang-scheduling policy hurts utilization

The opposite failure mode is just as real: a scheduler that always waits for a job's
full resource requirement to be available before placing any of it can leave capacity
idle that a smaller, immediately-schedulable job could have used in the meantime. If a
1,000-GPU job is queued waiting for capacity that won't be available for hours, and a
1-GPU debug job arrives in the interim, a purely rigid gang-scheduling policy with no
backfill mechanism leaves that capacity idle rather than letting the small job run
and vacate before the large job's capacity is ready.

**Backfill** scheduling is the standard resolution: reserve capacity for the queued
gang-scheduled job, but allow smaller jobs that can complete before that capacity is
needed to run in the gap, as long as they won't delay the reserved job's start. This
recovers much of bin-packing's utilization benefit without sacrificing the
all-or-nothing guarantee gang-scheduled jobs require.

## Why this is a foundational tension, not a solved problem

There is no configuration of a scheduler that simultaneously maximizes utilization,
guarantees no gang-scheduled job ever waits, and never leaves capacity idle — these
goals genuinely conflict under contention, and any real scheduling policy is choosing
a specific point on that tradeoff, whether or not that choice is made explicitly. This
is precisely the reasoning
[Gang Scheduling for Distributed Jobs](../patterns/gpu-scheduling/gang-scheduling-for-distributed-jobs.md)
and [Utilization vs. Researcher Velocity](../patterns/gpu-scheduling/utilization-vs-researcher-velocity.md)
build on: naming which goal a scheduling policy is actually prioritizing is more
useful than treating "the scheduler isn't working well" as a bug to be patched rather
than a tradeoff to be tuned.

## Connections to other foundations

[GPU Interconnect & Collective Communication](gpu-interconnect-and-collective-communication.md)
adds a further wrinkle: even a successful gang-scheduled placement can perform badly
if it ignores network topology, which is exactly why gang scheduling and
topology-aware placement are usually discussed together rather than as fully
independent concerns.
