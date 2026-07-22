# Serving Mode Selection

> **One-liner:** Online, async-queue, and batch serving modes fit different latency and workload shapes, and forcing a long-running video inference request into a synchronous online path is a common, expensive mismatch.

## Symptom

- A synchronous online serving endpoint for a long-running inference workload (video
  processing, large generative outputs) requires holding open connections for minutes,
  producing timeout errors, wasted connection resources, and poor client experience.
- A workload with genuinely low, predictable latency requirements is served through an
  async queue, adding unnecessary polling latency and complexity for a use case that
  didn't need it.
- Provisioning capacity for a synchronous serving endpoint handling highly variable-
  duration requests (some fast, some very slow) requires sizing for the worst case,
  wasting capacity for the common, fast case.
- A team building a new serving path defaults to the same serving mode used
  elsewhere in the organization, without evaluating whether it actually fits the new
  workload's latency and duration characteristics.

## Mechanism

Different inference workloads have fundamentally different latency and duration
profiles, and forcing all of them through the same serving mode produces a mismatch
whose cost shows up differently depending on which direction the mismatch runs.

**Online/synchronous serving** — a client sends a request and waits, connection open,
for the response — fits workloads with genuinely low, bounded latency: a request that
completes in milliseconds to low seconds. This mode's cost model assumes request
duration is short and predictable enough that holding a connection open for the
duration is cheap and reasonable.

**Async/queue-based serving** — a client submits a request, receives an
acknowledgment, and later polls or receives a callback with the result — decouples
request submission from result availability, which fits workloads with longer,
more variable duration: heavy video inference, large batch-style generative outputs,
or anything where the actual processing time can range from seconds to many minutes.
This mode trades immediacy (the client doesn't get an instant answer) for the ability
to handle highly variable-duration work without tying up connection resources or
forcing clients to wait synchronously for something that might take a long time.

**Batch/offline serving** — the same distributed GPU-inference machinery used for
data enrichment (see [Heterogeneous CPU/GPU Batch Pipelines](../offline-inference/heterogeneous-cpu-gpu-batch-pipelines.md))
applied at serving time — fits workloads where there's no individual client waiting
for a specific response at all, just a large volume of work to process with a
throughput, not latency, objective.

Choosing the wrong mode for a given workload's actual duration and latency profile
produces predictable failure: heavy, long-running work forced through a synchronous
online path produces exactly the timeout and resource-waste symptoms described above,
because the serving infrastructure (connection handling, timeout configuration,
capacity provisioning) was built around an assumption — short, bounded request
duration — that this specific workload violates. The inverse mismatch (a genuinely
low-latency workload routed through an async queue) doesn't cause outright failures,
but adds unnecessary latency and complexity for no corresponding benefit.

## Real-world sightings

Video and other heavy-media inference workloads are widely documented across
serving-infrastructure engineering guidance as a canonical case for async/queue-based
serving specifically, distinguishing them explicitly from text or small-image
inference workloads that fit comfortably within synchronous, low-latency serving —
this distinction is a recurring, explicit theme in production ML serving
architecture discussions precisely because the mismatch is common enough to warrant
repeated, explicit guidance against it.

KServe's and similar model-serving platforms' documentation explicitly support both
synchronous and asynchronous inference request patterns as distinct, first-class
options, reflecting industry recognition that a single serving mode doesn't fit every
workload shape a platform needs to support.

## Mitigations

### Matching serving mode to workload duration/latency profile explicitly

**What it is:** Evaluate a new serving workload's actual expected request duration
and latency requirements before defaulting to whatever serving mode is already in use
elsewhere, choosing online, async, or batch deliberately based on that evaluation.

**Cost:** Requires upfront analysis of workload characteristics, which is easy to
skip under time pressure in favor of "just use what we already have."

**How it backfires:** None specific to doing this evaluation correctly — the risk is
in skipping it, which is exactly the failure mode this mitigation exists to prevent.

### Async queue infrastructure as a standard, reusable serving primitive

**What it is:** Build and maintain async/queue-based serving infrastructure as a
standard, available option alongside synchronous serving, so teams with
long-duration workloads have a well-supported path rather than being forced into
synchronous serving by default because it's the only option readily available.

**Cost:** Requires investing in and operating queue infrastructure (submission,
status tracking, result retrieval, callback or polling mechanisms) as a first-class
platform capability.

**How it backfires:** If async infrastructure is built but poorly documented or
poorly supported relative to the synchronous path, teams may still default to
synchronous serving out of familiarity even when it's a worse fit, simply because
the better-fitting option has more friction to actually use.

### Explicit duration-based routing for mixed-duration workloads

**What it is:** For a workload with genuinely mixed request durations (mostly fast,
occasionally slow), route requests to different serving modes based on predicted or
observed duration, rather than forcing all requests through a single mode.

**Cost:** Requires a mechanism to predict or classify request duration before
routing, which isn't always straightforward or accurate.

**How it backfires:** A duration prediction that's wrong (a request predicted fast
turns out slow, or vice versa) routes the request to a poorly-fitting serving mode
anyway, and misrouted requests can be harder to diagnose than a simple, single-mode
system where the mismatch, if any, is at least uniform and predictable.

## Interactions

- [Heterogeneous CPU/GPU Batch Pipelines](../offline-inference/heterogeneous-cpu-gpu-batch-pipelines.md) —
  the batch serving mode shares its underlying execution machinery with offline batch
  inference generally.
- [Continuous & Dynamic Batching](continuous-and-dynamic-batching.md) — within
  whichever serving mode is chosen, batching is a separate, complementary lever for
  GPU utilization.
- [Tiered SLOs for Mixed Traffic](tiered-slos-for-mixed-traffic.md) — a related
  concern about serving heterogeneous workloads without forcing them all through one
  undifferentiated policy, here applied to serving mode rather than latency SLO.

## References

- KServe Documentation. *Inference Protocol — Synchronous and Asynchronous
  Predictions*. Describes support for both serving modes as first-class options.
- NVIDIA Triton Inference Server Documentation. *Model Configuration — Response
  Handling*. Discusses serving mode considerations for varying request duration
  profiles.
- Ray Serve Documentation. *Handling Long-Running Requests*. Discusses async
  serving patterns for workloads with variable or long request duration.
