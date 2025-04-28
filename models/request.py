# models/request.py
"""
Defines the SpectrumRequest class.
Each SpectrumRequest represents a demand for spectrum access,
with a desired node, requested bandwidth, and device type.
It also maintains a trace log of its lifecycle.
"""

class SpectrumRequest:
    def __init__(self, req_id, arrival_time, node_id, requested_bw, device_type):
        self.req_id = req_id                  # Unique request ID
        self.arrival_time = arrival_time      # Time (in minutes) when the request arrives
        self.node_id = node_id                # Desired node (an integer ID)
        self.requested_bw = requested_bw      # Desired bandwidth in MHz (20, 40, …, 200)
        self.device_type = device_type        # "5G" or "IoT"
        self.is_assigned = False              # Whether the request has been granted
        self.reject_reason = None             # If rejected, a message indicating why
        self.trace = []                       # records events for the request

    def add_trace(self, message):
        self.trace.append(message)

    def __repr__(self):
        return (f"<Request#{self.req_id} node={self.node_id} bw={self.requested_bw} "
                f"arr_t={self.arrival_time} device_type={self.device_type} "
                f"assigned={self.is_assigned}>")