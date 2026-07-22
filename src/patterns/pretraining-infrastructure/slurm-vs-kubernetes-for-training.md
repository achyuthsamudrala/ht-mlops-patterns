# SLURM vs. Kubernetes for Training

> **One-liner:** SLURM optimizes for the researcher's single tightly-coupled job; Kubernetes optimizes for a platform running many concurrent workloads under one operational model.

## Symptom

- Researchers accustomed to a simple `sbatch`/`srun` mental model find a
  Kubernetes-based training platform's job submission and gang-scheduling behavior
  unfamiliar and higher-friction, even when the underlying capability is equivalent.
- A platform team wants a single operational model spanning training, evaluation, and
  serving, but the training team's existing workflows are built entirely around
  SLURM's job semantics.
- Kubernetes' default scheduler, without additional tooling, mishandles gang
  scheduling for large distributed training jobs (see
  [Gang Scheduling vs. Bin-Packing](../../foundations/gang-scheduling-vs-bin-packing.md)),
  requiring add-ons that SLURM provides natively.
- An organization runs both SLURM (for training) and Kubernetes (for serving and other
  services) and pays the operational cost of maintaining two separate scheduling
  substrates and on-call rotations.

## Mechanism

SLURM originates from and remains deeply rooted in high-performance computing, where
the dominant workload shape is a single large, tightly-coupled job (an MPI-style
application, or a large distributed training run) that needs a specific, fixed set of
resources gang-scheduled together, run to completion, and released. SLURM's core
abstractions (`sbatch`, `srun`, job arrays, gang scheduling as a built-in, first-class
capability) map directly onto this workload shape, and its operational model is
comparatively simple for exactly this reason — one primary kind of workload, well
supported natively.

Kubernetes was designed for a different dominant case: many independent, loosely-
coupled services running concurrently, each independently scaled and managed, with
gang scheduling as an atypical requirement rather than the default assumption. Vanilla
Kubernetes handles this original use case well but has no native concept of
"schedule these N pods together or none at all" — that has to be layered on via
additional tooling (Volcano, Kueue, or similar gang-scheduling-aware schedulers/
queuing systems), because it wasn't part of the platform's original design center.

The organizational-level tradeoff follows directly from this: teams whose primary
need is running large, tightly-coupled training jobs, and whose users (researchers)
value the simple, direct control SLURM's job model provides, tend to prefer SLURM —
it's a better fit for the dominant workload shape and requires less additional
tooling to get gang scheduling right. Teams that need one operational substrate
spanning training, evaluation, and production serving — sharing infrastructure,
tooling, CI/CD integration, and on-call model across all of them — tend to prefer
Kubernetes, accepting the added complexity of gang-scheduling add-ons in exchange for
not operating two entirely separate scheduling systems with two different
operational models, upgrade cadences, and skill requirements.

Neither framing is a universal answer: an organization can and often does run both,
using SLURM for the training-specific workload where its native fit is strongest, and
Kubernetes for everything else, accepting the cost of operating two systems as the
price of giving each workload shape the scheduler best suited to it — this is a common
enough pattern that it's worth naming as a legitimate third option, not just a
compromise forced by indecision.

## Real-world sightings

SLURM's own documentation and its long history as the dominant HPC scheduler
(originating in and remaining widely deployed across national labs and HPC centers)
directly reflects its design center around gang-scheduled, tightly-coupled batch jobs
— this isn't a retrofit, it's the workload SLURM was built for from the start.

Kubernetes' gang-scheduling gap and the corresponding rise of Kueue and Volcano as
purpose-built extensions are explicitly documented in both projects' own design
rationale, each framing their existence around the specific limitation that vanilla
Kubernetes scheduling wasn't designed for all-or-nothing batch job placement — a
gap that had to be filled by dedicated tooling precisely because it wasn't native.

## Mitigations

### Choosing based on dominant workload shape, not tooling familiarity alone

**What it is:** Base the SLURM-versus-Kubernetes decision on whether the
organization's actual dominant workload is large, tightly-coupled training jobs
(favoring SLURM) or a mix of training, evaluation, and serving needing one
operational substrate (favoring Kubernetes), rather than defaulting to whichever the
existing team happens to already know.

**Cost:** Requires an honest assessment of workload shape, which can be
uncomfortable if it points away from the tooling a team already has expertise in.

**How it backfires:** An organization's dominant workload shape can shift over time
(a research-heavy lab that grows a significant production-serving business) without a
corresponding re-evaluation of the scheduling substrate choice, leaving a mismatch that
compounds as the newer workload type grows.

### Running both, deliberately, for their respective strengths

**What it is:** Operate SLURM specifically for large training jobs and Kubernetes for
everything else, accepting the cost of two systems as the price of giving each
workload the scheduler it fits best.

**Cost:** Doubles the operational surface area — two systems to patch, monitor, and
staff on-call for, and a real integration cost connecting the two (data and artifacts
have to flow between the SLURM-scheduled training side and the Kubernetes-scheduled
serving side).

**How it backfires:** Without deliberate integration work, running both can produce
two disconnected islands rather than one coherent platform, reintroducing exactly the
governance and lineage gaps a unified platform is meant to avoid (see
[The Governed Pipeline as the Only Path to Production](../workflow-orchestration/the-governed-pipeline-as-the-only-path-to-production.md)).

### Kubernetes plus a gang-scheduling-aware queue (Kueue/Volcano)

**What it is:** Standardize on Kubernetes as the single operational substrate, adding
a purpose-built gang-scheduling and queuing layer to close the native gap for
large training jobs.

**Cost:** Adds a real, nontrivial piece of infrastructure to operate and keep updated,
and gang-scheduling behavior via an add-on may not be as battle-tested or as
feature-complete as SLURM's native, decades-refined implementation for the most
demanding HPC-style workloads.

**How it backfires:** For workloads at the very largest scale or with the most
demanding gang-scheduling requirements, an add-on layer can still show rough edges
SLURM's native implementation wouldn't — this mitigation closes most, not necessarily
all, of the gap.

## Interactions

- [Gang Scheduling vs. Bin-Packing](../../foundations/gang-scheduling-vs-bin-packing.md) —
  the foundational tension this pattern's choice is fundamentally about resolving at
  the platform level.
- [The Managed vs. Build Tradeoff](../../foundations/the-managed-vs-build-tradeoff.md) —
  both SLURM and Kubernetes sit on the "build" side of that broader axis relative to
  a fully managed training service.
- [Gang Scheduling for Distributed Jobs](../gpu-scheduling/gang-scheduling-for-distributed-jobs.md) —
  the specific scheduling capability this page's Kubernetes option requires an
  add-on to provide natively.

## References

- SLURM Documentation. *Slurm Workload Manager Overview*. Describes SLURM's job model
  and native gang-scheduling design, rooted in HPC batch scheduling.
- Kubernetes SIG Scheduling. *Kueue Documentation*. Describes the design motivation
  for adding gang-scheduling and job-queueing semantics to Kubernetes.
- Volcano Project Documentation. *Volcano: A Kubernetes Native Batch Scheduling
  System*. Describes an alternative gang-scheduling extension for Kubernetes,
  independently arrived at.
