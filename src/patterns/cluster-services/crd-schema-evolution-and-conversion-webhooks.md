# CRD Schema Evolution & Conversion Webhooks

> **One-liner:** Evolving a custom resource's schema without a correct conversion webhook breaks every client still reading the old version, often invisibly until it doesn't.

## Symptom

- A client (a controller, a CLI tool, a script) reading a custom resource via an older
  API version starts receiving unexpected null or missing fields after a schema
  change, even though the resource's data hasn't actually been lost.
- Upgrading a CRD to add a new required field, or to restructure existing fields,
  breaks existing stored objects that were created under the old schema and haven't
  been touched since.
- A conversion webhook that correctly converts in one direction (old-to-new) but not
  the reverse (new-to-old) causes silent data loss or corruption for clients still
  reading the older version.
- Rolling out a new CRD version across a cluster with many existing custom resource
  instances requires understanding how each existing instance will be interpreted
  under the new schema, and this understanding wasn't validated before the rollout.

## Mechanism

Kubernetes custom resources support multiple API versions simultaneously, letting
different clients read and write a resource type using whichever version they were
built against — this is what allows a schema to evolve without breaking every client
simultaneously, on the assumption that clients migrate to newer versions on their own
timeline rather than all at once. Making this actually work requires a **conversion
webhook**: a service that translates a custom resource's stored representation
between its different declared API versions on the fly, so a client requesting
version v1 of a resource that's actually stored (or was last written) as v2 gets a
correctly-converted v1 representation, and vice versa.

The correctness burden this places on the conversion webhook is substantial and easy
to underestimate: it has to correctly represent every field's semantics across
every declared version, in both directions, including cases where a newer version
adds fields with no v1 equivalent (what should a v1 client see for a field that
didn't exist in v1?), removes or renames fields (how does a v2-only field map back to
whatever v1 called it, if anything?), or restructures data in a way that doesn't have
a lossless round-trip (a field split into two, or two fields merged into one). A
conversion webhook that handles the common, expected cases correctly but has a gap
for some less-obvious field combination or edge case produces silent, partial data
loss or corruption for exactly the clients hitting that gap — and because most
requests likely don't hit the gap, the bug can go undetected for a long time, showing
up only when a client happens to exercise the specific problematic combination.

This is compounded by existing stored objects: a schema evolution doesn't retroactively
rewrite every already-stored instance of a custom resource — objects created under an
older schema version remain stored in whatever form they were written, and the
conversion webhook has to correctly interpret and convert *that* stored form on every
read, not just handle freshly-created objects under the new schema. A conversion
webhook validated only against newly-created test objects, never against the actual
distribution of already-existing production objects (which may include edge cases
from earlier, less-constrained schema versions), can pass all its tests while still
failing on real production data.

## Real-world sightings

Kubernetes' own documentation on Custom Resource Definition versioning explicitly
describes the conversion webhook requirement and its correctness obligations across
all declared versions, and explicitly warns that conversion must be correct in both
directions and must handle all previously-stored object shapes, not just newly
created ones — a direct acknowledgment, in first-party documentation, of exactly the
failure mode described above.

The kubebuilder book's coverage of multi-version CRDs and conversion webhooks devotes
significant attention to round-trip correctness testing specifically, recommending
explicit round-trip tests (convert v1 to v2 and back, verify no data loss) as a
standard practice — guidance that exists precisely because this is a commonly
under-tested area in real operator implementations.

## Mitigations

### Explicit round-trip conversion testing

**What it is:** Test that converting a resource from version A to version B and back
to version A produces an equivalent result, for a representative range of field value
combinations, not just the common or expected cases.

**Cost:** Requires constructing and maintaining a representative test suite covering
edge cases (empty fields, boundary values, fields introduced in later versions),
which is more testing investment than validating only the "happy path."

**How it backfires:** Round-trip tests built only against synthetically-constructed
test objects, rather than sampled from actual production object distributions, can
still miss real edge cases that exist in production data but weren't anticipated by
whoever wrote the test cases.

### Testing conversion against actual stored production object shapes

**What it is:** Before rolling out a schema evolution, sample actual existing custom
resource instances from production and validate the conversion webhook against their
real, as-stored shapes, not just newly-constructed test objects.

**Cost:** Requires access to representative production data (or a realistic staging
environment with comparable object diversity) and a process for incorporating this
validation into the rollout process.

**How it backfires:** Sampled validation only catches issues present in the sampled
objects — a rare but real object shape that wasn't included in the sample can still
slip through undetected.

### Treating conversion webhook changes as high-risk, gated rollouts

**What it is:** Apply extra scrutiny, staged rollout, and rollback readiness
specifically to conversion webhook changes, recognizing that a bug here affects every
client reading the resource type, not just the specific feature the schema change was
meant to support.

**Cost:** Adds process overhead (additional review, staged rollout, monitoring)
compared to treating a schema change like any other code change.

**How it backfires:** None specific to applying appropriate caution — the risk this
mitigation addresses is precisely the opposite: treating a conversion webhook change
as routine when its actual blast radius (every client of the resource type) warrants
more caution than that.

## Interactions

- [Owner References & Garbage Collection](owner-references-and-garbage-collection.md) —
  a related metadata-correctness concern where subtle misconfiguration produces
  similarly silent, hard-to-diagnose failures.
- [Operator Reconciliation Idempotency](operator-reconciliation-idempotency.md) — a
  controller reading a mis-converted resource can make incorrect reconciliation
  decisions based on the corrupted view, compounding a conversion bug into an
  operational incident.
- [Dataset Versioning Without Copying Bytes](../training-data-platforms/dataset-versioning-without-copying-bytes.md) —
  a related but distinct schema-evolution concern for data rather than Kubernetes API
  objects, sharing the general principle that evolving a schema safely requires
  explicit compatibility handling, not just adding new fields and hoping.

## References

- Kubernetes Documentation. *Custom Resource Definition Versioning*. Describes
  conversion webhook requirements and correctness obligations across API versions.
- The Kubebuilder Book. *Multi-Version CRDs*. Discusses conversion webhook
  implementation and round-trip testing practices.
- Kubernetes Documentation. *API Versioning*. Discusses the broader Kubernetes API
  versioning and deprecation policy that CRD versioning follows the same principles
  as.
