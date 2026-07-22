# Kubernetes Control Plane at Scale

These patterns cover what breaks in the Kubernetes control plane once cluster size, object count, or watch volume crosses the thresholds where etcd and the apiserver stop being invisible infrastructure.

## Reading order

[etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md) first — most control-plane scaling incidents trace back to it eventually.

## Patterns in this section

- [etcd as the Hidden Bottleneck](etcd-as-the-hidden-bottleneck.md)
- [API Priority and Fairness](api-priority-and-fairness.md)
- [Controller Reconciliation Storms](controller-reconciliation-storms.md)
- [Scaling Limits: Nodes vs. Objects vs. Watches](scaling-limits-nodes-objects-watches.md)
- [Raft Consensus for Cluster State](raft-consensus-for-cluster-state.md)
