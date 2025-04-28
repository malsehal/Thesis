"""
Defines the MetricsCollector class for tracking spectrum utilization and management metrics.
"""

class MetricsCollector:
    """
    Collects and calculates metrics for spectrum management simulation.
    """
    def __init__(self):
        # Initialize counters
        self.mhz_km2_min_granted = 0.0  # Traditional spectrum use metric (kept for backward compatibility)
        self.coord_queries = 0.0        # Coordination queries count
        self.human_minutes = 0.0        # Human reviewer time
        self.requests_total = 0         # Total number of requests processed
        self.requests_denied = 0        # Number of denied requests
        self.quality_sum = 0.0          # Sum of quality values
        self.quality_count = 0          # Count of quality measurements
        
        # For correct SUE calculation
        self.daily_user_counts = {}     # Dictionary to track max users per day {day: max_count}
        self.active_day_sum = 0         # Sum of active users per day
        self.avg_quality_sum = 0.0      # Sum of average quality values
        self.avg_quality_count = 0      # Count of average quality measurements
        self.total_mhz_min_km2 = 0.0    # Total MHz·km²·minutes
        self.coordination_cost = 0.0    # Total coordination cost (for dynamic/semi-dynamic renewals)
    
    def update_usage(self, active_assignments, environment, tick_minutes=1):
        """
        Update spectrum usage metrics based on active assignments.
        
        Args:
            active_assignments: List of active Assignment objects
            environment: The Environment instance containing nodes
            tick_minutes: Number of minutes in this tick (default=1)
        """
        # Update traditional metric (kept for backward compatibility)
        for assignment in active_assignments:
            # Calculate bandwidth of assignment
            bandwidth = assignment.freq_end - assignment.freq_start
            
            # Get node and its coverage area (number of squares)
            # This assumes each square is 1 km²
            node = environment.nodes[assignment.node_id]
            area_km2 = len(node.covered_squares)
            
            # Accumulate MHz·km²·minutes (with quality factor)
            self.mhz_km2_min_granted += bandwidth * area_km2 * tick_minutes * assignment.quality
            self.total_mhz_min_km2 += bandwidth * area_km2 * tick_minutes
        
        # Only update daily user counts if tick_minutes is a multiple of 1440 (i.e., at day boundaries)
        if tick_minutes % 1440 == 0:
            current_day = tick_minutes // 1440 - 1
            active_user_count = len(active_assignments)
            self.daily_user_counts[current_day] = max(
                self.daily_user_counts.get(current_day, 0), 
                active_user_count
            )
            self.active_day_sum += active_user_count
    
    def update_daily_users(self, day, active_assignments):
        """
        Update the daily user count for the given day.
        Args:
            day: int, the day index (0-based)
            active_assignments: list of active assignments at the end of the day
        """
        user_count = len(active_assignments)
        # print(f"[DEBUG] Day {day}: Active assignments at day end = {user_count}")
        self.daily_user_counts[day] = user_count
        self.active_day_sum += user_count
    
    def add_quality_measurement(self, quality):
        """
        Add a quality measurement to the metrics.
        
        Args:
            quality: The quality value to record
        """
        self.quality_sum += quality
        self.quality_count += 1
        self.avg_quality_sum += quality
        self.avg_quality_count += 1
    
    def compute_interference(self, assignments, environment, arch_policy=None, mitigated_conflicts=None):
        """
        Compute interference metrics for a list of assignments.
        Args:
            assignments: list of Assignment objects
            environment: Environment instance
            arch_policy: ArchitecturePolicy (for mitigation logic)
            mitigated_conflicts: set of mitigated conflicts (optional)
        Returns:
            (num_interfering, interference_rate)
        """
        # print("[DEBUG] mitigated_conflicts received in compute_interference:", mitigated_conflicts)
        if mitigated_conflicts is None:
            mitigated_conflicts = set()
        interfering = set()
        mode = getattr(arch_policy, 'coordination_mode', None)
        # print(f"[DEBUG] Post-processing interference check: coordination_mode={mode}")
        # print("[DEBUG] assignment IDs in compute_interference:", [getattr(a, 'assignment_id', None) for a in assignments])
        # print("[DEBUG] Covered squares for each node:")
        # for node in environment.nodes:
        #     print(f"Node {node.node_id} covers squares: {sorted(node.covered_squares)}")

        # print("[DEBUG] Final assignments (pre-interference check):")
        # for a in assignments:
        #     covered = sorted(environment.nodes[a.node_id].covered_squares)
        #     print(f"Assignment {a.assignment_id}: node={a.node_id}, freq=({a.freq_start}-{a.freq_end}), device={a.device_type}, covered_squares={covered}")
        # Extra: Check for true conflicts and print summary
        found_conflict = False
        for i, a1 in enumerate(assignments):
            for j in range(i+1, len(assignments)):
                a2 = assignments[j]
                same_freq = not (a1.freq_end <= a2.freq_start or a2.freq_end <= a1.freq_start)
                overlap_squares = environment.nodes[a1.node_id].covered_squares.intersection(environment.nodes[a2.node_id].covered_squares)
                if same_freq and overlap_squares:
                    pair = tuple(sorted((a1.assignment_id, a2.assignment_id)))
                    if pair in mitigated_conflicts:
                        continue  # This conflict was mitigated, skip
                    # print(f"[SUMMARY CONFLICT] Assignments {a1.assignment_id} and {a2.assignment_id} overlap in freq and squares: freq=({a1.freq_start}-{a1.freq_end}) & ({a2.freq_start}-{a2.freq_end}), squares={sorted(overlap_squares)}")
                    found_conflict = True
                    # Only count as interfering if not mitigated
                    interfering.add(a1.assignment_id)
                    interfering.add(a2.assignment_id)
        if not found_conflict:
            # print("[SUMMARY] No true freq+squares conflicts in final assignments.")
            pass

        # print("[DEBUG] Checking for assignment conflicts:")
        num_interfering = len(interfering)
        interference_rate = num_interfering / max(1, len(assignments))
        return num_interfering, interference_rate

    def apply_query_multipliers(self, coord_queries, arch_policy):
        """
        Apply post-processing multipliers to the coord_queries metric based on freq_plan, enforcement_mode, and priority_mode,
        but only for Dynamic and Semi-Dynamic licensing.
        """
        licensing_mode = getattr(arch_policy, 'licensing_mode', None)
        if licensing_mode not in ['Dynamic', 'Semi-Dynamic']:
            return coord_queries
        freq_mult = {
            'Large Blocks': 1,
            'Sub Channels': 1.5,
            'Freq Slicing': 2
        }.get(getattr(arch_policy, 'freq_plan', None), 1)
        enforcement_mult = 2 if getattr(arch_policy, 'enforcement_mode', None) == 'Active' else 1
        priority_mult = {
            'Exclusive': 1,
            'Hierarchical': 1.5,
            'Co-Primary': 2
        }.get(getattr(arch_policy, 'priority_mode', None), 1)
        return coord_queries * freq_mult * enforcement_mult * priority_mult

    def apply_human_minutes_multipliers(self, human_minutes, arch_policy):
        """
        Apply post-processing multipliers to the Human_Minutes metric based on freq_plan, enforcement_mode, and priority_mode,
        but only for Manual licensing.
        """
        if getattr(arch_policy, 'licensing_mode', None) != 'Manual':
            return human_minutes
        freq_mult = {
            'Large Blocks': 1,
            'Sub Channels': 1.5,
            'Freq Slicing': 2
        }.get(getattr(arch_policy, 'freq_plan', None), 1)
        enforcement_mult = 2 if getattr(arch_policy, 'enforcement_mode', None) == 'Active' else 1
        priority_mult = {
            'Exclusive': 1,
            'Hierarchical': 1.5,
            'Co-Primary': 2
        }.get(getattr(arch_policy, 'priority_mode', None), 1)
        return human_minutes * freq_mult * enforcement_mult * priority_mult

    def final_report(self, total_band_mhz, total_area_km2, sim_minutes, final_active_assignments, environment, arch_policy, mitigated_conflicts=None):
        """
        Generate a final report of all metrics.
        
        Args:
            total_band_mhz: Total bandwidth in MHz
            total_area_km2: Total area in km²
            sim_minutes: Total simulation minutes
            final_active_assignments: List of active assignments at end of simulation (for total_active_users)
            environment: Environment instance (needed for interference metric)
            arch_policy: ArchitecturePolicy (for mitigation logic)
            mitigated_conflicts: set of mitigated conflicts (optional)
        
        Returns:
            Dictionary of metrics
        """
        traditional_sue = self.mhz_km2_min_granted / max(1, total_band_mhz * total_area_km2 * sim_minutes)
        # Compute mean quality based on final active assignments, not just initial assignment time
        if final_active_assignments is not None and len(final_active_assignments) > 0:
            mean_quality = sum(a.quality for a in final_active_assignments) / max(1, len(final_active_assignments))
        else:
            mean_quality = self.quality_sum / max(1, self.quality_count)
        total_active_users = len(final_active_assignments) if final_active_assignments is not None else 0
        correct_sue = self.total_mhz_min_km2 / max(1, total_band_mhz * total_area_km2 * sim_minutes)
        num_interfering, interference_rate = self.compute_interference(
            final_active_assignments, environment, arch_policy, mitigated_conflicts=mitigated_conflicts)
        interference_metrics = {
            'Num_Interfering_Assignments': num_interfering,
            'Interference_Rate': interference_rate
        }
        # Apply the human minutes multiplier logic here
        base_human_minutes = self.human_minutes
        human_minutes = self.apply_human_minutes_multipliers(base_human_minutes, arch_policy)

        # Apply the query multipliers for dynamic/semi-dynamic
        base_coord_queries = self.coord_queries
        coord_queries = self.apply_query_multipliers(base_coord_queries, arch_policy)

        # Compute coordination cost using the normalized formula
        WH = 1      # human coordination weight
        WD = 1      # database queries weight
        RT = 1     # human reference time (minutes)
        RQ = 100   # database queries reference
        HCT = human_minutes
        DBQ = coord_queries
        coordination_cost = WH * (HCT / RT) + WD * (DBQ / RQ)

        blocking_prob = self.requests_denied / max(1, self.requests_total)
        return {
            'SUE': traditional_sue, 
            'Coordination_Cost': coordination_cost,
            'Human_Minutes': human_minutes,
            'Requests_Total': self.requests_total,
            'Requests_Denied': self.requests_denied,
            'Blocking_Prob': blocking_prob,
            'Mean_Quality': mean_quality,
            'Total_Active_Users': total_active_users,
            'Correct_SUE': correct_sue,
            **interference_metrics
        }
