#!/usr/bin/env python3
"""
Script to run an event-driven spectrum sharing simulation for a user-specified architecture, demand scenario, and simulation duration.
Outputs performance metrics to the console.
"""
import random
from config.scenarios import SCENARIOS, DEFAULT_SIM_MINUTES
from models.environment import Environment
from utils.demand_generator import generate_demand
from morphology.architecture_enumerator import get_architecture_by_name, COORDINATION_MODES, LICENSING_MODES, FREQ_PLANS, INTERFERENCE_MITIGATIONS, SENSING_MODES, PRICING_MODES, ENFORCEMENT_MODES, PRIORITY_MODES
from core.event_simulation import EventDrivenSimulation
from core.metrics import MetricsCollector


def prompt_choice(prompt, choices, default=None):
    print(f"{prompt} (choices: {', '.join(choices)})")
    if default:
        print(f"Press Enter to use default: {default}")
    while True:
        val = input(f"Enter choice: ").strip()
        if not val and default:
            return default
        if val in choices:
            return val
        print(f"Invalid choice. Please choose from: {', '.join(choices)}")

def prompt_text(prompt, default=None):
    if default:
        val = input(f"{prompt} [default: {default}]: ").strip()
        return val if val else default
    else:
        return input(f"{prompt}: ").strip()


def main():
    print("=== Event-Driven Spectrum Simulation ===")
    scenario = prompt_choice("Select demand scenario", list(SCENARIO_CONFIG.keys()), default='medium')
    config = SCENARIO_CONFIG[scenario]
    scenario_key = config["scenario_key"]
    sim_days = int(prompt_text("Simulation duration (days)", default=str(config["sim_days"])))
    squares_rows = int(prompt_text("Grid rows", default=str(config["squares_rows"])))
    squares_cols = int(prompt_text("Grid cols", default=str(config["squares_cols"])))

    coordination_mode = prompt_choice("coordination_mode", COORDINATION_MODES, default='Hybrid')
    licensing_mode = prompt_choice("licensing_mode", LICENSING_MODES, default='Manual')
    freq_plan = prompt_choice("freq_plan", FREQ_PLANS, default='Large Blocks')
    interference_mitigation = prompt_choice("interference_mitigation", INTERFERENCE_MITIGATIONS, default='Beamforming')
    sensing_mode = prompt_choice("sensing_mode", SENSING_MODES, default='Database Only')
    pricing_mode = prompt_choice("pricing_mode", PRICING_MODES, default='Auction Based')
    enforcement_mode = prompt_choice("enforcement_mode", ENFORCEMENT_MODES, default='Passive')
    priority_mode = prompt_choice("priority_mode", PRIORITY_MODES, default='Co-Primary')

    arch_policy = get_architecture_by_name(
        coordination_mode, licensing_mode, freq_plan, interference_mitigation,
        sensing_mode, pricing_mode, enforcement_mode, priority_mode
    )
    if arch_policy is None:
        print(f"Error: Architecture not found or infeasible.")
        return

    sim_minutes = sim_days * 24 * 60
    env = Environment(squares_rows=squares_rows, squares_cols=squares_cols)
    demand = generate_demand(scenario_key, env, sim_minutes, rng_seed=42)

    # print("\n=== Generated Demand (Spectrum Requests) ===")
    # for req in demand:
    #     print(f"RequestID={req.req_id}, arrival={req.arrival_time}, node={req.node_id}, bw={req.requested_bw}, device={req.device_type}")
    # print(f"Total requests generated: {len(demand)}")

    # print("\n=== Processing Spectrum Requests ===")
    simulation = EventDrivenSimulation(env, arch_policy, demand, sim_minutes)
    results = simulation.run()

    # Print processed requests: accepted/denied and why
    # print("\n=== Spectrum Request Outcomes ===")
    # for req in demand:
    #     status = "ACCEPTED" if getattr(req, 'is_assigned', False) else "DENIED"
    #     reason = getattr(req, 'reject_reason', None)
    #     if status == "DENIED" and reason:
    #         print(f"RequestID={req.req_id}: {status} (Reason: {reason})")
    #     else:
    #         print(f"RequestID={req.req_id}: {status}")
    #     # Print trace if available
    #     if hasattr(req, 'trace') and req.trace:
    #         for msg in req.trace:
    #             print(f"    Trace: {msg}")

    print("\n=== Simulation Performance Metrics ===")
    for k, v in results.items():
        print(f"{k}: {v}")

    # --- DEBUG: Compare admitted users in both modes ---
    # Print all admitted user IDs for comparison
    admitted_users = [req.req_id for req in demand if getattr(req, 'is_assigned', False)]
    # print(f"\n[DEBUG] Admitted user IDs: {admitted_users}")
    # print(f"[DEBUG] Total admitted users: {len(admitted_users)} out of {len(demand)} total requests")

    # --- GLOBAL INTERFERENCE CHECK (GROUND TRUTH) ---
    # print("\n=== Global Interference Check (Ground Truth) ===")
    # final_assignments = simulation.spectrum_manager.active
    # metrics = MetricsCollector()
    # num_interfering, interference_rate = metrics.compute_interference(final_assignments, env, arch_policy)
    # print(f"Num_Interfering_Assignments: {num_interfering}")
    # print(f"Interference_Rate: {interference_rate}")

if __name__ == "__main__":
    # Add default scenario config for interactive use
    SCENARIO_CONFIG = {
        "low": {
            "scenario_key": "low",
            "sim_days": 180,
            "squares_rows": 5,
            "squares_cols": 5,
            "total_band_mhz": 600,
        },
        "medium": {
            "scenario_key": "medium",
            "sim_days": 180,
            "squares_rows": 5,
            "squares_cols": 5,
            "total_band_mhz": 600,
        },
        "high": {
            "scenario_key": "high",
            "sim_days": 180,
            "squares_rows": 5,
            "squares_cols": 5,
            "total_band_mhz": 600,
        },
    }
    main()
