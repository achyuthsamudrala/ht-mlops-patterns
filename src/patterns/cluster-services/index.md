# Cluster Services & Operators

These patterns address the operators, controllers, and cluster services every workload depends on invisibly — where correctness under replay, partial failure, and concurrent reconciliation is the whole job.

## Reading order

[Operator Reconciliation Idempotency](operator-reconciliation-idempotency.md) first — it's the property every other pattern in this family assumes.

## Patterns in this section

- [Operator Reconciliation Idempotency](operator-reconciliation-idempotency.md)
- [Service Discovery at Fleet Scale](service-discovery-at-fleet-scale.md)
- [Owner References & Garbage Collection](owner-references-and-garbage-collection.md)
- [CRD Schema Evolution & Conversion Webhooks](crd-schema-evolution-and-conversion-webhooks.md)
- [Graceful Degradation for Invisible Infrastructure](graceful-degradation-for-invisible-infrastructure.md)
