# Heterogeneous CPU/GPU Batch Pipelines

> **One-liner:** Batch inference over media is a CPU-bound decode stage feeding a GPU-bound inference stage, and treating it as a single homogeneous stage starves the GPU.

## Symptom

- A batch inference job's GPU utilization sits well below what the model's own
  compute time should permit, while CPU utilization on the same workers is
  saturated.
- Adding more GPU workers to a batch inference job doesn't proportionally improve
  throughput, because the CPU-bound decode/preprocessing stage feeding those GPUs
  hasn't scaled correspondingly.
- A batch inference framework that schedules decode and inference as a single,
  undifferentiated unit of work per item shows worse throughput than one that treats
  them as separately-scaled, pipelined stages.
- Profiling a batch inference job shows the model's forward-pass time is small
  relative to total per-item wall-clock time, with the remainder attributable to
  decode and preprocessing.

## Mechanism

Batch inference over media (running a model — captioning, embedding, detection,
classification — over a large corpus of images or videos) has the same fundamental
shape as the training-time data-loading problem described in
[Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md)
and [GPU-Accelerated Video Decode](../training-data-platforms/gpu-accelerated-video-decode.md):
a CPU-bound decode stage has to feed a GPU-bound inference stage, and if these two
stages aren't pipelined and independently scaled, the GPU — the expensive, scarce
resource — sits idle waiting on the comparatively cheap CPU stage.

The distinguishing characteristic for batch inference specifically (versus training)
is that the workload is embarrassingly parallel across items — there's no
cross-item dependency the way there is across training steps — which makes it
naturally well-suited to a producer-consumer pipeline architecture: a pool of CPU
workers decode and preprocess items, feeding a queue; a pool of GPU workers consume
from that queue, batch items together, and run inference. Sizing these two pools
independently (more CPU workers if decode is the bottleneck, more GPU workers or
larger inference batch sizes if GPU throughput is the constraint) is what lets the
pipeline actually saturate the GPU, rather than treating "process one item" as a
single, monolithic unit of work that implicitly ties decode and inference scaling
together.

Frameworks built specifically for this pattern (Ray Data being the most prominent
example for ML batch inference) support heterogeneous resource requirements per
pipeline stage natively — a CPU-only stage and a GPU stage in the same pipeline can be
independently scaled and scheduled, with the framework handling the queueing and
backpressure between them (see
[Backpressure in GPU Batch Inference](backpressure-in-gpu-batch-inference.md)).
General-purpose distributed compute frameworks not designed with this heterogeneity in
mind (traditional Spark, for instance, designed primarily around CPU-based SQL/ETL)
can express the pattern but tend to handle GPU-stage scaling and CPU/GPU pipelining
less naturally, often requiring more manual work to avoid exactly the GPU-starvation
symptom described above.

## Real-world sightings

Ray Data's documentation explicitly frames its design around exactly this
heterogeneous pipeline pattern — CPU-bound decode/preprocessing feeding GPU-bound
inference, with independently configurable resource requirements and concurrency per
pipeline stage — citing large-scale batch inference over media as a primary,
motivating use case distinct from Spark's traditional tabular ETL strengths.

NVIDIA DALI's documentation, while primarily framed around training-time data
loading, explicitly notes its applicability to batch inference preprocessing as well,
for the same underlying reason: GPU-accelerated decode benefits any pipeline where
decode cost is significant relative to model compute time, whether that pipeline is
training or offline batch inference.

## Mitigations

### Pipelining with independently-scaled CPU and GPU stages

**What it is:** Structure the batch inference job as a pipeline with separately
sized and scaled CPU (decode/preprocess) and GPU (inference) stages, connected via a
queue, rather than treating each item's full processing as one monolithic unit.

**Cost:** Requires a framework or custom implementation supporting this
heterogeneous pipeline pattern, adding architectural complexity compared to a
simpler, single-stage-per-item design.

**How it backfires:** Sizing the two stages requires understanding their relative
throughput, which can shift if either the model or the input data characteristics
change (a larger, slower model shifts the balance toward CPU stage being
over-provisioned; higher-resolution input media shifts it the other way) — a sizing
that was correct once needs periodic re-validation.

### GPU-accelerated decode for the preprocessing stage

**What it is:** Use NVDEC-based decode (via DALI or similar) for the batch
inference pipeline's preprocessing stage, not just for training, reducing or
eliminating the CPU-bound decode bottleneck directly.

**Cost:** Shares NVDEC hardware decoder capacity with the GPU's other work, and
requires the same integration work described in
[GPU-Accelerated Video Decode](../training-data-platforms/gpu-accelerated-video-decode.md).

**How it backfires:** If the inference stage itself is also GPU-bound and running on
the same physical GPUs, decode and inference now compete for GPU resources (even if
NVDEC and CUDA cores are physically separate, they share the same GPU's overall
power and thermal budget), which can require careful profiling to confirm the net
effect is actually positive for a given workload.

### Batching inference requests within the GPU stage

**What it is:** Accumulate multiple decoded items into a batch before running
inference, rather than running inference on items one at a time, to better utilize
GPU compute (the same batching principle described in
[Continuous & Dynamic Batching](../online-serving/continuous-and-dynamic-batching.md)
for online serving, applied here to offline batch processing).

**Cost:** Batching introduces a buffering delay (waiting to accumulate a batch)
which matters less for offline batch processing than for online serving latency, but
still affects end-to-end pipeline latency for the corpus overall.

**How it backfires:** A batch size chosen without regard to per-item size variance
(some items decode to much larger tensors than others — variable-length video clips,
for instance) can produce inconsistent memory usage per batch, risking
out-of-memory errors for batches that happen to draw several large items together.

## Interactions

- [Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md) —
  the training-time analog of this exact CPU/GPU pipelining problem.
- [GPU-Accelerated Video Decode](../training-data-platforms/gpu-accelerated-video-decode.md) —
  the specific mitigation technique that applies equally to batch inference
  preprocessing as it does to training data loading.
- [Backpressure in GPU Batch Inference](backpressure-in-gpu-batch-inference.md) — the
  mechanism that makes a heterogeneous pipeline's CPU and GPU stages coexist safely
  without one overrunning the other.

## References

- Ray Documentation. *Ray Data — Working with GPUs*. Describes heterogeneous
  CPU/GPU pipeline support for batch inference workloads.
- NVIDIA DALI Documentation. *Inference Pipelines*. Describes GPU-accelerated decode
  applicability to batch inference, not just training.
- Sethi, R. et al. (Facebook). *Presto: SQL on Everything*. ICDE 2019. Contrasting
  reference point: a system optimized for CPU-based tabular processing, illustrating
  the mismatch this pattern's mitigations address for GPU-heavy media pipelines.
