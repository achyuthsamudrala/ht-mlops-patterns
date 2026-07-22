# The Shard Pattern for Training Data

> **One-liner:** Packing samples into large sequential shards is what makes object-storage-backed training data loading viable at all.

## Symptom

- A training job reading directly from millions of small individual objects in cloud
  storage spends most of its wall-clock time on I/O rather than compute, with GPU
  utilization far below what the hardware should sustain.
- Listing or enumerating the dataset's files takes minutes to hours before training
  can even begin.
- Throughput scales poorly with added data-loading workers, because each worker is
  bottlenecked by per-request latency rather than by available bandwidth.
- A dataset migrated from a small pilot scale to full production scale (still stored
  as individual files) sees data-loading throughput degrade disproportionately to the
  data volume increase.

## Mechanism

Object storage (S3, GCS, Blob Storage, and equivalents) is built for durability,
scale, and cost-efficiency, not for low-latency random access to millions of tiny
objects. Every object read incurs meaningful fixed per-request overhead — connection
setup, request routing, metadata lookup — that's largely independent of the object's
size. For a training dataset made of millions of small individual samples (an image, a
short audio clip, a small JSON record), this per-request overhead dominates total read
cost, and the theoretical bandwidth an object store can sustain becomes irrelevant
because the workload is fundamentally request-rate-bound, not bandwidth-bound.

The shard pattern resolves this by packing many samples into large, sequentially-
readable files — WebDataset-style tar shards, MosaicML's Streaming Dataset format
(MDS), TFRecord, or similar. A single read against a shard retrieves many samples'
worth of data in one request, amortizing the fixed per-request cost across hundreds
or thousands of samples instead of paying it once per sample. This converts the access
pattern from "many small random reads" (object storage's worst case) into "few large
sequential reads" (close to object storage's best case), and is the single most
consequential decision in designing a training data pipeline at scale.

Sharding does introduce a real cost of its own: samples are no longer independently
addressable in the same lightweight way, which has downstream consequences for
shuffling (see [Two-Level Shuffle for Streaming Datasets](two-level-shuffle-for-streaming-datasets.md))
and for versioning individual samples (see
[Dataset Versioning Without Copying Bytes](dataset-versioning-without-copying-bytes.md)).
Shard size itself is a tuning parameter: too small and per-request overhead
reappears at the shard level; too large and a single shard read becomes a
coarse-grained unit that's expensive to skip or resume mid-shard.

## Real-world sightings

WebDataset's project documentation explicitly frames its tar-shard design around
exactly this problem: sequential, high-throughput reads from object storage or network
filesystems, motivated by the observed poor performance of naive small-file-per-sample
datasets at scale, particularly for large image and video training corpora where
sample counts commonly reach into the hundreds of millions.

MosaicML's engineering blog posts on their Streaming Dataset library describe the same
motivating problem independently arrived at — designing a shard format and reader
specifically to make training directly from cloud object storage (rather than
requiring the entire dataset to be localized to fast local disk first) practical at
large scale, with shard size and shuffle-buffer configuration as explicit, documented
tuning knobs.

## Mitigations

### Packing samples into shards at write time

**What it is:** Structure the dataset-creation pipeline to write shards directly,
rather than writing individual sample files and sharding as an afterthought.

**Cost:** Requires the ingestion or curation pipeline to buffer and batch samples
before writing, adding pipeline complexity compared to a naive one-file-per-sample
write path.

**How it backfires:** A shard boundary chosen without regard to how the dataset will
later be filtered or subsetted (e.g., shards mixing samples that a later curation pass
wants to include and exclude) can force reading and discarding a lot of unwanted data
just to reach the wanted samples within a shard.

### Tuning shard size to the workload's actual throughput needs

**What it is:** Choose a shard size (commonly on the order of hundreds of megabytes)
that amortizes per-request overhead without making individual shards so large that
skipping or resuming mid-shard becomes expensive.

**Cost:** Requires empirical tuning against the specific storage backend and network
path in use; there's no universal correct shard size.

**How it backfires:** A shard size tuned for one storage backend's request-latency
characteristics can be poorly suited after a migration to a different backend or
region with different latency behavior.

### Sharding derived/enriched data the same way as raw data

**What it is:** Apply the same shard-packing discipline to derived artifacts (extracted
frames, embeddings, enrichment outputs), not just the original raw dataset.

**Cost:** Requires enrichment and preprocessing pipelines to be shard-aware, rather
than naively writing one output file per input sample.

**How it backfires:** Derived data pipelines are often built later, by different teams,
than the original data ingestion pipeline, and it's easy for the shard discipline
established for raw data to not be replicated for derived data, reintroducing the
small-file problem one layer downstream.

## Interactions

- [Two-Level Shuffle for Streaming Datasets](two-level-shuffle-for-streaming-datasets.md) —
  sharding is the precondition this pattern's shuffle strategy is built around; true
  per-sample random access, which sharding deliberately avoids, would otherwise be
  needed for a naive global shuffle.
- [Object Storage vs. Parallel Filesystem](object-storage-vs-parallel-filesystem.md) —
  shard-based sequential reads are precisely what makes object storage viable as the
  primary training data source in the first place.
- [Data Loading as the Real Bottleneck](../pretraining-infrastructure/data-loading-as-the-real-bottleneck.md) —
  poor shard design is one of the most common root causes of GPU-starving data
  loading.

## References

- WebDataset Documentation. *WebDataset Format and Design*. Describes the tar-shard
  format and its motivation for sequential, high-throughput reads from object storage.
- MosaicML Engineering Blog. *Introducing Streaming Datasets*. Describes shard-based
  streaming directly from cloud object storage at large scale.
- Melnik, S. et al. *Dremel: Interactive Analysis of Web-Scale Datasets*. VLDB 2010.
  Broader context on why large, contiguous chunked reads outperform many small ones on
  distributed storage systems generally.
