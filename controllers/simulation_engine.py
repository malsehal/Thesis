"""
SimulationEngine: runs the discrete‐time simulation.
For automated licensing, it processes requests at fixed intervals (every minute for short-term or daily for mid-term).
For manual licensing, it processes requests only at daily intervals.
"""
from config.parameters import POISSON_ARRIVAL_LAMBDA, SIMULATION_STEPS, SHORT_TERM_DURATION, MID_TERM_DURATION, LONG_TERM_DURATION, MANUAL_PROCESSING_INTERVAL
from models.request import SpectrumRequest
from utils.random_utils import sample_poisson, random_request_parameters
from strategies.interference_mitigation import apply_interference_mitigation

class SimulationEngine:
    def __init__(self, environment, coordinator, arch_policy):
        self.env = environment
        self.coordinator = coordinator
        self.arch_policy = arch_policy
        self.current_time = 0
        self.global_req_id = 0
        self.all_requests = []

    def run(self, sim_logger=None):
        # Determine processing interval based on licensing mode and grant duration.
        if self.arch_policy.licensing_mode == "Manual":
            processing_interval = MANUAL_PROCESSING_INTERVAL  # Process requests daily.
        else:
            if self.arch_policy.grant_duration == "ShortTerm":
                processing_interval = 1  # Every minute.
            elif self.arch_policy.grant_duration == "MidTerm":
                processing_interval = MID_TERM_DURATION  # Every day.
            else:
                processing_interval = SIMULATION_STEPS  # Permanent.
        for t in range(SIMULATION_STEPS):
            self.current_time = t
            # Always remove expired assignments.
            self.env.remove_expired_assignments(t)
            # Generate new requests regardless, but only process them at the designated interval.
            new_reqs = self.generate_requests(t)
            for req in new_reqs:
                self.all_requests.append(req)
            # For automated licensing, process every minute or day.
            if self.arch_policy.licensing_mode == "Automated":
                # Process if t is an interval boundary.
                if t % processing_interval == 0:
                    assigned_list, rejected_list = self.coordinator.assign_requests(new_reqs, self.env, t, self.arch_policy)
            else:  # Manual licensing: batch process daily.
                if t % processing_interval == 0:
                    # Process all pending requests whose delay has elapsed.
                    pending_reqs = [r for r in self.all_requests if not r.is_assigned and r.arrival_time <= t]
                    assigned_list, rejected_list = self.coordinator.assign_requests(pending_reqs, self.env, t, self.arch_policy)
            # Apply interference mitigation after assignments.
            apply_interference_mitigation(self.env, self.arch_policy, t)
            if sim_logger:
                sim_logger.log_event(f"=== Time step {t} ===")
                for a in self.get_all_assignments():
                    sim_logger.log_event(f"Assigned: {a}")
                for r in new_reqs:
                    if not r.is_assigned:
                        sim_logger.log_event(f"Rejected request: {r}")
        # End-of-simulation processing if needed.

    def generate_requests(self, t):
        count = sample_poisson(POISSON_ARRIVAL_LAMBDA)
        reqs = []
        for i in range(count):
            node_id, bw, dur, device_type = random_request_parameters()
            req = SpectrumRequest(self.global_req_id, t, node_id, bw, dur, device_type)
            req.add_trace(f"Arrived at time {t}: node={node_id}, requested_bw={bw}, duration={dur}, device_type={device_type}")
            self.global_req_id += 1
            reqs.append(req)
        return reqs

    def get_all_assignments(self):
        assignments = []
        for node in self.env.nodes:
            assignments.extend(node.active_assignments)
        return assignments