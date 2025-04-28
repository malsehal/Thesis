"""
Defines priority strategies.
In CoPrimary, no request preempts another.
In Hierarchical, 5G has higher priority than IoT.
"""
class CoPrimaryPriority:
    def decide_preemption(self, existing_assignment, new_request):
        return False

class HierarchicalPriority:
    def decide_preemption(self, existing_assignment, new_request):
        if existing_assignment.device_type == "IoT" and new_request.device_type == "5G":
            return True
        return False