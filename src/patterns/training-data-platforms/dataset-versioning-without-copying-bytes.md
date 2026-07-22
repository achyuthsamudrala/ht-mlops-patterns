# Dataset Versioning Without Copying Bytes

> **One-liner:** Reproducible dataset snapshots at petabyte scale require versioning the manifest, not the underlying bytes.

## Symptom

- Reproducing the exact dataset a model was trained on, months later, is impossible
  because the underlying files have since been modified, moved, or deleted, even
  though "the dataset" nominally still exists.
- A dataset "snapshot" mechanism that copies the full dataset per version becomes
  prohibitively expensive as dataset size and version count both grow, since storage
  cost scales with versions × dataset size rather than with what actually changed.
- Two team members working from what they believe is "the same dataset" get subtly
  different results, traced back to one of them reading data that was updated after
  the other's run started.
- A dataset registry records a version identifier, but no one can determine which
  underlying files that identifier actually corresponds to, because there's no
  immutable record separate from the mutable current state of the storage location.

## Mechanism

Petabyte-scale datasets make naive per-version full copies infeasible — the storage
cost of even a handful of full copies of a petabyte-scale corpus is significant, and
most changes between versions are small relative to the total dataset (a new batch of
samples added, a small subset re-labeled or filtered out), so copying the entire
dataset to capture a small delta is enormously wasteful.

The resolution is to version the **manifest** — an ordered, immutable list of
(object key, content hash) pointers describing exactly which underlying objects
constitute a given dataset version — rather than the underlying bytes themselves. A
new dataset version is a new manifest, most of whose entries point to the same
underlying objects as the previous version, with only the actually-changed entries
differing. This is copy-on-write at the metadata layer: the expensive operation (byte
storage) isn't duplicated, only the cheap operation (a list of pointers) is.

This only works cleanly if the underlying object storage is used **immutably**: an
object key, once written, is never overwritten or mutated in place — any change is
written as a new object with a new key (typically content-addressed, keyed by a hash
of its contents), and old manifests continue pointing at old, unchanged objects
indefinitely. If any producer violates this discipline — mutating an existing object
key in place — every manifest pointing at that key silently changes what it
represents, breaking reproducibility for every version that referenced it, often
without any visible error.

Table formats designed for exactly this pattern (Apache Iceberg, Delta Lake) or
purpose-built dataset versioning tools (lakeFS) implement this manifest-versioning
discipline directly, giving git-like branch/snapshot/time-travel semantics over
otherwise-plain object storage without ever requiring a full data copy per version.
Reproducing "the dataset as of version X" becomes reading the manifest for version X
and resolving its pointers — a cheap metadata operation regardless of how large the
underlying dataset is.

## Real-world sightings

lakeFS's own documentation and design posts describe exactly this git-like,
copy-on-write versioning model over object storage, explicitly motivated by the
infeasibility of full-copy-per-version snapshots at the multi-terabyte-to-petabyte
scale typical of ML training datasets.

Apache Iceberg's table specification documents its manifest-list and manifest-file
design as providing atomic, versioned snapshots of very large tables without copying
underlying data files, explicitly designed to support time-travel queries (reading the
table as it existed at a past snapshot) as a first-class, efficient operation rather
than an expensive reconstruction.

## Mitigations

### Strictly immutable, content-addressed object writes

**What it is:** Never overwrite an existing object key; write any changed or new data
under a new key, ideally derived from a content hash so identical content naturally
deduplicates across versions.

**Cost:** Requires write-path discipline enforced across every producer that writes to
the dataset's storage location — a single mutating writer breaks the guarantee for
every version referencing the objects it touched.

**How it backfires:** This discipline has to be enforced organizationally, not just
technically, in most implementations — a well-intentioned but uninformed engineer
"fixing a file in place" can silently invalidate reproducibility for every past
version referencing that file, with no error to signal what happened.

### Manifest-based versioning via a table format or dedicated tool

**What it is:** Use a table format (Iceberg, Delta) or dataset-versioning tool
(lakeFS) that implements manifest-based, copy-on-write versioning natively, rather
than building this discipline from scratch.

**Cost:** Adopting one of these introduces a specific tooling dependency and, for
table formats, a specific metadata-layer scaling profile of its own (see the parallel
concern in [Idempotent Incremental Enrichment](idempotent-incremental-enrichment.md)
about content-addressing's own bookkeeping cost).

**How it backfires:** Manifest structures over billions of objects are themselves
non-trivial metadata to manage; a table format not designed with this scale in mind
can turn the metadata layer itself into a bottleneck, an issue these formats explicitly
address but that a hand-rolled manifest system might not.

### Retention pinned to what's actually referenced

**What it is:** Garbage-collect underlying objects only once no live manifest
version (especially one referenced by a registered model or published dataset)
still points to them, using reference counting rather than a simple time-based
retention window.

**Cost:** Requires tracking which manifests are still "live" (referenced by something
that matters), which is more bookkeeping than a blind time-based deletion policy.

**How it backfires:** Retention policy is a genuine bind: keeping every version
forever is eventually too costly at real scale, while aggressive garbage collection
risks deleting an object an old, still-referenced experiment's reproducibility depends
on — there's no retention policy that's simultaneously free and risk-free.

## Interactions

- [Idempotent Incremental Enrichment](idempotent-incremental-enrichment.md) — both
  patterns depend on content-addressing as the mechanism that makes versioning and
  deduplication cheap; they compound in any pipeline that both enriches and versions
  the same corpus.
- [The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md) —
  manifests typically reference shards rather than individual samples, which is
  consistent with and reinforces the sharding discipline.
- [Reproducibility Levels on Nondeterministic Hardware](../../foundations/reproducibility-levels-on-nondeterministic-hardware.md) —
  dataset versioning is one of the four pillars (code, config, data, container) that
  pipeline-level reproducibility depends on.

## References

- lakeFS Documentation. *Git-like Version Control for Data Lakes*. Describes the
  copy-on-write, manifest-based versioning model over object storage.
- Apache Iceberg Documentation. *Table Spec — Manifests and Snapshots*. Describes
  atomic, versioned table snapshots without full data copies.
- Armbrust, M. et al. *Delta Lake: High-Performance ACID Table Storage over Cloud
  Object Stores*. VLDB 2020. Describes transaction-log-based versioning with the same
  copy-on-write metadata principle.
