#!/usr/bin/env python3
"""
Runs event-driven spectrum simulation for the HIGH demand scenario across all feasible architectures.
Saves results to results/high_demand/event_driven_results_high.csv and generates trade space plots.
"""
import os
import csv
from config.scenarios import SCENARIOS
from models.environment import Environment
from utils.demand_generator import generate_demand
from morphology.architecture_enumerator import generate_all_architectures
from core.event_simulation import EventDrivenSimulation
from tqdm import tqdm
import copy
import pandas as pd

# Scenario configuration
SCENARIO_KEY = "high"
SIM_DAYS = 180
SCENARIO_CONFIG = {
    "scenario_key": SCENARIO_KEY,
    "sim_days": SIM_DAYS,
    "squares_rows": 5,
    "squares_cols": 5,
    "total_band_mhz": 600,
}

RESULTS_DIR = "results/high_demand"
RESULTS_CSV = os.path.join(RESULTS_DIR, "event_driven_results_high.csv")
PLOT_SCRIPT = "plot_high_demand_trade_space.py"

os.makedirs(RESULTS_DIR, exist_ok=True)

# Prepare simulation parameters
sim_minutes = SIM_DAYS * 24 * 60

# Enumerate all feasible architectures
architectures = generate_all_architectures(apply_filter=True)

# Run simulation for all architectures and collect results
all_results = []
for arch in tqdm(architectures, desc="Architectures", unit="arch"):
    env = Environment(squares_rows=SCENARIO_CONFIG["squares_rows"], squares_cols=SCENARIO_CONFIG["squares_cols"])
    demand = generate_demand(SCENARIO_KEY, env, sim_minutes, rng_seed=42)
    simulation = EventDrivenSimulation(env, arch, demand, sim_minutes)
    results = simulation.run()
    results["architecture_id"] = str(arch)
    all_results.append(results)

# Save all results to CSV
if all_results:
    df = pd.DataFrame(all_results)
    df.to_csv(RESULTS_CSV, index=False, float_format='%.8f')

# Generate trade space plot
os.system(f"python {PLOT_SCRIPT}")
