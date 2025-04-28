"""
Spectrum Manager module for frequency assignments.
"""
from models.assignment import Assignment
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ
from collections import defaultdict
import random

class SpectrumManager:
    """
    Manages spectrum assignments based on requests and architectural policies.
    """
    def __init__(self, environment, architecture_policy, metrics_collector):
        """
        Initialize the Spectrum Manager.
        
        Args:
            environment: The simulation environment
            architecture_policy: The architectural policy to apply
            metrics_collector: Metrics collector instance
        """
        self.environment = environment
        self.arch_policy = architecture_policy
        self.metrics = metrics_collector
        # Use lists for assignment management
        self.active = []  # List of all active assignments
        self.square_to_assignments = defaultdict(list)  # Each square: list of assignments
        self.next_assignment_id = 0
        self.manual_queue = []  # Queue for manual licensing mode
        self.mitigated_conflicts = set()
        
        # Derive constants from architecture policy
        # Channel step based on frequency plan
        if self.arch_policy.freq_plan == "Large Blocks":
            self.channel_step_mhz = 200
        elif self.arch_policy.freq_plan == "Sub Channels":
            self.channel_step_mhz = 40
        else:  # "Freq Slicing"
            self.channel_step_mhz = 10
            
        # Query interval based on licensing mode
        if self.arch_policy.licensing_mode == "Manual":
            self.query_interval = float('inf')  # Permanent assignments
        elif self.arch_policy.licensing_mode == "Semi-Dynamic":
            self.query_interval = 1440  # Daily
        else:  # "Dynamic"
            self.query_interval = 1  # Every minute
            
        # Define coordination query costs based on topology
        if self.arch_policy.coordination_mode == "Centralized":
            self.initial_query_cost = 1.0
            self.renewal_query_cost = 0.5
        elif self.arch_policy.coordination_mode == "Decentralized":
            self.initial_query_cost = 0.5  # Distributed coordination costs less
            self.renewal_query_cost = 0.5
        else:  # "Hybrid"
            self.initial_query_cost = 0.75
            self.renewal_query_cost = 0.5
            
        # For Exclusive mode, define fixed band partitions
        self.band_partitions = {}
        if self.arch_policy.priority_mode == "Exclusive":
            total_band = TOTAL_BANDWIDTH_MHZ
            # Divide into three equal parts (each 200 MHz)
            self.band_partitions = {
                "5G": (FREQ_BASE_MHZ, FREQ_BASE_MHZ + total_band // 3),
                "IoT": (FREQ_BASE_MHZ + total_band // 3, FREQ_BASE_MHZ + 2 * (total_band // 3)),
                "Federal": (FREQ_BASE_MHZ + 2 * (total_band // 3), FREQ_BASE_MHZ + total_band)
            }
    
    def _add_assignment(self, assignment):
        self.active.append(assignment)
        node = self.environment.nodes[assignment.node_id]
        for square in node.covered_squares:
            self.square_to_assignments[square].append(assignment)

    def _remove_assignment(self, assignment):
        if assignment in self.active:
            self.active.remove(assignment)
        node = self.environment.nodes[assignment.node_id]
        for square in node.covered_squares:
            if assignment in self.square_to_assignments[square]:
                self.square_to_assignments[square].remove(assignment)
        
    def process_arrivals(self, requests, current_tick):
        """
        Process incoming spectrum requests with coordination mode logic.
        
        Args:
            requests: List of SpectrumRequest objects
            current_tick: Current simulation tick
        """
        mode = self.arch_policy.coordination_mode
        for request in requests:
            request.add_trace(f"Arrived at time {request.arrival_time}: node={request.node_id}, requested_bw={request.requested_bw} MHz, device_type={request.device_type}")
            candidates = self._generate_frequency_candidates(request)
            assignment_made = False
            # Hybrid: randomly choose centralized or decentralized for each request
            if mode == "Hybrid":
                use_centralized = random.random() < 0.5
            else:
                use_centralized = (mode == "Centralized")
            for freq_start, freq_end in candidates:
                # --- ENFORCE EXCLUSIVE MODE PARTITIONING ---
                if self.arch_policy.priority_mode == "Exclusive":
                    part = self.band_partitions.get(request.device_type)
                    if part is not None:
                        if not (part[0] <= freq_start and freq_end <= part[1]):
                            continue  # Skip candidates outside partition
                temp_assignment = Assignment(
                    assignment_id=self.next_assignment_id,
                    node_id=request.node_id,
                    freq_start=freq_start,
                    freq_end=freq_end,
                    device_type=request.device_type,
                    priority_tier=self._get_priority_tier(request.device_type)
                )
                node = self.environment.nodes[temp_assignment.node_id]
                possible_conflicts = []
                if use_centralized:
                    # Global: check all covered squares for all nodes
                    if isinstance(self.environment.nodes, dict):
                        nodes_iter = self.environment.nodes.values()
                    else:
                        nodes_iter = self.environment.nodes
                    for n in nodes_iter:
                        for square in n.covered_squares:
                            possible_conflicts.extend(self.square_to_assignments[square])
                else:
                    # Decentralized: check only assignments made by self and direct neighbors (not all assignments in shared squares)
                    neighbor_ids = set([request.node_id])
                    if hasattr(self.environment, 'get_neighbors'):
                        neighbor_ids.update(self.environment.get_neighbors(request.node_id))
                    possible_conflicts = []
                    seen_assignments = set()
                    for n_id in neighbor_ids:
                        n = self.environment.nodes[n_id]
                        for square in n.covered_squares:
                            # Only include assignments that were made by this neighbor (not all assignments in the square)
                            for assignment in self.square_to_assignments[square]:
                                if assignment.node_id == n_id and id(assignment) not in seen_assignments:
                                    possible_conflicts.append(assignment)
                                    seen_assignments.add(id(assignment))
                # Deduplicate by id to avoid redundant checks
                seen = set()
                conflict = False
                preempted_assignment = None
                for assignment in possible_conflicts:
                    if id(assignment) in seen:
                        continue
                    seen.add(id(assignment))
                    if temp_assignment.conflicts_with(assignment, self.environment):
                        # --- HIERARCHICAL PRIORITY ENFORCEMENT ---
                        if self.arch_policy.priority_mode == "Hierarchical":
                            temp_priority = temp_assignment.priority_tier
                            other_priority = assignment.priority_tier
                            if temp_priority < other_priority:
                                # Preempt the lower-priority assignment
                                self._remove_assignment(assignment)  # Remove immediately
                                request.add_trace(f"Preempted assignment {assignment.assignment_id} (node={assignment.node_id}, freq={assignment.freq_start}-{assignment.freq_end}) due to higher priority.")
                                # After preemption, double-check for new conflicts with remaining assignments
                                # Rebuild possible_conflicts without the preempted assignment
                                possible_conflicts_updated = [a for a in possible_conflicts if a != assignment]
                                # Re-check for conflicts
                                still_conflict = False
                                for other in possible_conflicts_updated:
                                    if temp_assignment.conflicts_with(other, self.environment):
                                        still_conflict = True
                                        conflict = True
                                        request.add_trace(f"Conflict remains after preemption with assignment {other.assignment_id} (node={other.node_id}, freq={other.freq_start}-{other.freq_end}).")
                                        break
                                if still_conflict:
                                    break  # Cannot assign due to remaining conflict
                                else:
                                    continue  # No more conflicts, continue to assignment
                            elif temp_priority > other_priority:
                                conflict = True
                                request.add_trace(f"Conflict with higher-priority assignment {assignment.assignment_id} (node={assignment.node_id}, freq={assignment.freq_start}-{assignment.freq_end}) not mitigated.")
                                break
                            # If equal priority, fall through to mitigation
                        mitigation_attempted = False
                        if self.arch_policy.interference_mitigation != "No Mitigation":
                            mitigation_attempted = temp_assignment.apply_mitigation(assignment, self.arch_policy, self.environment)
                        if mitigation_attempted:
                            self.mitigated_conflicts.add(tuple(sorted((temp_assignment.assignment_id, assignment.assignment_id))))
                            request.add_trace(f"Conflict with assignment {assignment.assignment_id} mitigated.")
                        else:
                            # If mitigation is not attempted or fails, resolve by priority (for non-hierarchical modes, treat as equal priority)
                            temp_priority = temp_assignment.priority_tier
                            other_priority = assignment.priority_tier
                            if temp_priority < other_priority:
                                self._remove_assignment(assignment)
                                request.add_trace(f"Preempted assignment {assignment.assignment_id} (node={assignment.node_id}, freq={assignment.freq_start}-{assignment.freq_end}) due to higher priority.")
                                possible_conflicts_updated = [a for a in possible_conflicts if a != assignment]
                                still_conflict = False
                                for other in possible_conflicts_updated:
                                    if temp_assignment.conflicts_with(other, self.environment):
                                        still_conflict = True
                                        conflict = True
                                        request.add_trace(f"Conflict remains after preemption with assignment {other.assignment_id} (node={other.node_id}, freq={other.freq_start}-{other.freq_end}).")
                                        break
                                if still_conflict:
                                    break
                                else:
                                    continue
                            elif temp_priority > other_priority:
                                conflict = True
                                request.add_trace(f"Conflict with higher-priority assignment {assignment.assignment_id} (node={assignment.node_id}, freq={assignment.freq_start}-{assignment.freq_end}) not mitigated.")
                                break
                            else:
                                conflict = True
                                request.add_trace(f"Conflict with assignment {assignment.assignment_id} (node={assignment.node_id}, freq={assignment.freq_start}-{assignment.freq_end}) not mitigated.")
                                break
                if not conflict:
                    if preempted_assignment is not None:
                        self._remove_assignment(preempted_assignment)
                    if self.query_interval != float('inf'):
                        temp_assignment = Assignment(
                            assignment_id=self.next_assignment_id,
                            node_id=request.node_id,
                            freq_start=freq_start,
                            freq_end=freq_end,
                            device_type=request.device_type,
                            priority_tier=self._get_priority_tier(request.device_type),
                            next_check_tick=current_tick + self.query_interval
                        )
                    self._add_assignment(temp_assignment)
                    self.next_assignment_id += 1
                    assignment_made = True
                    self.metrics.requests_total += 1
                    self.metrics.coord_queries += self.initial_query_cost
                    self.metrics.add_quality_measurement(temp_assignment.quality)
                    request.is_assigned = True
                    request.reject_reason = None
                    request.add_trace(f"Granted at time {current_tick}: freq=({freq_start}-{freq_end})")
                    request.assigned_freq = (freq_start, freq_end)
                    break
            if not assignment_made:
                self.metrics.requests_total += 1
                self.metrics.requests_denied += 1
                request.is_assigned = False
                request.reject_reason = "conflict or no candidates"
                request.add_trace(f"Denied at time {current_tick}: conflict or no candidates")
    
    def renew_assignments(self, current_tick):
        """
        Renew assignments that are due for review.
        For Dynamic mode: count query cost for ALL active assignments every tick, but only reprocess those due for review.
        Args:
            current_tick: Current simulation tick
        """
        assignments_to_remove = []
        is_dynamic = self.arch_policy.licensing_mode == "Dynamic"
        if is_dynamic:
            for assignment in self.active:
                self.metrics.coord_queries += self.renewal_query_cost
        for assignment in list(self.active):  # list() so we can safely remove
            if assignment.next_check_tick is None or assignment.next_check_tick != current_tick:
                continue
            node = self.environment.nodes[assignment.node_id]
            possible_conflicts = []
            for square in node.covered_squares:
                possible_conflicts.extend(self.square_to_assignments[square])
            # Remove self and deduplicate by id
            seen = set()
            conflict = False
            for other in possible_conflicts:
                if other is assignment or id(other) in seen:
                    continue
                seen.add(id(other))
                if assignment.conflicts_with(other, self.environment):
                    if not assignment.apply_mitigation(other, self.arch_policy, self.environment):
                        conflict = True
                        break
            if not conflict:
                # Update assignment in place (preserving quality and history)
                assignment.next_check_tick = current_tick + self.query_interval
                # Optionally, keep a history/log if desired (e.g., assignment.history.append(...))
                if not is_dynamic:
                    self.metrics.coord_queries += self.renewal_query_cost
            else:
                if conflict:
                    assignments_to_remove.append(assignment)
                    self.metrics.requests_denied += 1
        # Remove revoked assignments
        for assignment in assignments_to_remove:
            self._remove_assignment(assignment)
        # No need to replace renewed assignments, as we update in place

    def tick_housekeeping(self, current_tick):
        """
        Perform regular housekeeping tasks each tick.
        
        Args:
            current_tick: Current simulation tick
        """
        # Renew assignments if needed
        self.renew_assignments(current_tick)
        
        # Process manual batch if it's time (daily)
        if self.arch_policy.licensing_mode == "Manual" and current_tick % 1440 == 0:
            self._process_manual_batch(current_tick)
        
        # Update usage metrics
        self.metrics.update_usage(self.active, self.environment, 1)
    
    def _process_manual_batch(self, current_tick):
        """
        Process a batch of manual licensing requests.
        
        Args:
            current_tick: Current simulation tick
        """
        if not self.manual_queue:
            return
            
        # Process all queued requests
        self.process_arrivals(self.manual_queue, current_tick)
        
        # Add human reviewer time to metrics (from config)
        # Updated: Human coordination time is now based on waiting time per request and coordination mode
        centralized_wait = 43200  # 30 days in minutes
        hybrid_wait = 28800      # 20 days in minutes
        decentralized_wait = 14400  # 10 days in minutes
        mode = self.arch_policy.coordination_mode
        if mode == "Centralized":
            per_request_wait = centralized_wait
        elif mode == "Hybrid":
            per_request_wait = hybrid_wait
        elif mode == "Decentralized":
            per_request_wait = decentralized_wait
        else:
            per_request_wait = centralized_wait  # fallback
        self.metrics.human_minutes += len(self.manual_queue) * per_request_wait
        
        # Clear the queue
        self.manual_queue = []
    
    def _generate_frequency_candidates(self, request):
        """
        Generate candidate frequencies for a request based on the frequency plan.
        Args:
            request: A SpectrumRequest object
        Returns:
            List of (freq_start, freq_end) tuples
        """
        candidates = []
        requested_bw = request.requested_bw
        # Large Blocks: Always allocate 200 MHz blocks, regardless of requested_bw
        if self.arch_policy.freq_plan == "Large Blocks":
            block_size = 200
            # Only assign if the whole block is available
            if self.arch_policy.priority_mode == "Exclusive":
                part = self.band_partitions.get(request.device_type)
                if part is not None:
                    start_freq = part[0]
                    while start_freq + block_size <= part[1]:
                        candidates.append((start_freq, start_freq + block_size))
                        start_freq += block_size
            else:
                start_freq = FREQ_BASE_MHZ
                while start_freq + block_size <= FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ:
                    candidates.append((start_freq, start_freq + block_size))
                    start_freq += block_size
        # Sub Channels: Use 40 MHz channels, must find enough contiguous channels
        elif self.arch_policy.freq_plan == "Sub Channels":
            channel_size = 40
            num_channels = (requested_bw + channel_size - 1) // channel_size  # ceil division
            total_channels = TOTAL_BANDWIDTH_MHZ // channel_size
            if self.arch_policy.priority_mode == "Exclusive":
                part = self.band_partitions.get(request.device_type)
                if part is not None:
                    part_bw = part[1] - part[0]
                    part_channels = part_bw // channel_size
                    for start_ch in range(part_channels - num_channels + 1):
                        freq_start = part[0] + start_ch * channel_size
                        freq_end = freq_start + num_channels * channel_size
                        if freq_end <= part[1]:
                            candidates.append((freq_start, freq_end))
            else:
                for start_ch in range(total_channels - num_channels + 1):
                    freq_start = FREQ_BASE_MHZ + start_ch * channel_size
                    freq_end = freq_start + num_channels * channel_size
                    if freq_end <= FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ:
                        candidates.append((freq_start, freq_end))
        # Freq Slicing: Allocate exactly requested_bw anywhere in the band
        else:  # "Freq Slicing"
            if self.arch_policy.priority_mode == "Exclusive":
                part = self.band_partitions.get(request.device_type)
                if part is not None:
                    for freq_start in range(part[0], part[1] - requested_bw + 1):
                        freq_end = freq_start + requested_bw
                        candidates.append((freq_start, freq_end))
            else:
                for freq_start in range(FREQ_BASE_MHZ, FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ - requested_bw + 1):
                    freq_end = freq_start + requested_bw
                    candidates.append((freq_start, freq_end))
        random.shuffle(candidates)
        return candidates
    
    def _get_priority_tier(self, device_type):
        """
        Get priority tier for a device type.
        
        Args:
            device_type: Device type string
            
        Returns:
            Priority tier (0 = highest)
        """
        if self.arch_policy.priority_mode == "Hierarchical":
            # Federal has highest priority (0), then 5G (1), then IoT (2)
            if device_type == "Federal":
                return 0
            elif device_type == "5G":
                return 1
            else:  # IoT
                return 2
        else:
            # In Co-Primary or Exclusive, all have same tier
            return 0
