# Lineage-Scoped Backfills

> **One-liner:** Recorded lineage between a derived dataset and the model version that produced it lets a backfill reprocess only what a model change actually affects, instead of the whole corpus.

## Symptom

- A model update affecting only one of several enrichment outputs (say, a captioning
  model, when embeddings and quality scores come from separate, unaffected models)
  triggers a full reprocessing pass touching all enrichment outputs, not just the
  affected one.
- Determining exactly which derived artifacts depend on a specific model version, or
  a specific source dataset version, requires manual investigation across pipeline
  code and configuration rather than a direct query.
- A backfill scoped "conservatively" (reprocessing more than strictly necessary, to
  avoid missing anything) costs substantially more GPU time than a precisely-scoped
  one would have, because the actual dependency relationships weren't tracked well
  enough to scope precisely.
- Downstream consumers of a derived dataset can't determine, after the fact, exactly
  which model versions and source data actually contributed to a specific result
  they're looking at.

## Mechanism

Content-addressed reprocessing (see [Content-Addressed Reprocessing](content-addressed-reprocessing.md))
already scopes reprocessing to whatever the content-addressed key indicates has
actually changed, but this scoping is implicit — it emerges from the key structure,
not from an explicit, queryable record of *why* a given piece of reprocessing is or
isn't necessary. **Lineage tracking** makes the dependency relationship explicit:
recording, for every derived artifact, exactly which source content and which model
version(s) produced it, as first-class, queryable metadata rather than something only
implicitly encoded in a content-addressed key.

This matters most precisely when a model update affects only *part* of a pipeline's
outputs. A pipeline enriching video with several independent models (captioning,
embedding, quality scoring) produces outputs that, correctly, have independent
lineage: an update to the captioning model should only invalidate captioning outputs,
not embeddings or quality scores, since those come from entirely different models
operating on the same source content. Without explicit lineage tracking, a
conservative implementation might not be confident in this independence and choose to
reprocess everything "to be safe" — content-addressing alone tells you *that* an
artifact's key hasn't changed, but doesn't as directly express the *reasoning* about
which specific upstream changes should or shouldn't matter to which specific
downstream outputs, which is exactly what makes precise, confident scoping possible.

Lineage also serves purposes beyond backfill scoping: it's what makes it possible to
answer, after the fact, "which model version and which source data actually produced
this specific result" — a question that matters for debugging (did a bad output come
from bad source data or a bad model?), for governance (can we prove what produced a
given piece of training data or evaluation result?), and for reproducibility more
generally, connecting directly to the broader theme of making pipelines auditable
rather than opaque.

## Real-world sightings

OpenLineage and Marquez, open-source lineage-tracking projects designed to integrate
with data orchestration tools, explicitly describe lineage tracking's role in
scoping reprocessing precisely and in answering provenance questions after the fact —
both capabilities motivated directly by the imprecise-scoping and unclear-provenance
problems described above.

Lineage-first orchestration frameworks (Dagster's asset-based model, Flyte's
lineage tracking) build lineage tracking into their core execution model rather than
treating it as an add-on, explicitly framing this as what makes precise,
confidence-scoped backfills possible — a design choice discussed directly in both
projects' documentation as a differentiator from task-centric orchestrators that
don't track data/model asset lineage as a first-class concept.

## Mitigations

### Recording explicit lineage edges for every derived artifact

**What it is:** Record, as queryable metadata, exactly which source content and
model version(s) produced each derived artifact, rather than relying only on
content-addressed keys to implicitly encode this.

**Cost:** Requires instrumenting every pipeline stage to emit lineage records, adding
implementation and storage overhead beyond what content-addressing alone requires.

**How it backfires:** Lineage tracking that's incomplete (some pipeline stages emit
lineage records, others don't) provides a false sense of completeness — a backfill
scoped using incomplete lineage can miss genuinely-affected downstream artifacts that
simply weren't tracked.

### Using lineage to scope backfills precisely rather than conservatively

**What it is:** When a model version changes, use recorded lineage to identify
exactly which derived artifacts depend on that specific model, scoping the backfill
to only those, rather than defaulting to a broader, "safer" reprocessing scope out
of uncertainty.

**Cost:** Requires trusting the lineage record's accuracy enough to scope
conservatively based on it — if lineage tracking has gaps, precise scoping based on
it can miss genuinely-affected artifacts.

**How it backfires:** Precise scoping based on lineage is only as trustworthy as the
lineage data itself; a team that adopts precise scoping without first validating
lineage completeness can under-reprocess and silently leave stale, un-updated
artifacts in place.

### Adopting a lineage-first orchestrator rather than bolting lineage onto a task-centric one

**What it is:** Use an orchestration framework that tracks data/model lineage as a
first-class part of its execution model (Dagster, Flyte), rather than retrofitting
lineage tracking onto a task-centric orchestrator not originally designed for it.

**Cost:** Represents a more significant orchestration-tooling choice, potentially
requiring migration from an existing task-centric orchestrator if one is already in
use.

**How it backfires:** None specific to making this architectural choice deliberately
— the risk is in the reverse: retrofitting lineage tracking onto a task-centric
system as an afterthought, which tends to produce exactly the incomplete-lineage
problem described above.

## Interactions

- [Content-Addressed Reprocessing](content-addressed-reprocessing.md) — the
  foundational idempotency mechanism this pattern's lineage tracking adds precise,
  explicit scoping on top of.
- [Task-Centric vs. Asset/Lineage-Centric Orchestration](../workflow-orchestration/task-centric-vs-asset-centric-orchestration.md) —
  the broader architectural choice that determines how naturally lineage tracking
  fits into a given orchestration platform.
- [Fair Model Comparison Under Drift](../model-lifecycle/fair-model-comparison-under-drift.md) —
  a related use of lineage: pinning exactly which model, eval set, and code version
  produced a given comparison result.

## References

- OpenLineage Documentation. *OpenLineage Specification*. Describes a standardized
  lineage metadata model for data and ML pipelines.
- Dagster Documentation. *Software-Defined Assets*. Describes an asset/lineage-first
  orchestration model built around exactly this precise-scoping capability.
- Flyte Documentation. *Data Lineage and Caching*. Describes lineage-aware caching
  and reprocessing scoping in a Kubernetes-native ML orchestration platform.
