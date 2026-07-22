# Quantization & Compiled Runtimes

> **One-liner:** Lower-precision weights and compiled execution graphs trade a small, usually acceptable accuracy cost for large latency, throughput, and cost wins.

## Symptom

- A serving endpoint running an unquantized, uncompiled model shows latency and cost
  per request substantially higher than equivalent deployments elsewhere reportedly
  achieve for similar models.
- Quantizing a model to a lower precision produces a meaningful throughput
  improvement but also a measurable accuracy regression on evaluation, requiring an
  explicit decision about whether the tradeoff is acceptable for the specific use
  case.
- A compiled runtime (TensorRT, ONNX Runtime, or similar) produces excellent
  performance for the specific model version and hardware it was compiled against,
  but requires re-compilation (and re-validation) whenever the model is updated.
- Two teams serving similar models see very different cost-per-request, traced back
  to one using an optimized (quantized, compiled) serving path and the other using a
  naive, unoptimized one.

## Mechanism

A model served in its original training precision (commonly FP32 or BF16) and
executed via a general-purpose, uncompiled runtime is usually leaving substantial
performance on the table relative to what the same model, optimized for inference
specifically, can achieve — training and inference have different priorities
(training needs precision and flexibility for gradient computation; inference needs
speed and efficiency for a fixed, already-trained computation graph), and using
training-oriented defaults for inference forfeits gains available specifically because
inference doesn't need training's flexibility.

**Quantization** reduces numerical precision (FP32 to FP16/BF16, or further to INT8
or FP8) for weights and/or activations, directly reducing memory bandwidth
requirements (less data to move) and often enabling faster compute paths on hardware
with dedicated lower-precision compute units. This is not free: reduced precision can
degrade model accuracy, and the magnitude of that degradation varies by model
architecture, task, and how aggressively precision is reduced — a small, usually
acceptable degradation for many tasks, but one that has to be explicitly measured and
evaluated against the specific use case's accuracy requirements, not assumed to be
negligible by default.

**Compiled runtimes** (TensorRT, ONNX Runtime, torch.compile, XLA) analyze a model's
computation graph ahead of time and generate optimized execution code specifically
for the target hardware — fusing multiple operations into single, more efficient
kernels, eliminating redundant computation, and choosing hardware-specific optimal
implementations for each operation. This produces genuine performance gains beyond
what the same model run through a general-purpose, interpretive execution path
achieves, but the compilation is specific to the exact model graph, precision, and
target hardware it was compiled for — updating the model, changing precision, or
deploying to different hardware generally requires re-compiling (and re-validating
performance and correctness for) the new configuration, which is a real operational
cost distinct from simply swapping in a new model checkpoint the way an uncompiled
runtime would allow.

These two techniques compound: a quantized model run through a compiled runtime
specifically optimized for that quantization level typically achieves substantially
better performance than either technique applied alone, since the compiler can
generate code specifically exploiting the lower-precision compute paths rather than
treating quantization as an afterthought layered on top of a compilation targeting
full precision.

## Real-world sightings

NVIDIA's TensorRT documentation explicitly describes graph optimization (layer
fusion, precision calibration for quantization, kernel auto-tuning for specific
target GPUs) as its core value proposition over running the same model through a
general-purpose framework runtime, with published benchmarks consistently showing
substantial latency and throughput improvements for models properly optimized through
this pipeline versus unoptimized execution.

vLLM's and other modern LLM serving frameworks' documentation on quantization support
(FP8, INT8, and other reduced-precision serving modes) explicitly discusses the
accuracy-versus-performance tradeoff and generally recommends task-specific accuracy
validation before adopting an aggressive quantization level in production, rather than
assuming a given quantization level's accuracy impact transfers uniformly across
different models and tasks.

## Mitigations

### Task-specific accuracy validation before adopting quantization

**What it is:** Measure accuracy impact on the specific task and evaluation set a
model will actually be used for, before adopting a given quantization level in
production, rather than assuming published accuracy-degradation figures (often
measured on different tasks or benchmarks) transfer directly.

**Cost:** Requires a representative evaluation set and the discipline to actually run
this validation before deploying a quantization change, rather than deploying and
observing production behavior after the fact.

**How it backfires:** An evaluation set that isn't representative of actual production
input distribution can pass validation while still missing a real accuracy
regression that only manifests on inputs the evaluation set doesn't adequately cover.

### Building compiled-runtime re-validation into the model update pipeline

**What it is:** Treat re-compilation and re-validation as a required step of any
model update pipeline for models served through a compiled runtime, rather than an
optional or easily-forgotten extra step.

**Cost:** Adds pipeline latency and complexity to every model update, compared to a
simpler pipeline that could swap in a new checkpoint without a compilation step.

**How it backfires:** A model update pipeline that treats compilation as optional or
separate from the main update path risks deploying an uncompiled (and thus much
slower) fallback if the compilation step is skipped or fails silently, without an
explicit signal that performance has regressed as a result.

### Establishing quantization/compilation as the default serving path, not an opt-in optimization

**What it is:** Make quantized, compiled serving the standard, default deployment
path for new models, rather than treating it as an advanced optimization applied only
after a naive deployment is already in production and its inefficiency is noticed.

**Cost:** Requires the platform team to build and maintain tooling that makes this
default path easy to adopt, rather than leaving each team to discover and implement
optimization independently.

**How it backfires:** A default optimized path that's harder to use or debug than a
naive one can push teams toward the naive path anyway under time pressure, unless the
optimized default is genuinely as easy to adopt as the naive alternative.

## Interactions

- [Continuous & Dynamic Batching](continuous-and-dynamic-batching.md) — a
  complementary, compounding lever for serving efficiency operating at the
  request-batching level rather than the per-operation compute level.
- [Fair Model Comparison Under Drift](../model-lifecycle/fair-model-comparison-under-drift.md) —
  quantization's accuracy impact has to be evaluated using the same rigor (pinned
  eval set, consistent methodology) this pattern describes for any model comparison.
- [Serving Mode Selection](serving-mode-selection.md) — quantization and compilation
  benefits apply across serving modes, but their relative importance differs (latency-
  critical online serving benefits most directly from reduced per-request compute
  time).

## References

- NVIDIA TensorRT Documentation. *TensorRT Developer Guide*. Describes graph
  optimization, precision calibration, and kernel auto-tuning for inference
  acceleration.
- Kwon, W. et al. *Efficient Memory Management for Large Language Model Serving with
  PagedAttention*. SOSP 2023. Discusses quantization support alongside continuous
  batching in the vLLM serving framework.
- Jacob, B. et al. *Quantization and Training of Neural Networks for Efficient
  Integer-Arithmetic-Only Inference*. CVPR 2018. Foundational treatment of
  quantization's accuracy/performance tradeoff.
