# Idempotent Incremental Enrichment

> **One-liner:** Content-addressed, versioned derived data turns dataset enrichment into a reconciliation problem instead of a fragile one-off batch job.

## Symptom

- Updating a single enrichment model (a captioning model, an embedding model, a
  quality classifier) triggers a full reprocessing of the entire historical corpus,
  costing days of GPU time even though most of the corpus is logically unaffected by
  the change.
- A pipeline interrupted partway through a large enrichment job either reprocesses
  already-completed work on restart (wasting compute) or, worse, loses track of what
  was already completed and silently skips it.
- Two runs of the same enrichment pipeline against the same input, separated by a
  retry, produce duplicate derived records rather than one canonical record per input.
- New data arriving continuously and full-corpus backfills triggered by model updates
  are implemented as two entirely separate code paths, doubling the maintenance
  burden and doubling the chance of them diverging in behavior.

## Mechanism

Enriching a large, continuously growing dataset with one or more ML models
(captioning, embedding, detection, quality scoring) has two properties that make a
naive one-off batch job fragile at scale: the corpus keeps growing (new data arrives
continuously, requiring incremental processing) and the enrichment logic itself keeps
changing (a new or updated model version requires reprocessing some or all of the
existing corpus). Treating these as unrelated problems — a streaming pipeline for new
data, a separate ad-hoc script for backfills — means solving the idempotency and
recovery problem twice, and it's easy for the two paths to diverge in subtle ways.

**Content-addressed derived data** resolves the duplicate-work and recovery problems
directly: key every derived artifact by a deterministic function of
`(content_hash, model_id, model_version, params_hash)`. Processing becomes naturally
idempotent — if an artifact with that exact key already exists, the work is already
done and can be skipped, regardless of whether the request to (re)process it came from
a retry, a duplicate scheduling, or an actual reprocessing need. Re-processing only
happens when one of those key components actually changes: new content, or a new model
version, or new processing parameters.

**Desired-state reconciliation** unifies the streaming-versus-backfill dichotomy: a
state table tracks, for every (content, required enrichment) pair, whether the
corresponding content-addressed artifact currently exists. A reconciliation loop
continuously computes the difference between "what enrichments should exist given the
current corpus and current model versions" and "what enrichments actually exist," and
enqueues work only for the delta. A new video arriving and a new model version both
just add rows to the desired-state side of this diff — the same reconciliation
mechanism handles both, rather than requiring separate code paths.

This reframes the entire problem: instead of writing and maintaining "a pipeline that
runs on new data" and separately "a pipeline that runs a backfill," there's one
mechanism — reconcile actual against desired — that naturally produces the correct
behavior for both cases, is safe to retry or run concurrently (since content-addressed
idempotency means duplicate work is simply wasted compute, never a correctness issue),
and scopes a model-version bump's reprocessing cost to exactly what changed rather
than requiring a special, hand-built backfill script each time.

## Real-world sightings

Content-addressed storage as a mechanism for idempotent, deduplicating processing is
a long-standing pattern in build systems (Bazel, Nix) and increasingly in ML data
pipelines specifically — the underlying principle (key derived artifacts by a hash of
their true inputs, so identical inputs never redundantly reprocess) transfers directly
from those domains to ML enrichment pipelines, even though the specific tooling
differs.

Desired-state reconciliation as the unifying mechanism for "new data" and "changed
processing logic" is the same core design pattern Kubernetes controllers use broadly
(see [Operator Reconciliation Idempotency](../cluster-services/operator-reconciliation-idempotency.md)
for the general version of this pattern) — reconciling observed state against desired
state, rather than reacting to discrete events, handles both the steady-state and the
bulk-change case with one code path, which is precisely why this design shows up
repeatedly across distributed systems facing an analogous problem.

## Mitigations

### Content-addressed keys spanning content, model, and parameters

**What it is:** Key every derived artifact by a hash of its actual dependencies —
input content, model version, and processing parameters — so identical inputs to
identical processing logic are recognized as already-done work.

**Cost:** Requires computing and checking hashes on every processing attempt, adding
modest overhead, and requires every enrichment step in the pipeline to participate in
this keying discipline consistently.

**How it backfires:** If a model's *behavior* changes without its *version identifier*
changing (a common mistake — updating model weights or serving code without bumping a
version string), content-addressing silently serves stale, incorrect cached results
under a key that no longer accurately represents what actually produced them.

### Desired-state reconciliation as the sole processing entry point

**What it is:** Route both new-data arrival and model-version-driven backfills through
the same reconciliation loop, rather than maintaining separate streaming and backfill
code paths.

**Cost:** Requires a scalable state table tracking (content, enrichment, version,
status) across potentially billions of rows, which is itself a real engineering
problem at large corpus sizes.

**How it backfires:** The state table itself needs partitioning and garbage collection
of stale entries (superseded model versions no longer needed); without this, the
control-plane table can become as large a scaling problem as the data it's tracking.

### Priority tiers and spot-backed capacity for backfill work

**What it is:** Run new-data enrichment at high priority and full-corpus backfills as
lower-priority, opportunistic (often spot/preemptible) work that fills otherwise-idle
GPU capacity under an explicit budget or capacity cap.

**Cost:** Backfill throughput becomes variable and opportunistic rather than
guaranteed, meaning a large backfill's completion time is less predictable.

**How it backfires:** This mitigation depends on the backfill work actually being
safely preemptible and resumable — if content-addressed idempotency and reconciliation
aren't correctly implemented, preempting a spot-backed backfill job risks losing
partial progress rather than simply resuming it later at no correctness cost.

## Interactions

- [Dataset Versioning Without Copying Bytes](dataset-versioning-without-copying-bytes.md) —
  both patterns rely on content-addressing as the enabling mechanism, and typically
  compound in any pipeline that both versions its raw data and enriches it.
- [Content-Addressed Reprocessing](../offline-inference/content-addressed-reprocessing.md) —
  the batch-inference-layer application of the exact same content-addressing
  discipline described here.
- [Operator Reconciliation Idempotency](../cluster-services/operator-reconciliation-idempotency.md) —
  the general control-theory pattern (reconcile observed against desired state) this
  page's enrichment-specific application is drawn from.

## References

- Kubernetes Documentation. *Controllers*. Describes the desired-state reconciliation
  pattern this page's enrichment control loop directly borrows from.
- Bazel Documentation. *Content-Addressed Storage and Remote Caching*. Describes
  content-addressing as a general mechanism for idempotent, deduplicating build/
  processing systems.
- Dean, J. and Ghemawat, S. *MapReduce: Simplified Data Processing on Large Clusters*.
  OSDI 2004. Foundational treatment of large-scale batch reprocessing patterns this
  approach improves on for the incremental case.
