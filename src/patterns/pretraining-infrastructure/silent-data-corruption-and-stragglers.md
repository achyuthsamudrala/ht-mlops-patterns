# Silent Data Corruption & Stragglers

> **One-liner:** A quietly miscomputing GPU or a consistently slow rank doesn't crash a job — it corrupts or delays it invisibly, and clean crash-recovery doesn't catch either.

## Symptom

- Training loss shows an unexplained spike or a slow degradation in quality that isn't
  traceable to any code, data, or hyperparameter change.
- One rank in a distributed job consistently takes longer per step than its peers,
  with the whole job's step time bounded by that one slow rank, but no crash or error
  is ever logged.
- A model's final evaluation metrics are unexpectedly poor relative to its training
  loss curve, suggesting some portion of training silently computed something other
  than what was intended.
- The same hardware, swapped into a different job, shows a similar (if less obvious)
  anomaly, suggesting a hardware-level rather than job-level cause.

## Mechanism

Most fault-tolerance design assumes failures announce themselves: a process crashes, a
node becomes unreachable, an exception is thrown. **Silent data corruption (SDC)** is a
failure mode that doesn't announce itself at all — a GPU continues executing and
returning results, but some of those results are quietly wrong, due to a hardware
defect (a bit flip not caught by error-correcting memory, a marginal chip under
thermal or voltage stress) rather than a software bug. Nothing crashes; the job
proceeds, but with corrupted intermediate values that can silently degrade model
quality in ways that are extremely difficult to attribute to their root cause after
the fact, because by the time the effect is visible (a worse-than-expected eval
score), the corrupting event and its downstream numerical consequences are long past.

**Stragglers** are a related but distinct problem: a rank that isn't failed, just
consistently slower than its peers — from thermal throttling, a marginal but
functional hardware component, or a subtly misconfigured node. Because collective
operations block on the slowest participant (see
[GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md)),
a single straggler caps the *entire* job's step time at its own pace, silently
wasting the idle capacity of every other, faster rank for as long as the straggler
remains in the job — and because nothing crashes, standard failure monitoring doesn't
flag it.

Both failure modes share the same defining characteristic: they don't trigger the
crash-and-restart recovery path that checkpointing and elastic scheduling are built
around (see [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md)
and [Elastic Training vs. Hot Spares](elastic-training-vs-hot-spares.md)), because
nothing has actually failed in the sense those mechanisms detect. Catching them
requires active, deliberate detection rather than passive failure-monitoring: per-step
timing comparison across ranks to flag consistent stragglers, and loss or
gradient-norm anomaly detection to flag potential silent corruption, since a corrupted
computation frequently (though not always) produces a numerically detectable
signature — a sudden loss spike, an anomalous gradient norm — even when it doesn't
produce an outright crash.

## Real-world sightings

The original MapReduce paper (Dean and Ghemawat, OSDI 2004) introduced speculative
execution specifically to address straggler tasks in large clusters, explicitly
distinguishing "the machine is slow" stragglers (which speculative re-execution
addresses) from other causes of slowness — a distinction that remains directly
relevant to distributed training straggler detection today, though ML training's
tightly-coupled, synchronous collective operations make simple task re-execution
less directly applicable than it is for MapReduce's independent tasks.

Meta's and Google's published large-scale training infrastructure papers and
engineering blog posts (on training frontier-scale models across many thousands of
GPUs) explicitly discuss silent data corruption as an observed, real production
concern at that scale, motivating hardware-level health-checking and numerical
anomaly-detection mechanisms as first-class parts of their training infrastructure,
rather than an unusual edge case.

## Mitigations

### Per-step timing comparison across ranks

**What it is:** Continuously monitor per-rank step timing and flag a rank that's
consistently slower than its peers as a straggler candidate for investigation or
automatic removal.

**Cost:** Requires instrumentation to collect and compare per-rank timing at fine
granularity, adding monitoring overhead and requiring a threshold for "consistently
slower" that avoids false-positives from normal variance.

**How it backfires:** A too-sensitive threshold flags normal, transient timing
variance (network jitter, brief contention) as a straggler and triggers unnecessary
node replacement; a too-loose threshold misses genuine, persistent stragglers that
are quietly capping the whole job's throughput.

### Loss and gradient-norm anomaly detection with automatic rollback

**What it is:** Monitor loss and gradient norm for anomalous spikes that could
indicate silent corruption, and automatically roll back to the last known-good
checkpoint (and potentially skip or re-fetch the suspect batch) when detected.

**Cost:** Requires defining what counts as "anomalous" versus legitimate training
noise, which varies by model and training phase (some architectures and phases have
naturally higher loss variance than others).

**How it backfires:** Automatic rollback triggered by a legitimate, non-corruption-
related loss spike (a genuinely hard batch, a learning-rate schedule transition)
wastes progress by rolling back training that wasn't actually corrupted — the
detection threshold has to balance false positives against the cost of missing real
corruption.

### Hardware-level health checking and proactive node retirement

**What it is:** Run periodic hardware diagnostics (memory tests, thermal checks, ECC
error-rate monitoring) across the fleet, and proactively retire nodes showing early
warning signs before they cause a training-time SDC or straggler incident.

**Cost:** Requires dedicated diagnostic tooling and scheduled downtime or reduced
availability for nodes undergoing testing, and needs to run frequently enough to catch
degradation before it manifests in an active job.

**How it backfires:** Diagnostics that pass in isolation don't guarantee a node won't
develop an issue under the specific sustained load of a real training job — hardware
health checking reduces but doesn't eliminate the risk of SDC or straggler behavior
appearing mid-job.

## Interactions

- [GPU Interconnect & Collective Communication](../../foundations/gpu-interconnect-and-collective-communication.md) —
  the mechanism by which a single straggler caps an entire job's step time, not just
  its own.
- [Distributed Checkpointing at Scale](distributed-checkpointing-at-scale.md) —
  automatic rollback on detected corruption depends on having a recent, valid
  checkpoint to roll back to.
- [Failure as the Steady State at Fleet Scale](../../foundations/failure-as-the-steady-state.md) —
  the foundational reasoning that failure (including silent failure) is expected at
  this scale, motivating active detection rather than passive monitoring alone.

## References

- Dean, J. and Ghemawat, S. *MapReduce: Simplified Data Processing on Large Clusters*.
  OSDI 2004. Introduces speculative execution for straggler mitigation.
- Ananthanarayanan, G. et al. *Reining in the Outliers in Map-Reduce Clusters using
  Mantri*. OSDI 2010. Extends straggler detection beyond simple speculation, relevant
  to distinguishing genuine hardware-caused stragglers from other slowness causes.
- Hochschild, P. H. et al. (Google). *Cores that don't count*. HotOS 2021. Documents
  silent data corruption as an observed, real phenomenon in large-scale production
  compute fleets.
