# Two-Level Shuffle for Streaming Datasets

> **One-liner:** True global shuffle requires random access that collapses object-storage throughput; shard-order plus buffer shuffling approximates it without paying that cost.

## Symptom

- A training pipeline attempting a true global shuffle across a sharded dataset sees
  I/O throughput collapse compared to a sequential read of the same shards.
- Training loss curves show a subtle periodicity correlated with shard boundaries,
  suggesting samples aren't as well-mixed across the epoch as intended.
- Increasing the in-memory shuffle buffer size improves apparent randomness but also
  increases memory usage and startup latency (time to fill the buffer before training
  can begin).
- Samples that were written to the same shard at dataset-creation time (e.g., all
  frames from one long video, or all records from one ingestion batch) show
  correlated behavior in a downstream model, suggesting incomplete shuffling.

## Mechanism

Stochastic gradient descent's convergence properties assume, in the idealized case,
that each mini-batch is a well-mixed, representative sample of the full dataset — not
a run of correlated, adjacent-in-storage samples. This creates a direct conflict with
[the shard pattern](the-shard-pattern-for-training-data.md): shards are, by design,
read sequentially for I/O efficiency, but sequential reads naturally produce
batches dominated by whichever shard is currently being read, which is the opposite of
a well-mixed sample if samples within a shard are at all correlated (which they often
are, since shards are frequently populated by writing samples in whatever order the
ingestion pipeline produced them).

A true global shuffle — randomly selecting the next sample from anywhere in the entire
dataset — would solve this completely, but requires random access to arbitrary
individual samples across arbitrary shards, which is exactly the access pattern
sharding was designed to avoid. Attempting a true global shuffle against
shard-organized data on object storage reintroduces the small-random-read problem
sharding exists to prevent.

**Two-level shuffle** resolves this tension with an approximation that's cheap enough
to actually implement at scale: first, shuffle the *order in which shards themselves*
are read each epoch (a coarse-grained shuffle, cheap because it only reorders which
large sequential read happens when, not the access pattern within a read). Second,
maintain a large in-memory shuffle buffer that accumulates samples from several
shards' worth of in-flight reads simultaneously, and draws training batches randomly
from that buffer rather than in strict read order — mixing samples across shards
within the buffer's window even though the underlying reads remain sequential.

This produces samples that are well-mixed *within* the buffer's window, but not
truly globally shuffled — two samples originally adjacent within the same shard have
some nonzero (if the buffer is reasonably large, small) chance of still landing in
the same training batch, and samples very far apart in shard order have essentially
zero chance of mixing within any single buffer window. Randomizing sample-to-shard
assignment at *dataset-creation time* (rather than only at read time) substantially
reduces the practical impact of this residual correlation, since it prevents any
shard from being dominated by samples that share some correlated property in the
first place.

## Real-world sightings

MosaicML's Streaming Dataset library documentation explicitly describes this exact
two-level approach — shuffling shard download order plus an in-memory shuffle buffer
— as its core shuffling strategy, and documents the buffer-size tradeoff between
shuffle quality (larger buffer, better mixing) and memory/startup cost directly as a
configurable, empirically-tuned parameter.

WebDataset's documentation similarly recommends randomized shard ordering combined
with a substantial in-process shuffle buffer as its standard shuffling recipe,
explicitly noting that a true global shuffle isn't practical for its sharded,
streaming access model and that this two-level approach is the accepted,
widely-adopted compromise for large-scale sharded training data.

## Mitigations

### Randomizing sample-to-shard assignment at write time

**What it is:** When creating shards, assign samples to shards pseudo-randomly rather
than in whatever natural order they arrive (chronological, by source, by batch),
reducing intra-shard correlation before any read-time shuffling even happens.

**Cost:** Requires a shuffling or randomization pass during dataset creation, adding
pipeline complexity and, for very large datasets, real compute cost to perform.

**How it backfires:** If new data is added incrementally to an existing dataset (see
[Idempotent Incremental Enrichment](idempotent-incremental-enrichment.md)), naively
appending new shards without re-randomizing against the existing corpus can
reintroduce correlation between "old" and "new" data at the shard level, even if each
individual batch of new data was itself randomized internally.

### Sizing the shuffle buffer against measured correlation risk

**What it is:** Choose an in-memory shuffle buffer size large enough to adequately mix
samples given the dataset's actual intra-shard correlation structure, rather than an
arbitrary default.

**Cost:** A larger buffer increases memory usage per data-loading worker and increases
the startup latency needed to fill the buffer before training can begin.

**How it backfires:** A buffer size tuned for one dataset's correlation structure
(e.g., short video clips) can be inadequate for a different dataset with longer-range
correlation (e.g., a dataset with many samples from the same source document or
session), producing worse-than-expected shuffle quality without an obvious signal that
this is the cause.

### Monitoring for shard-boundary-correlated training metrics

**What it is:** Watch for periodicity in loss curves or other training metrics that
correlates with shard read order, as a diagnostic signal that shuffling isn't
adequately mixing the data.

**Cost:** Requires instrumentation correlating training step number with which shard
was being read, which isn't always straightforward to expose from a given data loading
library.

**How it backfires:** None specific — the absence of this monitoring just means a
shuffle-quality problem is discovered later, via subtler downstream effects on model
quality, rather than caught early and directly.

## Interactions

- [The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md) — the
  precondition that creates the shuffle-vs-throughput tension this pattern resolves.
- [Idempotent Incremental Enrichment](idempotent-incremental-enrichment.md) — new data
  added incrementally has to be integrated into the shuffle strategy carefully to avoid
  reintroducing correlation between old and new shards.
- [Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md) —
  buffer-based shuffling adds memory and startup overhead that compounds with other
  data-loading pipeline costs.

## References

- MosaicML Engineering Blog / Documentation. *Streaming Dataset Shuffling*. Describes
  the shard-order-plus-buffer two-level shuffle strategy and its tuning parameters.
- WebDataset Documentation. *Shuffling*. Describes the recommended shuffle-buffer
  approach for sharded, streaming datasets.
- Bottou, L. *Stochastic Gradient Descent Tricks*. Describes the theoretical
  motivation for well-mixed mini-batches in SGD convergence.
