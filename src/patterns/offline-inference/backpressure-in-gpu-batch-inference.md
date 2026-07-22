# Backpressure in GPU Batch Inference

> **One-liner:** A batch pipeline without backpressure between its decode and inference stages either starves the GPU or overruns its memory, depending on which stage runs ahead.

## Symptom

- A heterogeneous CPU/GPU batch pipeline (see
  [Heterogeneous CPU/GPU Batch Pipelines](heterogeneous-cpu-gpu-batch-pipelines.md))
  shows memory usage growing steadily during a run, eventually leading to an
  out-of-memory failure on the decode/preprocessing workers.
- GPU utilization in the same pipeline is inconsistent — periods of good utilization
  followed by periods of idling, correlating with the queue between decode and
  inference stages alternately filling and draining.
- Increasing the number of CPU decode workers, intending to improve throughput,
  instead increases the rate of memory growth and time to eventual OOM failure,
  without a corresponding GPU utilization improvement.
- A pipeline that runs reliably on smaller test corpora fails predictably on larger
  production runs, once the queue between stages has had enough time to accumulate
  a problematic backlog.

## Mechanism

In a pipelined batch inference architecture (decode/preprocess on CPU workers,
inference on GPU workers, connected by a queue), the two stages don't necessarily run
at the same rate — decode throughput and inference throughput are independent
quantities, set by different resource constraints, and there's no inherent reason they
should match exactly. Without an explicit mechanism to reconcile this mismatch, one of
two failure modes results, depending on which direction the mismatch runs.

If decode outpaces inference (CPU workers produce decoded items faster than GPU
workers consume them), the queue between the stages grows without bound, consuming
increasing memory to hold the backlog of decoded-but-not-yet-inferred items —
unbounded intermediate storage between stages of mismatched throughput eventually
exhausts available memory, producing an OOM failure that gives no advance warning
proportional to how severe the mismatch actually is.

If inference outpaces decode (GPU workers are ready for more work faster than CPU
workers can supply it), the GPU sits idle waiting for the queue to have available
items — this is the GPU-starvation symptom central to
[Heterogeneous CPU/GPU Batch Pipelines](heterogeneous-cpu-gpu-batch-pipelines.md),
here specifically attributed to the absence of any mechanism letting the faster
consumer signal the slower producer that it's ready, or letting the producer signal
the consumer that it's fallen behind.

**Backpressure** resolves both failure modes by making the mismatch bounded and
visible rather than unbounded and invisible: a bounded queue between stages, where the
producer (decode) blocks or is throttled once the queue reaches its capacity limit,
rather than continuing to produce unboundedly. This converts an unbounded-memory-
growth failure into a simple, visible, bounded steady state — the queue fills to its
configured limit and stays there, with decode throughput naturally throttled to match
whatever rate inference can actually sustain, and GPU idling, if it occurs, becomes
directly attributable to queue depth (empty queue means decode genuinely can't keep
up) rather than an unexplained utilization gap.

## Real-world sightings

Ray Data's documentation on streaming execution explicitly describes backpressure-
aware pipeline execution as a core design feature specifically for heterogeneous
CPU/GPU batch pipelines, framing it directly as the mechanism that keeps GPU
utilization high without risking unbounded memory growth from an unconstrained
upstream stage.

The Reactive Streams specification, widely adopted across JVM-based streaming and
data pipeline frameworks, formalizes subscriber-driven demand signaling (a consumer
explicitly requesting how much data it can currently accept) as the general
mechanism underlying backpressure — the same underlying principle Ray Data and similar
ML-specific batch frameworks apply to the CPU-decode/GPU-inference pipeline shape
specifically.

## Mitigations

### Bounded queues between pipeline stages

**What it is:** Configure a maximum queue depth between the decode and inference
stages, so the producer stage is throttled (blocked or rate-limited) once the queue
reaches capacity, rather than allowed to produce unboundedly.

**Cost:** A queue that's too small can limit the pipeline's ability to smooth over
short-term rate variance between stages, reducing overall throughput compared to a
more generously-sized (but still bounded) queue.

**How it backfires:** A queue depth chosen without profiling the actual rate
mismatch between stages for a specific workload can be poorly calibrated — too small
for a workload with legitimately high rate variance, or unnecessarily memory-hungry
for one that doesn't need much buffering at all.

### Framework-native streaming execution with built-in backpressure

**What it is:** Use a batch inference framework (Ray Data or similar) that
implements backpressure-aware streaming execution natively, rather than building a
custom pipeline without this consideration from scratch.

**Cost:** Requires adopting the specific framework's execution model and
abstractions, which is a real dependency and learning-curve cost compared to a
simpler, framework-agnostic implementation.

**How it backfires:** Relying on a framework's built-in backpressure doesn't
eliminate the need to understand and tune it — default configuration may not be
well-suited to a specific workload's actual decode/inference rate ratio, and treating
backpressure as fully automatic without any tuning consideration can still produce
suboptimal throughput.

### Monitoring queue depth as the primary diagnostic signal

**What it is:** Track queue depth between pipeline stages as a first-class
operational metric, using it to directly diagnose whether decode or inference is the
current bottleneck, rather than inferring this indirectly from GPU/CPU utilization
alone.

**Cost:** Requires instrumentation exposing intermediate queue depth, which isn't
always a standard metric exposed by every batch processing framework.

**How it backfires:** None specific — the absence of this monitoring just means
diagnosing a throughput problem requires more indirect reasoning (comparing CPU and
GPU utilization separately) rather than a single, direct signal.

## Interactions

- [Heterogeneous CPU/GPU Batch Pipelines](heterogeneous-cpu-gpu-batch-pipelines.md) —
  the pipeline architecture this pattern's backpressure mechanism is specifically
  necessary to make safe and efficient.
- [Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md) —
  the training-time analog, where the same producer/consumer rate-mismatch problem
  appears between data loading and model compute.
- [Content-Addressed Reprocessing](content-addressed-reprocessing.md) — a job that
  crashes from unbounded queue growth loses no correctness (thanks to content-
  addressed idempotency) but does lose the wasted compute already spent on the
  in-flight, un-flushed batch — backpressure prevents the crash from happening in the
  first place.

## References

- Ray Documentation. *Ray Data — Streaming Execution and Backpressure*. Describes
  backpressure-aware execution for heterogeneous batch pipelines.
- Reactive Streams Specification. *reactive-streams.org*. Defines the general
  subscriber-driven demand signaling protocol underlying backpressure implementations.
- NVIDIA DALI Documentation. *Pipeline Execution*. Discusses prefetch and buffering
  configuration relevant to producer/consumer rate matching in GPU data pipelines.
