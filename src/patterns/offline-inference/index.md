# Offline / Batch Inference

These patterns cover running models over large, growing datasets as GPU batch jobs — where idempotency and content-addressing are what keep a backfill from becoming an unbounded, unrepeatable cost.

## Reading order

[Content-Addressed Reprocessing](content-addressed-reprocessing.md) first — it's the mechanism that makes every other mitigation in this family affordable.

## Patterns in this section

- [Heterogeneous CPU/GPU Batch Pipelines](heterogeneous-cpu-gpu-batch-pipelines.md)
- [Content-Addressed Reprocessing](content-addressed-reprocessing.md)
- [Spot-Backed Backfill Under a Budget Cap](spot-backed-backfill-under-budget.md)
- [Backpressure in GPU Batch Inference](backpressure-in-gpu-batch-inference.md)
- [Lineage-Scoped Backfills](lineage-scoped-backfills.md)
