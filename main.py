#!/usr/bin/env python3
"""
main.py

Entry point for the spectrum sharing simulation.
"""

import sys
import random
import time
from config.parameters import RANDOM_SEED
from config.scenarios import SCENARIOS, DEFAULT_SIM_MINUTES
from models.environment import Environment
from core.simulation import Simulation
from core.event_simulation import EventDrivenSimulation
from utils.demand_generator import generate_demand
from morphology.architecture_enumerator import generate_all_architectures, get_architecture_by_name

def run_single_architecture(arch_policy, scenario_key="medium", sim_minutes=DEFAULT_SIM_MINUTES):
    """
    Run simulation for a single architecture policy and scenario.
    
    Args:
        arch_policy: The architecture policy to simulate
        scenario_key: Key of the scenario to use
        sim_minutes: Number of simulation minutes
        
    Returns:
        Dictionary with simulation results
    """
    # Set the random seed for reproducibility
    random.seed(RANDOM_SEED)
    
    # Create the environment
    env = Environment(squares_rows=3, squares_cols=3)
    
    # Generate demand based on the scenario
    demand_list = generate_demand(scenario_key, env, sim_minutes)
    
    # Create and run the simulation
    simulation = Simulation(env, arch_policy, demand_list, sim_minutes)
    results = simulation.run()
    
    # Save results to CSV
    simulation.save_results(scenario_key)
    
    return results

def run_event_driven_architecture(arch_policy, scenario_key="medium", sim_minutes=DEFAULT_SIM_MINUTES):
    """
    Run event-driven simulation for a single architecture policy and scenario.
    Args:
        arch_policy: The architecture policy to simulate
        scenario_key: Key of the scenario to use
        sim_minutes: Number of simulation minutes
    Returns:
        Dictionary with simulation results
    """
    random.seed(RANDOM_SEED)
    env = Environment(squares_rows=3, squares_cols=3)
    demand_list = generate_demand(scenario_key, env, sim_minutes)
    simulation = EventDrivenSimulation(env, arch_policy, demand_list, sim_minutes)
    results = simulation.run()
    simulation.save_results(scenario_key)
    return results

def run_batch(scenario_keys=None, max_architectures=None):
    """
    Run a batch of simulations for multiple architectures and scenarios.
    
    Args:
        scenario_keys: List of scenario keys to run, or None for all scenarios
        max_architectures: Maximum number of architectures to run, or None for all
    """
    if scenario_keys is None:
        scenario_keys = list(SCENARIOS.keys())
    
    # Generate all feasible architectures
    architectures = generate_all_architectures(apply_filter=True)
    
    if max_architectures:
        architectures = architectures[:max_architectures]
    
    total_runs = len(architectures) * len(scenario_keys)
    print(f"Running {total_runs} simulations ({len(architectures)} architectures × {len(scenario_keys)} scenarios)")
    
    current_run = 0
    start_time = time.time()
    
    # Run simulations for all combinations
    for scenario_key in scenario_keys:
        for arch in architectures:
            current_run += 1
            progress = current_run / total_runs * 100
            elapsed = time.time() - start_time
            eta = (elapsed / current_run) * (total_runs - current_run) if current_run > 0 else 0
            
            # Print progress
            arch_id = f"{arch.coordination_mode}-{arch.licensing_mode}-{arch.priority_mode}"
            print(f"[{progress:.1f}%] Running {arch_id} with {scenario_key} scenario (ETA: {eta:.0f}s)")
            
            # Run the simulation
            run_single_architecture(arch, scenario_key)
    
    print(f"Batch complete. Total time: {time.time() - start_time:.1f}s")

def main():
    """Main entry point."""
    # Option 1: Run a specific architecture
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        arch_policy = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Power Control",
            sensing="Device Based",
            pricing="Usage Based",
            enforcement="Active",
            priority="Hierarchical"
        )
        scenario_key = "medium" if len(sys.argv) <= 2 else sys.argv[2]
        results = run_single_architecture(arch_policy, scenario_key)
        print("Results:", results)
    
    # Option 2: Run a batch for a specific scenario
    elif len(sys.argv) > 1 and sys.argv[1] == "scenario":
        scenario_key = "medium" if len(sys.argv) <= 2 else sys.argv[2]
        max_architectures = 10 if len(sys.argv) <= 3 else int(sys.argv[3])
        run_batch([scenario_key], max_architectures)
    
    # Option 3: Run a full batch on all scenarios
    elif len(sys.argv) > 1 and sys.argv[1] == "full":
        max_architectures = None if len(sys.argv) <= 2 else int(sys.argv[2])
        run_batch(None, max_architectures)
    
    # Option 4: Run tests
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        import unittest
        from tests.test_exclusive_partition import TestExclusivePartition
        from tests.test_hierarchical_preemption import TestHierarchicalPreemption
        from tests.test_semi_dynamic_queue_cost import TestSemiDynamicQueueCost
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        suite.addTests(loader.loadTestsFromTestCase(TestExclusivePartition))
        suite.addTests(loader.loadTestsFromTestCase(TestHierarchicalPreemption))
        suite.addTests(loader.loadTestsFromTestCase(TestSemiDynamicQueueCost))
        
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    
    # Default: print usage
    else:
        print("Usage:")
        print("  python main.py single [scenario]")
        print("  python main.py scenario [scenario] [max_architectures]")
        print("  python main.py full [max_architectures]")
        print("  python main.py test")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())