"""
HybridCoordinator:
Implements a hybrid approach:
First, use decentralized assignment per node, then apply a centralized conflict resolution.
"""
from controllers.coordinator_decentralized import DecentralizedCoordinator
from strategies.interference_mitigation import apply_interference_mitigation

class HybridCoordinator:
    def __init__(self, freq_allocator, licensing, priority, interference, arch_policy):
        # Use decentralized approach for initial assignments.
        self.decentralized = DecentralizedCoordinator(freq_allocator, licensing, priority, interference, arch_policy)
        self.arch_policy = arch_policy

    def assign_requests(self, requests, environment, current_time, arch_policy):
        assigned_list, rejected_list = self.decentralized.assign_requests(requests, environment, current_time, arch_policy)
        # Then, apply centralized interference mitigation to resolve conflicts across nodes.
        apply_interference_mitigation(environment, arch_policy, current_time)
        return assigned_list, rejected_list