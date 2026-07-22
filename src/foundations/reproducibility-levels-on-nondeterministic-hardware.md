# Reproducibility Levels on Nondeterministic Hardware

> **"Reproducible" has to mean something achievable, or it becomes a promise nobody
> actually keeps.** Bit-exact reruns of a large training job are, in the general case,
> not achievable on real GPU hardware — and treating that as the reproducibility bar
> sets teams up to either give up on reproducibility entirely or quietly fake it.

## Why bit-exact reproduction usually isn't possible

Several independent sources of nondeterminism compound in a real distributed training
run: floating-point addition is not associative, so summing the same values in a
different order (which happens routinely — different reduction orders across GPU
kernels, different thread scheduling, different all-reduce implementations) produces
slightly different results. Many GPU kernels use nondeterministic algorithms by
default (some convolution and atomic-operation implementations trade determinism for
speed). Distributed collective communication order can vary run to run depending on
network timing. And hardware-level variation (different GPU models, driver versions,
firmware) can shift numerical results even with identical code.

Deterministic kernels and operations do exist for many of these cases, but they carry a
real performance cost — sometimes substantial — which is why they're opt-in rather
than default. Forcing full determinism, if it's even fully achievable for a given
model architecture and framework combination, usually means giving up meaningful
throughput to get it.

## The achievable target: statistical / pipeline reproducibility

Given this, the realistic reproducibility bar isn't "identical numbers," it's
"identical inputs and a controlled, understood process, producing results that are
consistent within expected numerical variance." This requires pinning everything
*except* the hardware-level nondeterminism that can't practically be eliminated:

- **Code**: the exact training script and library versions, typically via a container
  image built once and referenced by digest, not by a mutable tag.
- **Configuration**: every hyperparameter and setting, captured explicitly (not left as
  ambient defaults that can silently change between framework versions).
- **Data**: the exact dataset version the run consumed, not "the dataset as of
  whenever someone reads this" (see
  [Dataset Versioning Without Copying Bytes](../patterns/training-data-platforms/dataset-versioning-without-copying-bytes.md)).
- **Seed**: explicit seeding of every source of randomness the framework exposes,
  understanding that this bounds but doesn't eliminate variance from the
  nondeterminism sources above.

A run reproduced this way won't produce bit-identical loss curves, but it will produce
statistically consistent ones — the same qualitative behavior, within the numerical
noise floor that any GPU training run has regardless of how carefully it's controlled.
This is a genuinely useful and achievable guarantee; claiming more than this is the
actual failure mode.

## Why this distinction matters practically

Teams that don't explicitly adopt this framing tend to fall into one of two failure
modes. Some quietly assume bit-exact reproducibility is the standard, and then treat
any numerical discrepancy between "reproduced" runs as evidence something is broken —
chasing a phantom bug that's actually just floating-point non-associativity. Others,
having discovered bit-exact reproduction is infeasible, give up on reproducibility
work altogether, losing the very real and achievable benefits of pinned code, config,
data, and containers.

Naming the achievable target explicitly — pipeline/statistical reproducibility, not
bit-exact — avoids both failure modes: it sets an honest expectation for what
"reproduced" means, and it keeps the team focused on the parts of reproducibility that
are actually within their control.

## Where the deterministic-kernel tradeoff is worth paying

There are contexts where the performance cost of deterministic kernels is worth
paying anyway — debugging a suspected numerical bug, where eliminating one source of
variance narrows the search space; regulatory or safety-critical contexts requiring a
stronger reproducibility guarantee; or small-scale validation runs where the
performance cost is immaterial. The general training-at-scale case is not one of
these, which is why deterministic kernels remain opt-in rather than a universal
default.

## Connections to other foundations

[Failure as the Steady State at Fleet Scale](failure-as-the-steady-state.md) adds
another layer: a training run that recovers from a mid-run failure via checkpoint
restart is, by construction, not going to bit-reproduce a run that completed without
any failure — the recovered run's numerical trajectory diverges from the point of
restart onward, which is a further reason bit-exact reproduction isn't a meaningful
target for any sufficiently long, large-scale run.
