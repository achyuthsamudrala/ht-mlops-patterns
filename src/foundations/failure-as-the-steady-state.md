# Failure as the Steady State at Fleet Scale

> **At a large enough fleet, failure isn't an exception path to handle — it's the
> normal operating condition the entire system has to be designed around.** A platform
> that treats a GPU or node failure as a rare event to patch around, rather than a
> constant background rate to design for, will be rebuilt from painful experience
> eventually; better to start from the right assumption.

## The arithmetic that makes this concrete

Individual component mean-time-between-failures (MTBF) numbers look reassuring in
isolation — a single GPU with an MTBF of tens of thousands of hours sounds like a
rare-failure component. But MTBF for a *system* of N independent components scales
down roughly as MTBF_component / N: a fleet of thousands of GPUs, each individually
reliable, collectively experiences a component failure far more often than any single
GPU's own failure rate would suggest.

Concretely: if a single GPU's MTBF is on the order of 50,000 hours, a job spanning
4,000 GPUs should expect a component failure roughly every 50,000/4,000 ≈ 12.5 hours
of aggregate run time — not because any individual GPU became less reliable, but
because the job now has 4,000 independent chances for something to fail, and the
failures compound across the whole allocated fleet, not just the compute nodes
themselves (networking, storage, and power infrastructure all contribute their own
failure modes on top of GPU failure specifically).

## Why this changes the design problem

If failure is rare, the natural design response is to treat it as an exception:
detect it, alert a human, and let recovery be a mostly-manual process. If failure is
routine — happening multiple times per day across a large fleet, for a job that might
run for weeks — that response doesn't scale, because a human-in-the-loop recovery
process applied at that frequency either burns out the on-call rotation or, more
likely, becomes so routinized that it stops actually treating the failure as urgent to
minimize.

The correct framing this forces: **the system's job isn't to prevent failure, it's to
make each individual failure cost as little as possible** — minutes of lost progress
and automated recovery time, not hours, and definitely not a human paged awake to
manually intervene. This reframing is what motivates
[Distributed Checkpointing at Scale](../patterns/pretraining-infrastructure/distributed-checkpointing-at-scale.md)'s
approach to checkpoint frequency as an explicit cost-optimization problem rather than
an afterthought, and
[Elastic Training vs. Hot Spares](../patterns/pretraining-infrastructure/elastic-training-vs-hot-spares.md)'s
treatment of fast, automated recovery as the central design goal.

## The quiet corollary: not all failures announce themselves

The arithmetic above covers failures that are at least detectable — a node goes
unreachable, a process crashes. A harder category is silent failure: a GPU that
continues running but produces subtly wrong results (silent data corruption), or a
node that's merely slow rather than dead (a straggler). Neither triggers an obvious
crash-and-restart signal, and at fleet scale, the probability of at least one silent
failure occurring during a long run is non-trivial for exactly the same reason
component-failure probability compounds across a large fleet. Designing only for
clean crash-and-restart failure handles the easier half of the problem; the harder
half requires active detection (see
[Silent Data Corruption & Stragglers](../patterns/pretraining-infrastructure/silent-data-corruption-and-stragglers.md)).

## Why this belongs in foundations rather than a single pattern page

This isn't a single failure mode with a single mitigation — it's the underlying
assumption that changes what a *correct* design looks like across checkpointing
frequency, scheduling elasticity, straggler detection, and even the choice between
hot spares and reshaping a distributed job after a loss. Every one of those patterns is
answering a version of the same question: given that failure will happen at a known,
predictable rate, what design minimizes the cost of each occurrence?

## Connections to other foundations

[GPU Interconnect & Collective Communication](gpu-interconnect-and-collective-communication.md)
compounds directly: a degraded (not fully failed) network link can produce a slow
straggler rather than a clean failure, which is harder to detect and reschedule around
than an outright crash. [Consensus & the CAP Tradeoff for Cluster State](consensus-and-the-cap-tradeoff.md)
describes a related but distinct failure domain — the control plane's own resilience
to node loss, as opposed to the training workload's.
