# Summary

[Introduction](introduction.md)
[Symptom Index](symptom-index.md)
[Interaction Map](interaction-map.md)

---

# Foundations

- [GPU Interconnect & Collective Communication](foundations/gpu-interconnect-and-collective-communication.md)
- [The Managed vs. Build Tradeoff](foundations/the-managed-vs-build-tradeoff.md)
- [Reproducibility Levels on Nondeterministic Hardware](foundations/reproducibility-levels-on-nondeterministic-hardware.md)
- [Failure as the Steady State at Fleet Scale](foundations/failure-as-the-steady-state.md)
- [Consensus & the CAP Tradeoff for Cluster State](foundations/consensus-and-the-cap-tradeoff.md)
- [Gang Scheduling vs. Bin-Packing](foundations/gang-scheduling-vs-bin-packing.md)

---

# Patterns


- [Training Data Platforms](patterns/training-data-platforms/index.md)
  - [The Shard Pattern for Training Data](patterns/training-data-platforms/the-shard-pattern-for-training-data.md)
  - [Object Storage vs. Parallel Filesystem](patterns/training-data-platforms/object-storage-vs-parallel-filesystem.md)
  - [GPU-Accelerated Video Decode](patterns/training-data-platforms/gpu-accelerated-video-decode.md)
  - [Two-Level Shuffle for Streaming Datasets](patterns/training-data-platforms/two-level-shuffle-for-streaming-datasets.md)
  - [Dataset Versioning Without Copying Bytes](patterns/training-data-platforms/dataset-versioning-without-copying-bytes.md)
  - [Idempotent Incremental Enrichment](patterns/training-data-platforms/idempotent-incremental-enrichment.md)

- [Large-Scale Pretraining Infrastructure](patterns/pretraining-infrastructure/index.md)
  - [Interconnect-Bound Distributed Training](patterns/pretraining-infrastructure/interconnect-bound-distributed-training.md)
  - [Composing Parallelism Strategies](patterns/pretraining-infrastructure/composing-parallelism-strategies.md)
  - [Data Loading as the Real Bottleneck](patterns/pretraining-infrastructure/data-loading-as-the-real-bottleneck.md)
  - [Distributed Checkpointing at Scale](patterns/pretraining-infrastructure/distributed-checkpointing-at-scale.md)
  - [Silent Data Corruption & Stragglers](patterns/pretraining-infrastructure/silent-data-corruption-and-stragglers.md)
  - [Elastic Training vs. Hot Spares](patterns/pretraining-infrastructure/elastic-training-vs-hot-spares.md)
  - [SLURM vs. Kubernetes for Training](patterns/pretraining-infrastructure/slurm-vs-kubernetes-for-training.md)

- [GPU Scheduling & Multi-Tenancy](patterns/gpu-scheduling/index.md)
  - [Gang Scheduling for Distributed Jobs](patterns/gpu-scheduling/gang-scheduling-for-distributed-jobs.md)
  - [Topology-Aware Placement](patterns/gpu-scheduling/topology-aware-placement.md)
  - [Preemption & Checkpoint-Gated Interruption](patterns/gpu-scheduling/preemption-and-checkpoint-gated-interruption.md)
  - [Hierarchical Fair-Share with Borrowing](patterns/gpu-scheduling/hierarchical-fair-share-with-borrowing.md)
  - [Fractional GPU Sharing](patterns/gpu-scheduling/fractional-gpu-sharing.md)
  - [Utilization vs. Researcher Velocity](patterns/gpu-scheduling/utilization-vs-researcher-velocity.md)

- [Kubernetes Control Plane at Scale](patterns/control-plane-at-scale/index.md)
  - [etcd as the Hidden Bottleneck](patterns/control-plane-at-scale/etcd-as-the-hidden-bottleneck.md)
  - [API Priority and Fairness](patterns/control-plane-at-scale/api-priority-and-fairness.md)
  - [Controller Reconciliation Storms](patterns/control-plane-at-scale/controller-reconciliation-storms.md)
  - [Scaling Limits: Nodes vs. Objects vs. Watches](patterns/control-plane-at-scale/scaling-limits-nodes-objects-watches.md)
  - [Raft Consensus for Cluster State](patterns/control-plane-at-scale/raft-consensus-for-cluster-state.md)

- [Cluster Services & Operators](patterns/cluster-services/index.md)
  - [Operator Reconciliation Idempotency](patterns/cluster-services/operator-reconciliation-idempotency.md)
  - [Service Discovery at Fleet Scale](patterns/cluster-services/service-discovery-at-fleet-scale.md)
  - [Owner References & Garbage Collection](patterns/cluster-services/owner-references-and-garbage-collection.md)
  - [CRD Schema Evolution & Conversion Webhooks](patterns/cluster-services/crd-schema-evolution-and-conversion-webhooks.md)
  - [Graceful Degradation for Invisible Infrastructure](patterns/cluster-services/graceful-degradation-for-invisible-infrastructure.md)

- [Offline / Batch Inference](patterns/offline-inference/index.md)
  - [Heterogeneous CPU/GPU Batch Pipelines](patterns/offline-inference/heterogeneous-cpu-gpu-batch-pipelines.md)
  - [Content-Addressed Reprocessing](patterns/offline-inference/content-addressed-reprocessing.md)
  - [Spot-Backed Backfill Under a Budget Cap](patterns/offline-inference/spot-backed-backfill-under-budget.md)
  - [Backpressure in GPU Batch Inference](patterns/offline-inference/backpressure-in-gpu-batch-inference.md)
  - [Lineage-Scoped Backfills](patterns/offline-inference/lineage-scoped-backfills.md)

- [Online Serving Systems](patterns/online-serving/index.md)
  - [Serving Mode Selection](patterns/online-serving/serving-mode-selection.md)
  - [Continuous & Dynamic Batching](patterns/online-serving/continuous-and-dynamic-batching.md)
  - [Cold Starts vs. Warm Pools](patterns/online-serving/cold-starts-vs-warm-pools.md)
  - [Quantization & Compiled Runtimes](patterns/online-serving/quantization-and-compiled-runtimes.md)
  - [Multi-Region GPU Capacity Failover](patterns/online-serving/multi-region-gpu-capacity-failover.md)
  - [Serving Protocol Standardization](patterns/online-serving/serving-protocol-standardization.md)
  - [Tiered SLOs for Mixed Traffic](patterns/online-serving/tiered-slos-for-mixed-traffic.md)

- [Workflow Orchestration for ML](patterns/workflow-orchestration/index.md)
  - [Task-Centric vs. Asset/Lineage-Centric Orchestration](patterns/workflow-orchestration/task-centric-vs-asset-centric-orchestration.md)
  - [Backfill as a First-Class Orchestration Concern](patterns/workflow-orchestration/backfill-as-a-first-class-concern.md)
  - [GitOps Promotion for ML Pipelines](patterns/workflow-orchestration/gitops-promotion-for-ml-pipelines.md)
  - [The Governed Pipeline as the Only Path to Production](patterns/workflow-orchestration/the-governed-pipeline-as-the-only-path-to-production.md)

- [Model Lifecycle & Experimentation](patterns/model-lifecycle/index.md)
  - [Experiment Tracking vs. Registry vs. Lineage Store](patterns/model-lifecycle/experiment-tracking-vs-registry-vs-lineage.md)
  - [Fair Model Comparison Under Drift](patterns/model-lifecycle/fair-model-comparison-under-drift.md)
  - [Gated Promotion Pipelines](patterns/model-lifecycle/gated-promotion-pipelines.md)
  - [Multimodal Dataset Exploration & Curation](patterns/model-lifecycle/multimodal-dataset-exploration-and-curation.md)
  - [The Fast Path and the Rigorous Path](patterns/model-lifecycle/the-fast-path-and-the-rigorous-path.md)
