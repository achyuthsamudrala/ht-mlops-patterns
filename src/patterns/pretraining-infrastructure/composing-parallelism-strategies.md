# Composing Parallelism Strategies

> **One-liner:** Data, tensor, pipeline, and sharded (FSDP/ZeRO) parallelism each trade memory for communication differently, and fitting a large model means composing them deliberately, not picking one.

## Symptom

- A model that fits comfortably during single-GPU debugging runs out of memory the
  moment it's scaled to its intended training configuration, despite having "enough"
  aggregate GPU memory across the cluster on paper.
- Switching from pure data parallelism to a sharded approach (FSDP/ZeRO) reduces
  per-GPU memory usage substantially but increases communication volume and, in some
  configurations, step time.
- A training configuration that worked well at one cluster size or model size performs
  poorly when scaled up, without any single obviously "wrong" setting — the
  parallelism strategy that was appropriate at the old scale no longer is.
- Combining multiple parallelism strategies (e.g., tensor parallelism within a node,
  data parallelism across nodes) produces a working but poorly-performing
  configuration, with no clear indication of which dimension is misconfigured.

## Mechanism

No single parallelism strategy is free, and each makes a different tradeoff between
memory usage and communication volume — understanding this tradeoff space, not
memorizing a "best" strategy, is what makes composing them correctly possible.

**Data parallelism** replicates the full model on every GPU and splits the training
batch across GPUs, each computing gradients on its own shard of data and
synchronizing via all-reduce. This is simple and communication-efficient per
parameter, but requires every GPU to hold a full copy of the model, its gradients, and
(for adaptive optimizers) its optimizer state — for a large enough model, this simply
doesn't fit in a single GPU's memory, regardless of how much aggregate cluster memory
exists.

**Sharded data parallelism (FSDP / DeepSpeed ZeRO)** addresses this directly: rather
than replicating the full model, optimizer state, and gradients on every GPU, these
are sharded across the data-parallel group, and each GPU only materializes the full
parameters it needs, briefly, via additional communication (all-gather) at the point
they're needed in the forward/backward pass. ZeRO's stages (1, 2, 3) progressively
shard more state (optimizer state, then gradients, then parameters themselves),
trading progressively more communication for progressively less per-GPU memory
pressure.

**Tensor parallelism** splits individual layers' computation (e.g., splitting a large
matrix multiplication) across multiple GPUs, letting a single layer larger than one
GPU's memory be computed collectively. This requires very frequent, low-latency
communication between the GPUs sharing a layer, which is why tensor parallelism is
typically confined to GPUs within a single node connected via NVLink — the
communication frequency makes it impractical across the slower cross-node
interconnect (see
[Interconnect-Bound Distributed Training](interconnect-bound-distributed-training.md)).

**Pipeline parallelism** splits a model's layers across GPUs sequentially (different
GPUs own different layers), with activations passed between them as data flows
through the model. This requires less frequent communication than tensor parallelism
(only at layer boundaries, not within every operation), making it more tolerant of
slower interconnect, but introduces "pipeline bubbles" — idle time while later stages
wait for earlier stages to produce their first outputs — that reduce achievable
utilization unless carefully scheduled (micro-batching to keep the pipeline full).

**Composing these** — commonly tensor parallelism within a node (fast NVLink),
pipeline parallelism across a modest number of nodes, and data parallelism (often
sharded) across the remaining scale — is how models too large for any single strategy
alone are trained in practice. The right composition depends on model size, per-layer
size, cluster topology, and interconnect quality, which is exactly why a configuration
that worked at one scale can fail or underperform at another: the tradeoff surface
itself shifts as any of these variables change.

## Real-world sightings

The ZeRO (Zero Redundancy Optimizer) paper (Rajbhandari et al., "ZeRO: Memory
Optimizations Toward Training Trillion Parameter Models," SC 2020) explicitly
formalizes the progressive memory/communication tradeoff across its three stages, and
is the direct basis for DeepSpeed's and PyTorch FSDP's sharded data parallelism
implementations.

Megatron-LM's design papers (Shoeybi et al., "Megatron-LM: Training Multi-Billion
Parameter Language Models Using Model Parallelism," and the follow-up work on
combining tensor, pipeline, and data parallelism) explicitly describe the
node-boundary-aware composition strategy — tensor parallelism within a node, pipeline
and data parallelism across nodes — as the practical approach for training models at a
scale no single strategy could handle alone, directly motivated by interconnect
locality constraints.

## Mitigations

### Matching parallelism dimension to interconnect locality

**What it is:** Place the most communication-frequent parallelism dimension (tensor
parallelism) within the fastest interconnect boundary (a single node's NVLink domain),
and less communication-frequent dimensions (pipeline, data) across slower
cross-node links.

**Cost:** Constrains tensor-parallel degree to at most the number of GPUs in a single
node (or NVLink domain), which caps how much memory relief that dimension alone can
provide.

**How it backfires:** A cluster with unusually fast cross-node interconnect (a
well-provisioned InfiniBand fabric) might tolerate more cross-node tensor parallelism
than this rule of thumb assumes, and rigidly following the rule can leave performance
on the table for such a cluster.

### Progressive ZeRO/FSDP sharding to fit within memory

**What it is:** Choose the least aggressive sharding stage (ZeRO-1, -2, or -3, or
FSDP's equivalent) that actually fits the model in available memory, rather than
defaulting to the most aggressive stage regardless of need.

**Cost:** More aggressive sharding stages increase communication volume, so
over-sharding a model that would have fit with less aggressive sharding trades away
throughput unnecessarily.

**How it backfires:** A sharding stage chosen to fit a model at one sequence length or
batch size can become insufficient if either grows later, requiring a re-tuning pass
that's easy to defer under deadline pressure.

### Profiling to attribute step time correctly before changing strategy

**What it is:** Profile a training step to determine whether time is dominated by
compute, tensor-parallel communication, pipeline bubbles, or data-parallel all-reduce,
before changing the parallelism configuration.

**Cost:** Requires distributed training profiling tooling and the expertise to
interpret it correctly across multiple overlapping parallelism dimensions.

**How it backfires:** None specific — the absence of this diagnostic step is what
leads to the "poorly-performing but working" configurations described in the symptom
list, where a team tunes the wrong dimension because they didn't first determine which
one was actually the bottleneck.

## Interactions

- [Interconnect-Bound Distributed Training](interconnect-bound-distributed-training.md) —
  the constraint that determines which parallelism dimensions are viable across which
  physical boundaries.
- [Elastic Training vs. Hot Spares](elastic-training-vs-hot-spares.md) — tensor- and
  pipeline-parallel configurations are far more rigid to reshape after a node loss
  than pure data-parallel ones, directly affecting recovery strategy choice.
- [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md) —
  sharded parallelism strategies (FSDP/ZeRO) require sharded, distributed checkpoint
  formats rather than a single consolidated checkpoint file.

## References

- Rajbhandari, S. et al. *ZeRO: Memory Optimizations Toward Training Trillion
  Parameter Models*. SC 2020. Formalizes the progressive sharding stages underlying
  FSDP and DeepSpeed ZeRO.
- Shoeybi, M. et al. *Megatron-LM: Training Multi-Billion Parameter Language Models
  Using Model Parallelism*. Describes tensor and pipeline parallelism composition.
- Narayanan, D. et al. *Efficient Large-Scale Language Model Training on GPU Clusters
  Using Megatron-LM*. SC 2021. Extends the composition to 3D parallelism (data,
  tensor, and pipeline together) at large cluster scale.
