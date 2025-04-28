"""
Test the Semi-Dynamic licensing mechanism over a month-long simulation.

This test verifies that:
1. Semi-Dynamic licensing correctly renews assignments daily (1440 minute intervals)
2. Metrics such as coordination query costs, assignment counts, and renewal patterns
   behave as expected over a month-long period
"""
import sys
import os
import unittest
import matplotlib.pyplot as plt
import numpy as np

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.environment import Environment
from utils.demand_generator import generate_demand
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from core.simulation import Simulation
from morphology.architecture_enumerator import get_architecture_by_name

# Constants for the simulation
SIM_DAYS = 30
MINUTES_PER_DAY = 1440
SIM_MINUTES = SIM_DAYS * MINUTES_PER_DAY


class TestSemiDynamicLicensingMonth(unittest.TestCase):
    """Test suite for Semi-Dynamic licensing over a month-long simulation."""
    
    def setUp(self):
        """Set up the test environment with a 2x2 grid."""
        self.env = Environment(squares_rows=2, squares_cols=2)
        self.metrics = MetricsCollector()
        
        # Create a Semi-Dynamic architecture
        self.arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Semi-Dynamic",  # Semi-Dynamic licensing mode
            freq_plan="Sub Channels",
            interference="Beamforming",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Generate medium demand scenario
        self.demand = generate_demand("medium", self.env, sim_minutes=SIM_MINUTES)
        
        # Create simulation instance
        self.simulation = Simulation(
            environment=self.env,
            architecture_policy=self.arch,
            demand_list=self.demand,
            sim_minutes=SIM_MINUTES
        )
    
    def test_monthly_simulation(self):
        """
        Run a month-long simulation and verify the semi-dynamic licensing mechanism.
        This tests basic functionality of Semi-Dynamic licensing, where assignments
        should be renewed daily.
        """
        # Create spectrum manager that we can track separately from the simulation
        manager = SpectrumManager(self.env, self.arch, self.metrics)
        
        # Track metrics over time
        active_assignments = []
        renewal_costs = []
        daily_coordination_queries = []
        
        # Initial metrics
        prev_coordination_cost = 0
        
        # Run simulation day by day to track daily metrics
        for day in range(SIM_DAYS):
            start_tick = day * MINUTES_PER_DAY
            end_tick = (day + 1) * MINUTES_PER_DAY
            
            # Get requests for this day
            daily_requests = [req for req in self.demand if start_tick <= req.arrival_time < end_tick]
            
            # Process each request
            for req in daily_requests:
                manager.process_arrivals([req], req.arrival_time)
            
            # Run all ticks for the day
            for tick in range(start_tick, end_tick):
                manager.tick_housekeeping(tick)
                
                # Every hour, check metrics
                if tick % 60 == 0:
                    active_assignments.append(len(manager.active))
            
            # Capture end-of-day metrics
            daily_renewal = self.metrics.coord_queries - prev_coordination_cost
            renewal_costs.append(daily_renewal)
            prev_coordination_cost = self.metrics.coord_queries
            daily_coordination_queries.append(daily_renewal)
        
        # Run the full simulation to get complete results
        results = self.simulation.run()
        
        # Verify basic results
        self.assertGreater(results["requests_total"], 0, "Should have processed requests")
        
        # Verify coordination cost pattern (should increase every day due to daily renewals)
        # After initial assignments, there should be consistent coordination costs for renewals
        for i in range(1, len(daily_coordination_queries)):
            if i >= 2:  # After a couple of days of establishing assignments
                self.assertGreater(daily_coordination_queries[i], 0, 
                               f"Day {i} should have coordination costs for renewals")
        
        # Create visualization of active assignments over time
        self._visualize_metrics(active_assignments, daily_coordination_queries, renewal_costs)
    
    def _visualize_metrics(self, active_assignments, daily_coordination_queries, renewal_costs):
        """Create visualizations of key metrics over time."""
        # Only create visualization when test runs directly (not via unittest runner)
        if not sys.argv[0].endswith('test_semi_dynamic_licensing_month.py'):
            return
            
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot active assignments over time (sampled hourly)
        hours = np.arange(len(active_assignments)) / 24  # Convert to days
        ax1.plot(hours, active_assignments)
        ax1.set_title('Active Spectrum Assignments Over Time')
        ax1.set_xlabel('Days')
        ax1.set_ylabel('Number of Active Assignments')
        ax1.grid(True)
        
        # Plot daily coordination query costs
        days = np.arange(len(daily_coordination_queries))
        ax2.bar(days, daily_coordination_queries, alpha=0.7)
        ax2.set_title('Daily Coordination Query Costs')
        ax2.set_xlabel('Day')
        ax2.set_ylabel('Coordination Cost')
        ax2.grid(True)
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('semi_dynamic_monthly_metrics.png')
        print(f"Saved visualization to semi_dynamic_monthly_metrics.png")
        
        # Also generate comparison with other licensing modes
        self._visualize_licensing_comparison()
    
    def _visualize_licensing_comparison(self):
        """Compare Semi-Dynamic with Manual and Dynamic licensing modes."""
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
            "Semi-Dynamic": self.arch,
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
        
        # Run simulation for each architecture with detailed tracking
        results = {}
        active_assignments_by_mode = {}
        mhz_km2_by_mode = {}
        
        for name, arch in archs.items():
            # Create a new simulation
            sim = Simulation(
                environment=self.env,
                architecture_policy=arch,
                demand_list=self.demand,
                sim_minutes=SIM_MINUTES
            )
            
            # Track metrics over time for this mode
            active_assignments = []
            mhz_km2_min_values = []
            
            # Create a separate spectrum manager to track
            metrics = MetricsCollector()
            manager = SpectrumManager(self.env, arch, metrics)
            
            # Run day by day
            for day in range(SIM_DAYS):
                start_tick = day * MINUTES_PER_DAY
                end_tick = (day + 1) * MINUTES_PER_DAY
                
                # Get requests for this day
                daily_requests = [req for req in self.demand if start_tick <= req.arrival_time < end_tick]
                
                # Process each request
                for req in daily_requests:
                    manager.process_arrivals([req], req.arrival_time)
                
                # Run all ticks for the day
                for tick in range(start_tick, end_tick):
                    manager.tick_housekeeping(tick)
                    
                    # Every hour, check metrics
                    if tick % 60 == 0:
                        active_assignments.append(len(manager.active))
                        mhz_km2_min_values.append(metrics.mhz_km2_min_granted)
            
            # Store metrics for this mode
            active_assignments_by_mode[name] = active_assignments
            mhz_km2_by_mode[name] = mhz_km2_min_values
            
            # Run the full simulation to get complete results
            results[name] = sim.run()
            
            # Print detailed SUE calculation for debugging
            print(f"\n{name} Licensing Mode - SUE Calculation:")
            print(f"  mhz_km2_min_granted: {results[name]['mhz_km2_min_granted']:.2f}")
            total_band_mhz = 600  # From config.parameters.TOTAL_BANDWIDTH_MHZ
            total_area_km2 = self.env.num_squares  # 4 in a 2x2 grid
            print(f"  total_band_mhz * total_area_km2 * total_minutes: {total_band_mhz} * {total_area_km2} * {SIM_MINUTES} = {total_band_mhz * total_area_km2 * SIM_MINUTES}")
            print(f"  SUE = {results[name]['SUE']:.6f}")
            print(f"  requests_total: {results[name]['requests_total']}")
            print(f"  requests_denied: {results[name]['requests_denied']}")
            print(f"  Blocking probability: {results[name]['Blocking_Prob']:.4f}")
        
        # Create comparison visualizations
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot 1: Coordination costs comparison
        mode_names = list(results.keys())
        coord_costs = [results[mode]["Coordination_Cost"] for mode in mode_names]
        ax1.bar(mode_names, coord_costs, color=['blue', 'green', 'red'])
        ax1.set_title('Total Coordination Cost by Licensing Mode')
        ax1.set_ylabel('Coordination Cost')
        ax1.grid(True, axis='y')
        
        # Plot 2: Spectrum utilization comparison
        spectral_efficiency = [results[mode]["SUE"] for mode in mode_names]
        ax2.bar(mode_names, spectral_efficiency, color=['blue', 'green', 'red'])
        ax2.set_title('Spectral Efficiency by Licensing Mode')
        ax2.set_ylabel('Spectral Efficiency (SUE)')
        ax2.grid(True, axis='y')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('licensing_mode_comparison.png')
        print(f"Saved comparison visualization to licensing_mode_comparison.png")
        
        # Create additional comparison of active assignments over time
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot active assignments over time for each mode
        hours = np.arange(len(active_assignments_by_mode["Manual"])) / 24  # Convert to days
        colors = {'Manual': 'blue', 'Semi-Dynamic': 'green', 'Dynamic': 'red'}
        
        for mode, assignments in active_assignments_by_mode.items():
            ax1.plot(hours, assignments, label=mode, color=colors[mode], alpha=0.7)
        
        ax1.set_title('Active Spectrum Assignments Over Time by Licensing Mode')
        ax1.set_xlabel('Days')
        ax1.set_ylabel('Number of Active Assignments')
        ax1.legend()
        ax1.grid(True)
        
        # Plot MHz·km²·minutes granted over time for each mode
        for mode, values in mhz_km2_by_mode.items():
            ax2.plot(hours, values, label=mode, color=colors[mode], alpha=0.7)
        
        ax2.set_title('Spectrum Usage (MHz·km²·min) by Licensing Mode')
        ax2.set_xlabel('Days')
        ax2.set_ylabel('MHz·km²·min')
        ax2.legend()
        ax2.grid(True)
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('licensing_mode_detailed_comparison.png')
        print(f"Saved detailed comparison visualization to licensing_mode_detailed_comparison.png")


if __name__ == '__main__':
    unittest.main()
