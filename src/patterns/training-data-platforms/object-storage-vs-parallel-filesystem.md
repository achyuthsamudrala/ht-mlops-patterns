# Object Storage vs. Parallel Filesystem

> **One-liner:** Object storage is the cheap, durable source of truth; a parallel filesystem is an expensive, ephemeral accelerator you rent for the duration of a run.

## Symptom

- A parallel filesystem (Lustre or equivalent) provisioned for a training cluster is
  treated as the dataset's permanent home, and its cost becomes a large, ongoing line
  item rather than a per-run expense.
- Aggregate training throughput across many nodes is bottlenecked by object storage's
  per-request characteristics even after adopting the shard pattern, because the
  cluster's aggregate read demand exceeds what object storage can sustain.
- A parallel filesystem instance is kept running between training runs "just in case,"
  and its idle cost goes unnoticed until a cost review surfaces it.
- Migrating a dataset from a parallel filesystem back to object storage (after a
  cost-cutting decision) reveals that the parallel filesystem had become the only
  copy of some derived data, with no equivalent object-storage backup.

## Mechanism

Object storage's cost and durability profile — cheap per gigabyte, effectively
unlimited scale, very high durability — makes it the correct default location for a
dataset's source-of-truth copy. But its request-latency and per-object overhead
characteristics (see [The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md))
mean that even with shard-based access, there's a ceiling on the aggregate read
throughput it can sustain across a large cluster of GPU nodes all reading concurrently
during a large training run.

A parallel filesystem (Lustre, and cloud-managed equivalents) is designed for
extremely high aggregate throughput — hundreds of gigabytes per second — feeding many
compute nodes simultaneously, and offers genuine POSIX filesystem semantics that some
tooling expects. This makes it valuable specifically for the duration of a large
training run where aggregate read demand exceeds what object storage alone can
sustain. But it comes at a real cost premium relative to object storage's per-gigabyte
price, and it's designed and priced as high-performance, not as a cost-efficient
long-term archive.

The mechanism that makes this work well: hydrate the parallel filesystem from object
storage for the duration of a run — pulling the working dataset onto it before
training starts — and treat it as ephemeral scratch space, not as a second copy of
truth. This lets a training run get parallel-filesystem-class throughput without
paying parallel-filesystem-class cost indefinitely, since the filesystem instance can
be torn down (or scaled down) once the run completes.

The failure mode described in the symptom list happens when this discipline erodes:
a parallel filesystem instance provisioned for one run stays running because tearing
it down and re-hydrating it for the next run feels like unnecessary friction, and
gradually it accumulates the status of a permanent, load-bearing system — at which
point its cost is no longer bounded by run duration, and worse, if any data ever
exists only there (a derived artifact regenerated during the run but never written
back to object storage), tearing it down risks real data loss.

## Real-world sightings

AWS's, GCP's, and Azure's own documentation for their managed Lustre offerings (FSx
for Lustre, Parallelstore/Managed Lustre, Azure Managed Lustre) explicitly describes
the hydrate-from-object-storage, scratch-for-a-run usage pattern as the intended
design, including automatic linking/sync features specifically built to make treating
the parallel filesystem as ephemeral straightforward rather than requiring manual data
management.

This "object storage is truth, fast filesystem is a rented accelerator" pattern
predates any single cloud vendor's specific product and reflects long-standing HPC
practice of using burst-buffer or scratch storage tiers ahead of long-term archival
storage — the specific technology names change, but the tiering discipline is a
decades-old idea in high-performance computing storage architecture.

## Mitigations

### Treating the parallel filesystem as ephemeral, torn down after each run

**What it is:** Provision the parallel filesystem instance specifically for a training
run's duration, hydrate it from object storage at the start, and tear it down (or
allow it to scale to zero) once the run completes.

**Cost:** Requires re-hydration time at the start of each run, adding startup latency
compared to a permanently-running filesystem.

**How it backfires:** If re-hydration is slow relative to run frequency (many short
runs in succession), the cumulative hydration overhead can erode much of the cost
benefit of tearing the filesystem down between runs — there's a real crossover point
where "just leave it running" becomes cheaper for high-frequency, short-duration
workloads.

### Never treating the parallel filesystem as the sole copy of any data

**What it is:** Ensure any data that exists on the parallel filesystem also exists (or
will be written back) to object storage, so tearing down the filesystem never risks
losing data that exists nowhere else.

**Cost:** Requires an explicit write-back step for any data generated or modified
during a run on the fast filesystem, adding pipeline complexity.

**How it backfires:** A write-back step that's added as an afterthought, rather than
being a required, verified part of the pipeline, is exactly the kind of discipline
that erodes under deadline pressure — "we'll write it back later" becoming "we forgot,
and then tore down the filesystem."

### Sizing parallel filesystem use to genuine aggregate-throughput need

**What it is:** Reserve parallel filesystem provisioning for cases where measured
aggregate read demand across the cluster genuinely exceeds what object storage (with
proper sharding) can sustain, rather than reaching for it by default.

**Cost:** Requires actually measuring aggregate throughput requirements rather than
assuming a parallel filesystem is always the safe, high-performance choice.

**How it backfires:** Underestimating aggregate throughput needs and skipping the
parallel filesystem tier for a genuinely throughput-constrained workload reintroduces
the object-storage bottleneck this tier exists to solve — this mitigation cuts both
ways and requires real measurement, not a default assumption in either direction.

## Interactions

- [The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md) —
  sharding is what makes object storage viable at all; parallel filesystems are the
  additional layer for when even well-sharded object storage can't sustain aggregate
  cluster throughput.
- [Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md) —
  the cluster-level symptom this tiering decision is directly trying to prevent.
- [The Managed vs. Build Tradeoff](../../foundations/the-managed-vs-build-tradeoff.md) —
  managed Lustre offerings versus self-operated parallel filesystems is itself an
  instance of the broader managed-vs-build axis.

## References

- Amazon Web Services Documentation. *Amazon FSx for Lustre*. Describes hydration
  from and linking to S3 for ephemeral, run-scoped high-throughput storage.
- Google Cloud Documentation. *Parallelstore*. Describes the managed Lustre-class
  offering and its intended usage pattern alongside Cloud Storage.
- Braam, P. *The Lustre Storage Architecture*. Describes the parallel filesystem
  design intended for high-aggregate-throughput HPC and ML training workloads.
