# Symptom Index

The incident-mode entry point. Find your observable below, then follow the discriminators
to the most likely candidate patterns.

> **Status:** skeleton only — categories are laid out, entries get filled in as each
> pattern family's pages are written (see the family phases). Run `make check-symptoms`
> to see which pattern pages aren't linked here yet.

---

## Distributed training stalls or runs slow

### Wall-clock time doesn't scale with added GPUs

- All-reduce time dominates step time → interconnect-bound distributed training
- One rank consistently lags the rest → silent data corruption and stragglers

### Job crashes and loses significant progress on restart

- Checkpoint interval mistuned relative to failure rate → distributed checkpointing at scale
- Reshaping the process group after a node loss → elastic training vs. hot spares

### GPUs sit idle despite a full input queue

- Data loading can't keep up with compute → data loading as the real bottleneck

---

## Cluster scheduling is unfair or underutilized

### Small jobs wait behind a large gang-scheduled job indefinitely

- No backfill scheduling → gang scheduling for distributed jobs

### One team's burst starves every other team's jobs

- No fair-share quota or borrowing policy → hierarchical fair-share with borrowing

### Fractional GPU sharing causes unexplained slowdowns

- MIG/time-slicing interference between co-scheduled workloads → fractional GPU sharing

---

## Kubernetes control plane is unhealthy

### apiserver latency rises with cluster size, not with load

- Watch fan-out or etcd compaction falling behind → etcd as the hidden bottleneck

### Controllers reconcile in synchronized bursts

- Resync period causing a thundering herd → controller reconciliation storms

---

## Offline/batch inference falls behind or re-does work unnecessarily

### A model version bump triggers reprocessing the entire corpus

- No content-addressed skip for unchanged inputs → content-addressed reprocessing

### GPU batch inference throughput doesn't scale with added workers

- CPU-bound decode starving GPU-bound inference → heterogeneous CPU/GPU batch pipelines

---

## Online serving is slow, expensive, or both

### p99 latency spikes under bursty traffic

- No warm pool, GPU autoscaling too slow → cold starts vs. warm pools

### GPU utilization is low despite queued requests

- Batching window too short or absent → continuous and dynamic batching

---

## Model promotion or experimentation is unreliable

### Two runs that should be comparable produce different-looking results

- Eval set or harness not pinned → fair model comparison under drift

### A model reaches production without going through the tracked pipeline

- No enforced single path to production → the governed pipeline as the only path to production
