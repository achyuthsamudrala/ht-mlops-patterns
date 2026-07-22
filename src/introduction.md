# Introduction

This is a field guide for engineers who build and operate ML platforms — the
infrastructure underneath large-scale pretraining, offline batch inference, online
model serving, workflow orchestration, and GPU scheduling.

## Who this is for

Engineers who already run distributed training jobs, serve models in production, or
operate Kubernetes clusters at meaningful scale, and are hitting the problems that
show up only once GPUs number in the thousands and failure becomes a steady-state
condition rather than an exception: checkpointing that costs more than it saves,
schedulers that leave half the fleet idle while jobs queue, control planes that
buckle under watch fan-out, and serving systems that can't decide between latency and
utilization.

This guide assumes familiarity with distributed training concepts (data/model
parallelism, at least one scheduler), containers, and Kubernetes fundamentals. It does
not assume prior experience with the internals of any specific scheduler or serving
framework — the mechanism sections introduce enough of that theory to reason about the
failure mode, and point to the framework-specific behavior (mostly Kubernetes, SLURM,
Ray, and the major serving runtimes) where it matters.

## What this guide is not

This is not a tutorial on any single framework or cloud provider, and it does not cover
model architecture, training algorithms, or research methodology. It covers a specific
set of mechanical failure modes — rooted in how GPU fleets are scheduled, how data
moves at training and inference time, and how models get promoted from research to
production — and their mitigations.

It is also not a comprehensive survey of every technique in the literature. The
patterns included are those that appear repeatedly in production incidents, papers,
and platform-engineering documentation from teams operating at genuine fleet scale.
Selection bias toward patterns that bite engineers in practice is intentional.

## Two reading modes

**Design mode** — read a pattern before you build. Each page describes the trap you're
trying to avoid and the mitigations available, including how each mitigation backfires
under specific conditions.

**Incident mode** — start at the [Symptom Index](symptom-index.md). Find your
observable, follow 2–4 candidate patterns, read the Mechanism section of the one that
fits.

## How patterns are structured

Every page follows the same six-section template:

1. **Symptom** — what your dashboards, scheduler UI, or training logs show, written
   for someone mid-incident.
2. **Mechanism** — why it happens, with the minimum theory needed to reason about it.
3. **Real-world sightings** — documented incidents, traceable to public sources. No
   fabricated examples.
4. **Mitigations** — what to do, what it costs, and **how it backfires** under specific
   conditions.
5. **Interactions** — which other patterns compound with this one and why.
6. **References** — 3–7 items, annotated.

The "how it backfires" entries matter. A mitigation that works as designed but on
wrong assumptions — a checkpoint interval tuned for last quarter's MTBF, a fair-share
quota sized for last quarter's team headcount — causes as many incidents as the
absence of any mitigation at all.

## Where to start

- If something is on fire right now: [Symptom Index](symptom-index.md)
- If you want the underlying concepts before reading patterns:
  [Foundations](foundations/gpu-interconnect-and-collective-communication.md)
- If you want to understand how patterns combine: [Interaction Map](interaction-map.md)
- If you're debugging a stalled distributed training run:
  [Pretraining Infrastructure patterns](patterns/pretraining-infrastructure/index.md)
- If you're debugging a serving system under load:
  [Online Serving patterns](patterns/online-serving/index.md)

## A note on real-world sightings

Each pattern page includes a "Real-world sightings" section. The standard for these
entries is verifiable public sources: peer-reviewed papers, published engineering blog
posts, or official documentation. Incidents described in these sections happened and
were reported publicly.

Where no strong public sighting exists, the section says so in one sentence rather
than fabricating a plausible-sounding incident. The absence of a cited sighting does
not mean the pattern is theoretical — it means no public documentation was found.
