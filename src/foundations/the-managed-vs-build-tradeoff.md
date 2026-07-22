# The Managed vs. Build Tradeoff

> **A managed ML platform sells you speed and support; a self-built platform on raw
> primitives sells you control and portability — and neither is free, they just charge
> different currencies.** Almost every tool-choice question in this guide is a specific
> instance of this one underlying axis, and defending a choice well means naming which
> currency you're spending, not just which tool you picked.

## What "managed" actually buys

Fully-managed ML platforms (SageMaker, Vertex AI, Azure Machine Learning, and their
equivalents for training, registries, and serving) bundle infrastructure operation,
scaling, and integration into a single product: you submit a training job or deploy an
endpoint, and the provisioning, scheduling, and most of the operational burden is
handled for you. This genuinely removes work — no scheduler to operate, no cluster
autoscaling logic to write, no serving runtime to patch and upgrade.

What it costs is control and portability. Managed platforms constrain you to their
supported workflows, their scaling knobs, their pricing model, and their specific
abstractions for jobs, models, and endpoints. Migrating away later means rewriting
against a different set of abstractions, not just changing a configuration file. And
the price is typically a real premium over the equivalent raw compute cost, because
you're paying for the operational layer on top of it.

## What "build" actually buys

Building on raw primitives (Kubernetes or SLURM directly, open-source schedulers,
training frameworks, and serving runtimes) costs real, ongoing engineering effort: you
need a platform team to operate the scheduler, tune the control plane, patch the
serving stack, and own the on-call burden for all of it. Nothing is handled for you by
default.

What this buys is control over exactly the dimensions that matter most at scale and
under customization: data loading strategy, batching behavior, scheduling policy,
placement logic, and the ability to move workloads across clouds or between on-prem
and cloud capacity without a rewrite. For a workload with genuinely novel requirements
— training on a modality or scale a managed platform's abstractions weren't designed
for — build is often not just cheaper at scale but the *only* option that actually
supports what's needed.

## Why the choice correlates so strongly with organization type

Organizations building genuinely novel, large-scale, or highly customized ML
workloads — frontier research labs, applied ML teams working with unusual modalities
or scales — tend to build on raw primitives, because the constraints managed
platforms impose bind exactly where their workloads are least standard: custom
training loops, non-standard data loading, bespoke batching and scheduling logic.
Teams running standard, well-supported workflows without a dedicated platform team
tend to choose managed, because the standard workflow is exactly what the managed
platform optimizes for, and the premium is worth paying to avoid building an
operations team from scratch.

This is not a claim that one is universally better — it's a claim that the tradeoff's
resolution depends on three concrete variables: **scale** (does the managed premium,
multiplied by usage, exceed what a platform team would cost to build and run the
equivalent), **customization** (does the workload fit the managed platform's supported
abstractions, or does it need something the platform wasn't built for), and **team
size and expertise** (is there a platform team capable of operating raw infrastructure
reliably, or would that capability itself need to be built from nothing).

## How this shows up throughout the rest of the guide

Nearly every family in this guide has at least one pattern where a managed option and
a build-your-own option both exist, and the right answer depends on exactly these
three variables rather than one option being objectively superior:
[SLURM vs. Kubernetes for Training](../patterns/pretraining-infrastructure/slurm-vs-kubernetes-for-training.md)
is fundamentally a build-vs-build choice within the "build" branch of this tradeoff,
while managed training services sit as a third option outside both. Serving
frameworks, orchestrators, and experiment trackers all present the same shape of
decision.

## Connections to other foundations

[Failure as the Steady State at Fleet Scale](failure-as-the-steady-state.md) shifts
this tradeoff at scale: the more failure-handling logic a workload needs (checkpoint
tuning, straggler detection, elastic recovery), the more likely a managed platform's
generic failure handling falls short of what a specific, large-scale training workload
actually requires — which is part of why frontier-scale training infrastructure is
disproportionately self-built even at organizations that use managed platforms
elsewhere.
