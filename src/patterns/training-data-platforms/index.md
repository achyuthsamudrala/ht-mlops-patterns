# Training Data Platforms

These patterns address how training data is stored, sharded, versioned, and enriched at a scale where naive small-file access patterns collapse under object storage's request-latency characteristics.

## Reading order

[The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md) first — it's the foundational decision every other pattern in this family assumes. Then [Object Storage vs. Parallel Filesystem](object-storage-vs-parallel-filesystem.md) for the storage-tier tradeoff that shard-based streaming depends on.

## Patterns in this section

- [The Shard Pattern for Training Data](the-shard-pattern-for-training-data.md)
- [Object Storage vs. Parallel Filesystem](object-storage-vs-parallel-filesystem.md)
- [GPU-Accelerated Video Decode](gpu-accelerated-video-decode.md)
- [Two-Level Shuffle for Streaming Datasets](two-level-shuffle-for-streaming-datasets.md)
- [Dataset Versioning Without Copying Bytes](dataset-versioning-without-copying-bytes.md)
- [Idempotent Incremental Enrichment](idempotent-incremental-enrichment.md)
