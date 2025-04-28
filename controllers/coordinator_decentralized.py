"""
DecentralizedCoordinator:
Each node processes its own requests independently.
"""
from config.parameters import AUTOMATED_DELAY, MANUAL_MIN_DELAY, MANUAL_MAX_DELAY, SHORT_TERM_DURATION, MID_TERM_DURATION, LONG_TERM_DURATION
from models.assignment import SpectrumAssignment
import random

class DecentralizedCoordinator:
    def __init__(self, freq_allocator, licensing, priority, interference, arch_policy):
        self.freq_allocator = freq_allocator
        self.licensing = licensing
        self.priority = priority
        self.interference = interference
        self.arch_policy = arch_policy
        if arch_policy.grant_duration == "ShortTerm":
            self.grant_duration = SHORT_TERM_DURATION
        elif arch_policy.grant_duration == "MidTerm":
            self.grant_duration = MID_TERM_DURATION
        else:
            self.grant_duration = LONG_TERM_DURATION

    def assign_requests(self, requests, environment, current_time, arch_policy):
        assigned_list = []
        rejected_list = []
        node_requests = {}
        for req in requests:
            node_requests.setdefault(req.node_id, []).append(req)
        for node_id, reqs in node_requests.items():
            node = environment.nodes[node_id]
            for req in reqs:
                if arch_policy.licensing_mode == "Manual":
                    delay = random.randint(MANUAL_MIN_DELAY, MANUAL_MAX_DELAY)
                else:
                    delay = AUTOMATED_DELAY
                start_time = current_time + delay
                end_time = start_time + self.grant_duration
                freq_assignment = self.freq_allocator.find_allocation(node.active_assignments, req.requested_bw, arch_policy)
                if freq_assignment is None:
                    req.is_assigned = False
                    req.reject_reason = "No bandwidth"
                    req.add_trace(f"Rejected at time {current_time}: reason={req.reject_reason}")
                    rejected_list.append(req)
                else:
                    new_assignment = SpectrumAssignment(req.req_id, req.node_id, start_time, end_time, freq_assignment[0], freq_assignment[1], freq_assignment[1]-freq_assignment[0], req.device_type)
                    node.add_assignment(new_assignment)
                    req.is_assigned = True
                    req.assign_time = start_time
                    req.end_time = end_time
                    req.add_trace(f"Assigned at time {current_time}: start_time={start_time}, end_time={end_time}, freq=({freq_assignment[0]}-{freq_assignment[1]}), quality={new_assignment.quality}")
                    assigned_list.append(new_assignment)
        return assigned_list, rejected_list