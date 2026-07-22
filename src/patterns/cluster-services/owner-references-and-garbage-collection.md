# Owner References & Garbage Collection

> **One-liner:** Kubernetes garbage collection depends entirely on owner references being set correctly; a missing or incorrect one leaks resources silently or deletes something still in use.

## Symptom

- Deleting a higher-level resource (a custom resource, a deployment) leaves behind
  child resources it should have cleaned up, which accumulate silently over time and
  are only noticed when someone happens to audit for orphaned resources.
- A resource is unexpectedly deleted as a side effect of deleting something else,
  because it was incorrectly given an owner reference to a resource it wasn't
  actually logically dependent on.
- An operator that creates and manages child resources (ConfigMaps, Secrets, other
  custom resources) shows a slow, steady accumulation of orphaned objects across the
  cluster, degrading etcd object-count-related scaling headroom over time (see
  [Scaling Limits: Nodes vs. Objects vs. Watches](../control-plane-at-scale/scaling-limits-nodes-objects-watches.md)).
- A resource shared, intentionally, between two different logical owners is deleted
  when only one of the two owners is deleted, because it was only ever given a single
  owner reference rather than reflecting its actual shared ownership.

## Mechanism

Kubernetes' built-in garbage collection deletes a resource automatically once all of
its owners (as declared via `ownerReferences` in its metadata) have themselves been
deleted — this is the mechanism that makes cascading deletion work (deleting a
Deployment cleans up its ReplicaSets and Pods) without every controller needing to
implement its own explicit cleanup logic. This is a genuinely valuable, widely relied
upon convenience, but it depends entirely on owner references being set correctly at
creation time — garbage collection has no independent understanding of "logical"
ownership beyond what's explicitly declared in this metadata field.

This creates two symmetric failure modes, both equally real. **Missing or incorrect
owner references** (a controller creates a child resource but forgets to set the
owner reference, or sets it incorrectly) mean garbage collection never triggers for
that resource — deleting the parent leaves the child behind indefinitely, an orphan
that accumulates unnoticed unless something explicitly audits for it. **Incorrect
owner references pointing at the wrong or an overly broad owner** produce the opposite
problem: a resource gets deleted when its stated owner is deleted, even though the
resource's actual logical lifecycle wasn't really tied to that owner — an unintended,
premature deletion.

Shared ownership — a resource that's logically owned by more than one parent, and
should only be garbage-collected once *all* of them are gone — requires setting
multiple owner references on the resource, which Kubernetes supports but which
operator implementations sometimes overlook, defaulting to a single owner reference
even when the actual ownership relationship is genuinely shared. This produces the
premature-deletion failure mode specifically for resources with legitimately shared
ownership.

Because garbage collection happens asynchronously, in the background, based purely on
this metadata, its behavior is often invisible until something goes wrong — there's no
immediate, visible signal when an owner reference is missing (the resource simply
never gets cleaned up, silently, until someone notices the accumulation) or
incorrect (the resource gets deleted at an unexpected moment, which can be hard to
trace back to the owner-reference configuration that caused it).

## Real-world sightings

Kubernetes' own documentation on owner references and garbage collection explicitly
describes both cascading deletion semantics (foreground vs. background cascading
deletion, with different ordering and blocking guarantees) and the requirement that
owner references be set correctly for the mechanism to function as intended —
explicitly noting that Kubernetes itself does not validate that an owner reference
reflects a "correct" or intended ownership relationship, only that it's a
syntactically valid reference.

The kubebuilder book's guidance on building operators explicitly discusses setting
owner references on created child resources as a standard, expected part of operator
implementation, and cross-references it directly with reconciliation idempotency (see
[Operator Reconciliation Idempotency](operator-reconciliation-idempotency.md)) since
correctly-set owner references are part of what prevents a naive, non-idempotent
reconciliation from creating duplicate child resources on replay.

## Mitigations

### Consistently setting owner references on every created child resource

**What it is:** Ensure every controller-created child resource has correctly-set
owner references pointing to its actual logical owner(s), as a standard, enforced
part of the controller's creation logic.

**Cost:** Requires discipline across every code path that creates resources, and
becomes harder to enforce consistently as more controllers and more resource types
are added to a cluster over time.

**How it backfires:** None specific to doing this correctly — the risk is entirely
in inconsistent application, which is why this needs to be systematically checked
(e.g., via linting or admission policy) rather than relying purely on developer
discipline.

### Periodic auditing for orphaned resources

**What it is:** Run periodic audits identifying resources with no owner references
(or owner references pointing to non-existent owners) that appear to logically belong
to some controller's managed resource set, surfacing missed cleanup before it
accumulates into a meaningful object-count problem.

**Cost:** Requires building or adopting audit tooling capable of distinguishing
"intentionally standalone resource" from "should have had an owner reference but
doesn't," which isn't always a clear-cut distinction from the resource's metadata
alone.

**How it backfires:** An audit that's run infrequently allows orphan accumulation to
continue unchecked between audit runs, and a false-positive-prone audit (flagging
intentionally standalone resources as orphans) trains operators to ignore its output.

### Correctly modeling shared ownership with multiple owner references

**What it is:** For resources with genuinely shared logical ownership across multiple
parents, set multiple owner references rather than defaulting to a single one,
ensuring garbage collection only triggers once every actual owner is gone.

**Cost:** Requires the controller logic to correctly track and update the full set of
current owners as ownership relationships change over the resource's lifetime, not
just at creation time.

**How it backfires:** A stale owner reference (pointing to an owner that logically no
longer applies but wasn't removed from the list) can prevent legitimate garbage
collection indefinitely, producing exactly the orphan-accumulation problem this
mitigation was meant to avoid, just through a different mechanism.

## Interactions

- [Operator Reconciliation Idempotency](operator-reconciliation-idempotency.md) —
  correctly-set owner references are part of what prevents duplicate resource
  creation on reconciliation replay.
- [Scaling Limits: Nodes vs. Objects vs. Watches](../control-plane-at-scale/scaling-limits-nodes-objects-watches.md) —
  orphaned resource accumulation directly degrades object-count scaling headroom over
  time.
- [CRD Schema Evolution & Conversion Webhooks](crd-schema-evolution-and-conversion-webhooks.md) —
  a related metadata-correctness concern, where a different kind of subtle
  misconfiguration (schema mismatch rather than ownership mismatch) produces
  similarly hard-to-diagnose failures.

## References

- Kubernetes Documentation. *Garbage Collection*. Describes owner reference
  semantics and foreground/background cascading deletion behavior.
- The Kubebuilder Book. *Owner References*. Describes practical owner-reference
  management for custom operators.
- Kubernetes Documentation. *Object Management*. Discusses metadata-driven resource
  lifecycle management including owner references.
