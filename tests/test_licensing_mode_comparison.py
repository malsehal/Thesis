"""
Test and compare different licensing modes.

This test:
1. Implements correct manual licensing with a 30-day processing delay
2. Calculates SUE based on average daily users rather than MHz·km²·min
3. Compares all three licensing modes over a 60-day simulation
"""
import sys
import os
import unittest
import matplotlib.pyplot as plt
import numpy as np
from copy import deepcopy

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.environment import Environment
from models.request import SpectrumRequest
from utils.demand_generator import generate_demand
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from core.simulation import Simulation
from morphology.architecture_enumerator import get_architecture_by_name

# Constants for the simulation
SIM_DAYS = 60  # Increased to 60 days to show manual licensing delay effects
MINUTES_PER_DAY = 1440
SIM_MINUTES = SIM_DAYS * MINUTES_PER_DAY
MANUAL_PROCESSING_DELAY_DAYS = 30  # 30-day delay for manual licensing processing


class SUETracker:
    """Helper class to track SUE based on average daily users."""
    
    def __init__(self, total_bandwidth, total_area, total_days):
        self.total_bandwidth = total_bandwidth  # MHz
        self.total_area = total_area  # km²
        self.total_days = total_days  # days
        self.daily_users = [0] * total_days  # Store user count for each day
        self.current_day = 0
    
    def update_daily_count(self, day, user_count):
        """Update the user count for a specific day."""
        if day < len(self.daily_users):
            self.daily_users[day] = max(self.daily_users[day], user_count)  # Take the max count for the day
    
    def calculate_sue(self):
        """Calculate SUE based on average daily users."""
        # Calculate average daily users
        avg_daily_users = sum(self.daily_users) / self.total_days if self.total_days > 0 else 0
        
        # Calculate SUE
        denominator = self.total_bandwidth * self.total_area * self.total_days
        sue = avg_daily_users / denominator if denominator > 0 else 0
        
        return sue, avg_daily_users


class TestLicensingModeComparison(unittest.TestCase):
    """Test suite for comparing different licensing modes."""
    
    def setUp(self):
        """Set up the test environment with a 2x2 grid."""
        self.env = Environment(squares_rows=2, squares_cols=2)
        
        # Generate medium demand scenario
        self.demand = generate_demand("medium", self.env, sim_minutes=SIM_MINUTES)
        
        # Print information about the generated requests
        print("\nGenerated Requests:")
        print("-------------------")
        print(f"{'ID':<4} {'Arrival (min)':<12} {'Day':<6} {'Node':<6} {'BW (MHz)':<10} {'Device Type':<12}")
        print("-" * 60)
        for req in self.demand:
            day = req.arrival_time / MINUTES_PER_DAY
            print(f"{req.req_id:<4} {req.arrival_time:<12} {day:<6.1f} {req.node_id:<6} "
                  f"{req.requested_bw:<10} {req.device_type:<12}")
        
        # Visualize grid layout
        fig, ax = plt.subplots(figsize=(4, 4))
        # Plot nodes on grid
        for node in self.env.nodes:
            ax.scatter(node.col, node.row, c='black')
            ax.text(node.col, node.row, str(node.node_id), color='white',
                    ha='center', va='center', fontsize=8)
        # Draw grid lines
        for x in range(self.env.num_nodes_cols):
            ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
        for y in range(self.env.num_nodes_rows):
            ax.axhline(y, color='gray', linestyle='--', linewidth=0.5)
        ax.set_xlim(-0.5, self.env.num_nodes_cols - 0.5)
        ax.set_ylim(-0.5, self.env.num_nodes_rows - 0.5)
        ax.set_title('Grid of Nodes (2x2 squares => 3x3 nodes)')
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        plt.tight_layout()
        plt.savefig('grid_nodes.png')
        print('Saved grid visualization to grid_nodes.png')
    
    def test_licensing_modes(self):
        """
        Compare different licensing modes.
        This test implements proper manual licensing delay and correct SUE calculation.
        """
        # Create architectures for each licensing mode
        archs = {
            "Manual": get_architecture_by_name(
                coord_mode="Centralized",
                licensing="Manual",
                freq_plan="Sub Channels",
                interference="Beamforming",
                sensing="Device Based",
                pricing="No Cost",
                enforcement="Active",
                priority="Co-Primary"
            ),
            "Semi-Dynamic": get_architecture_by_name(
                coord_mode="Centralized",
                licensing="Semi-Dynamic",
                freq_plan="Sub Channels",
                interference="Beamforming",
                sensing="Device Based",
                pricing="No Cost",
                enforcement="Active",
                priority="Exclusive"
            ),
            "Dynamic": get_architecture_by_name(
                coord_mode="Centralized",
                licensing="Dynamic",
                freq_plan="Sub Channels",
                interference="Beamforming",
                sensing="Device Based",
                pricing="No Cost",
                enforcement="Active",
                priority="Co-Primary"
            )
        }
        
        # Track metrics for each mode
        active_assignments_by_mode = {}
        coordination_cost_by_mode = {}
        sue_values_by_mode = {}
        correct_sue_by_mode = {}
        avg_daily_users_by_mode = {}
        requests_processed_by_mode = {}
        
        # Constants for SUE calculation
        TOTAL_BANDWIDTH = 600  # MHz
        TOTAL_AREA = self.env.num_squares  # 4 km² in a 2x2 grid
        
        for name, arch in archs.items():
            print(f"\nRunning simulation for {name} licensing mode...")
            print("=" * 60)
            
            # Create a separate spectrum manager and metrics collector
            metrics = MetricsCollector()
            manager = SpectrumManager(self.env, arch, metrics)
            
            # Create SUE tracker
            sue_tracker = SUETracker(TOTAL_BANDWIDTH, TOTAL_AREA, SIM_DAYS)
            
            # Track metrics over time
            active_assignments = []
            coordination_costs = []
            sue_values = []
            requests_processed = 0
            
            # For manual licensing, track pending requests and their scheduled processing times
            if name == "Manual":
                pending_requests = []
                
            # Track assignments
            assignments_log = []
            
            # Run day by day
            for day in range(SIM_DAYS):
                start_tick = day * MINUTES_PER_DAY
                end_tick = (day + 1) * MINUTES_PER_DAY
                
                # Get requests for this day
                daily_requests = [req for req in self.demand if start_tick <= req.arrival_time < end_tick]
                
                if daily_requests:
                    print(f"\nDay {day}: Processing {len(daily_requests)} new request(s)")
                
                # Handle new requests based on licensing mode
                if name == "Manual":
                    # For manual licensing, delay processing by MANUAL_PROCESSING_DELAY_DAYS
                    for req in daily_requests:
                        processing_time = req.arrival_time + (MANUAL_PROCESSING_DELAY_DAYS * MINUTES_PER_DAY)
                        pending_requests.append((req, processing_time))
                        print(f"  Request ID {req.req_id} ({req.device_type}, {req.requested_bw} MHz) "
                              f"queued for processing on day {processing_time / MINUTES_PER_DAY:.1f}")
                    
                    # Process any pending requests that have reached their processing time
                    requests_to_process = []
                    remaining_pending = []
                    
                    for req, proc_time in pending_requests:
                        if proc_time <= end_tick:
                            requests_to_process.append(req)
                            requests_processed += 1
                            print(f"  Processing delayed request ID {req.req_id} "
                                  f"({req.device_type}, {req.requested_bw} MHz)")
                        else:
                            remaining_pending.append((req, proc_time))
                    
                    # Update pending requests
                    pending_requests = remaining_pending
                    
                    # Process due requests
                    if requests_to_process:
                        # Remember the number of active assignments before processing
                        prev_active_count = len(manager.active)
                        
                        manager.process_arrivals(requests_to_process, end_tick - 1)
                        
                        # Check which requests were granted
                        new_active_count = len(manager.active)
                        if new_active_count > prev_active_count:
                            print(f"  Granted {new_active_count - prev_active_count} of {len(requests_to_process)} requests")
                            for assignment in manager.active[-new_active_count:]:
                                assignments_log.append({
                                    'day': day,
                                    'node_id': assignment.node_id,
                                    'freq_range': f"{assignment.freq_start}-{assignment.freq_end}",
                                    'device_type': assignment.device_type,
                                    'quality': assignment.quality
                                })
                                print(f"    Node {assignment.node_id}: {assignment.freq_start}-{assignment.freq_end} MHz, "
                                      f"quality: {assignment.quality:.2f}")
                        else:
                            print(f"  All {len(requests_to_process)} requests were denied")
                else:
                    # For Semi-Dynamic and Dynamic, process immediately
                    for req in daily_requests:
                        # Remember the number of active assignments before processing
                        prev_active_count = len(manager.active)
                        
                        print(f"  Processing request ID {req.req_id} ({req.device_type}, {req.requested_bw} MHz)")
                        manager.process_arrivals([req], req.arrival_time)
                        requests_processed += 1
                        
                        # Check if the request was granted
                        new_active_count = len(manager.active)
                        if new_active_count > prev_active_count:
                            print(f"    Request granted")
                            assignment = manager.active[-1]
                            assignments_log.append({
                                'day': day,
                                'node_id': assignment.node_id,
                                'freq_range': f"{assignment.freq_start}-{assignment.freq_end}",
                                'device_type': assignment.device_type,
                                'quality': assignment.quality
                            })
                            print(f"    Node {assignment.node_id}: {assignment.freq_start}-{assignment.freq_end} MHz, "
                                  f"quality: {assignment.quality:.2f}")
                        else:
                            print(f"    Request denied for Node {req.node_id}")
                
                # Run all ticks for the day
                max_users_today = 0
                for tick in range(start_tick, end_tick):
                    manager.tick_housekeeping(tick)
                    
                    # Track max users for the day
                    current_users = len(manager.active)
                    max_users_today = max(max_users_today, current_users)
                    
                    # Every hour, record metrics
                    if tick % 60 == 0:
                        active_assignments.append(current_users)
                        coordination_costs.append(metrics.coord_queries)
                        sue_value = metrics.mhz_km2_min_granted / (TOTAL_BANDWIDTH * TOTAL_AREA * (tick + 1))
                        sue_values.append(sue_value)
                
                # Update daily user count in SUE tracker
                sue_tracker.update_daily_count(day, max_users_today)
                
                # Print daily summary if there were any requests or active assignments
                if daily_requests or max_users_today > 0:
                    print(f"  End of day {day}: {max_users_today} active assignments, "
                          f"coordination cost: {metrics.coord_queries:.1f}")
            
            # Print final assignment summary
            print(f"\nFinal Assignments for {name} licensing mode:")
            print("=" * 60)
            if assignments_log:
                print(f"{'Day':<6} {'Node':<6} {'Freq Range':<20} {'Device Type':<12} {'Quality':<8}")
                print("-" * 60)
                for a in assignments_log:
                    print(f"{a['day']:<6} {a['node_id']:<6} {a['freq_range']:<20} {a['device_type']:<12} {a['quality']:<.2f}")
            else:
                print("No assignments made")
            
            # Calculate correct SUE based on average daily users
            correct_sue, avg_daily_users = sue_tracker.calculate_sue()
            
            # Store metrics for this mode
            active_assignments_by_mode[name] = active_assignments
            coordination_cost_by_mode[name] = coordination_costs
            sue_values_by_mode[name] = sue_values
            correct_sue_by_mode[name] = correct_sue
            avg_daily_users_by_mode[name] = avg_daily_users
            requests_processed_by_mode[name] = requests_processed
            
            # Print results
            print(f"\nFinal Results for {name} licensing mode:")
            print("=" * 60)
            print(f"  Requests processed: {requests_processed}")
            print(f"  Peak active assignments: {max(active_assignments)}")
            print(f"  Average daily users: {avg_daily_users:.2f}")
            print(f"  Final coordination cost: {coordination_costs[-1]}")
            print(f"  Traditional SUE: {sue_values[-1]:.6f}")
            print(f"  Correct SUE (avg daily users): {correct_sue:.6f}")
        
        # Verify that Dynamic and Semi-Dynamic processed more requests than Manual
        self.assertGreater(
            requests_processed_by_mode["Dynamic"], 
            requests_processed_by_mode["Manual"],
            "Dynamic should process more requests than Manual due to processing delay"
        )
        
        self.assertGreater(
            requests_processed_by_mode["Semi-Dynamic"], 
            requests_processed_by_mode["Manual"],
            "Semi-Dynamic should process more requests than Manual due to processing delay"
        )
        
        # Generate visualizations
        self._create_visualizations(
            active_assignments_by_mode, 
            coordination_cost_by_mode, 
            sue_values_by_mode,
            correct_sue_by_mode,
            avg_daily_users_by_mode,
            requests_processed_by_mode
        )
    
    def _create_visualizations(self, active_assignments, coordination_costs, sue_values, correct_sue, avg_daily_users, requests_processed):
        """Create visualizations of the licensing mode comparison."""
        # Only create visualization when test runs directly
        if not sys.argv[0].endswith('test_licensing_mode_comparison.py'):
            return
        
        # Colors for each mode
        colors = {'Manual': 'blue', 'Semi-Dynamic': 'green', 'Dynamic': 'red'}
        
        # Figure 1: Active assignments over time
        fig, ax = plt.subplots(figsize=(12, 6))
        hours = np.arange(len(next(iter(active_assignments.values())))) / 24  # Convert to days
        
        for mode, assignments in active_assignments.items():
            ax.plot(hours, assignments, label=mode, color=colors[mode], alpha=0.7)
        
        ax.set_title('Active Spectrum Assignments Over Time by Licensing Mode')
        ax.set_xlabel('Days')
        ax.set_ylabel('Number of Active Assignments')
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        plt.savefig('licensing_active_assignments.png')
        print("Saved visualization to licensing_active_assignments.png")
        
        # Figure 2: Coordination costs over time
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for mode, costs in coordination_costs.items():
            ax.plot(hours, costs, label=mode, color=colors[mode], alpha=0.7)
        
        ax.set_title('Coordination Costs Over Time by Licensing Mode')
        ax.set_xlabel('Days')
        ax.set_ylabel('Coordination Cost')
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        plt.savefig('licensing_coordination_costs.png')
        print("Saved visualization to licensing_coordination_costs.png")
        
        # Figure 3: SUE values over time
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for mode, values in sue_values.items():
            ax.plot(hours, values, label=mode, color=colors[mode], alpha=0.7)
        
        ax.set_title('Traditional SUE Over Time by Licensing Mode')
        ax.set_xlabel('Days')
        ax.set_ylabel('Spectral Use Efficiency (MHz·km²·min based)')
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        plt.savefig('licensing_sue_values.png')
        print("Saved visualization to licensing_sue_values.png")
        
        # Figure 4: Bar charts comparing the final metrics
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        
        # Plot 1: Final Coordination Costs
        mode_names = list(colors.keys())
        final_costs = [coordination_costs[mode][-1] for mode in mode_names]
        ax1.bar(mode_names, final_costs, color=[colors[mode] for mode in mode_names])
        ax1.set_title('Final Coordination Costs')
        ax1.set_ylabel('Coordination Cost')
        ax1.grid(True, axis='y')
        
        # Plot 2: Correct SUE (based on avg daily users)
        user_sue_values = [correct_sue[mode] for mode in mode_names]
        ax2.bar(mode_names, user_sue_values, color=[colors[mode] for mode in mode_names])
        ax2.set_title('Correct SUE\n(Avg Daily Users / (B×S×T))')
        ax2.set_ylabel('SUE')
        for i, mode in enumerate(mode_names):
            ax2.text(i, user_sue_values[i] * 1.05, f'{avg_daily_users[mode]:.2f} users',
                    ha='center', va='bottom', fontsize=9)
        ax2.grid(True, axis='y')
        
        # Plot 3: Requests Processed
        reqs_processed = [requests_processed[mode] for mode in mode_names]
        ax3.bar(mode_names, reqs_processed, color=[colors[mode] for mode in mode_names])
        ax3.set_title('Requests Processed')
        ax3.set_ylabel('Number of Requests')
        ax3.grid(True, axis='y')
        
        plt.tight_layout()
        plt.savefig('licensing_comparison_bars.png')
        print("Saved visualization to licensing_comparison_bars.png")


if __name__ == '__main__':
    unittest.main()
