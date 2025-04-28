"""
Core simulation module for spectrum management.
"""
import os
import csv
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from config.scenarios import DEFAULT_SIM_MINUTES

class Simulation:
    """
    Main simulation class that orchestrates the spectrum management process.
    """
    def __init__(self, environment, architecture_policy, demand_list, sim_minutes=DEFAULT_SIM_MINUTES):
        """
        Initialize the simulation.
        
        Args:
            environment: The simulation environment
            architecture_policy: The architectural policy to apply
            demand_list: List of requests (already sorted by arrival time)
            sim_minutes: Total simulation minutes
        """
        self.environment = environment
        self.architecture_policy = architecture_policy
        self.demand_list = demand_list
        self.sim_minutes = sim_minutes
        
        # Create metrics collector and spectrum manager
        self.metrics = MetricsCollector()
        self.spectrum_manager = SpectrumManager(environment, architecture_policy, self.metrics)
        
        # Results storage
        self.results = None
    
    def run(self):
        """
        Run the simulation.
        
        Returns:
            Dictionary with simulation results
        """
        # Create cursor to track position in demand list
        cursor = 0
        demand_length = len(self.demand_list)
        
        # Main simulation loop
        for tick in range(self.sim_minutes):
            # Process arrivals for this tick
            arrivals = []
            while cursor < demand_length and self.demand_list[cursor].arrival_time == tick:
                arrivals.append(self.demand_list[cursor])
                cursor += 1
            
            # Handle arrivals based on licensing mode
            self.spectrum_manager.process_arrivals(arrivals, tick)
            self.spectrum_manager.tick_housekeeping(tick)
        
        # Gather final assignments
        final_active_assignments = []
        for node in self.environment.nodes:
            final_active_assignments.extend(node.active_assignments)

        # DEBUG: Print mitigated_conflicts before metrics
        mitigated_conflicts = getattr(self.spectrum_manager, 'mitigated_conflicts', None)
        print("[DEBUG] mitigated_conflicts at end:", mitigated_conflicts)
        print("[DEBUG] Final assignments (assignment_id, node_id, freq_start, freq_end):")
        for a in final_active_assignments:
            print(f"  id={a.assignment_id}, node={a.node_id}, freq=({a.freq_start}-{a.freq_end})")

        # Call metrics report with mitigated_conflicts
        self.results = self.metrics.final_report(
            total_band_mhz=self.environment.squares_cols * 120,  # Example: 120 MHz per col
            total_area_km2=self.environment.num_squares,
            sim_minutes=self.sim_minutes,
            final_active_assignments=final_active_assignments,
            environment=self.environment,
            arch_policy=self.architecture_policy,
            mitigated_conflicts=mitigated_conflicts
        )
        # Add architecture policy info
        self.results.update({
            "coordination_mode": self.architecture_policy.coordination_mode,
            "licensing_mode": self.architecture_policy.licensing_mode,
            "freq_plan": self.architecture_policy.freq_plan,
            "interference_mitigation": self.architecture_policy.interference_mitigation,
            "sensing_mode": self.architecture_policy.sensing_mode,
            "pricing_mode": self.architecture_policy.pricing_mode,
            "enforcement_mode": self.architecture_policy.enforcement_mode,
            "priority_mode": self.architecture_policy.priority_mode
        })
        
        return self.results
    
    def save_results(self, scenario_key, results_dir="results"):
        """
        Save simulation results to CSV.
        
        Args:
            scenario_key: Key of the scenario used
            results_dir: Directory to save results
        """
        if self.results is None:
            raise ValueError("No results to save. Run simulation first.")
        
        # Add scenario key to results
        self.results["scenario"] = scenario_key
        
        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)
        
        # Determine CSV file path
        csv_path = os.path.join(results_dir, "simulation_results.csv")
        file_exists = os.path.isfile(csv_path)
        
        # Write results
        with open(csv_path, 'a', newline='') as csvfile:
            fieldnames = list(self.results.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(self.results)
