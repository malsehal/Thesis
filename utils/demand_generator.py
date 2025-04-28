#!/usr/bin/env python3
"""
Demand Generator:
Generates a list of SpectrumRequest objects representing demand for spectrum access.
Each request is created with:
  - An arrival time from the selected scenario.
  - A desired node, evenly distributed across the nodes via round-robin.
  - A requested bandwidth drawn by weighted random from the device's bandwidth distribution.
  - A device type, drawn by weighted random from the scenario's device distribution.
  - A desired frequency allocation, randomly chosen such that the frequency block's
    width equals the requested bandwidth and lies within FREQ_BASE_MHZ to 
    FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ. The start frequency is aligned to 10 MHz boundaries.
    
The scenario key specifies which demand pattern to use.
"""

import random
from models.request import SpectrumRequest
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ
from config.scenarios import SCENARIOS, DEFAULT_SIM_MINUTES

def generate_demand(scenario_key, environment, sim_minutes=DEFAULT_SIM_MINUTES, rng_seed=42):
    """
    Generates a list of SpectrumRequest objects based on the specified scenario.

    Parameters:
      scenario_key (str): The key of the scenario to use ("low", "medium", "high").
      environment: An environment instance that contains nodes.
      sim_minutes (int): The simulation duration in minutes.
      rng_seed (int): Seed for the random number generator.

    Returns:
      List[SpectrumRequest]: The list of generated requests, ordered by arrival time.
    """
    # Set the random seed for reproducibility
    random.seed(rng_seed)
    
    # Look up the scenario
    scenario = SCENARIOS[scenario_key]
    
    demand_list = []
    request_id = 0
    
    # Filter the arrival minutes to those within the simulation horizon
    arrival_minutes = [t for t in scenario.arrival_minutes if t < sim_minutes]
    
    # Evenly distribute requests across nodes via round-robin
    nodes = environment.nodes
    n_nodes = len(nodes)
    for idx, arrival_time in enumerate(arrival_minutes):
        node = nodes[idx % n_nodes]
        node_id = node.node_id
        
        # Select a device type based on weighted distribution
        device_choices, device_weights = zip(*scenario.device_dist)
        device_type = random.choices(device_choices, weights=device_weights, k=1)[0]
        
        # Select bandwidth for this device type based on weighted distribution
        bw_choices, bw_weights = zip(*scenario.bw_dist[device_type])
        requested_bw = random.choices(bw_choices, weights=bw_weights, k=1)[0]
        
        # Determine the maximum allowable start frequency so that the entire block fits within the band
        max_start_possible = FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ - requested_bw
        # Build a list of possible start frequencies aligned to 10 MHz boundaries
        possible_starts = list(range(FREQ_BASE_MHZ, max_start_possible + 1, 10))
        freq_start = random.choice(possible_starts)
        freq_end = freq_start + requested_bw

        # Create the SpectrumRequest
        req = SpectrumRequest(request_id, arrival_time, node_id, requested_bw, device_type)
        # Attach the desired frequency allocation
        req.desired_frequency = (freq_start, freq_end)
        # Also assign the frequency start and end directly for later use
        req.freq_start = freq_start
        req.freq_end = freq_end

        req.add_trace(
            f"Arrived at time {arrival_time}: node={node_id}, requested_bw={requested_bw} MHz, "
            f"device_type={device_type}, desired_frequency=({freq_start}-{freq_end})"
        )
        demand_list.append(req)
        request_id += 1

    # No need to sort as arrival minutes are already in order
    return demand_list

# For testing the demand generator independently:
if __name__ == "__main__":
    from models.environment import Environment  # Ensure your environment module is available.
    env = Environment(squares_rows=1, squares_cols=1)
    scenario_key = "medium"  # Use medium demand scenario
    requests = generate_demand(scenario_key, env)
    print(f"Generated Demand Requests for scenario '{scenario_key}':")
    print(f"Total requests: {len(requests)}")
    for i, req in enumerate(requests[:5]):  # Print first 5 for brevity
        print(req)
        for trace in req.trace:
            print("   " + trace)
    if len(requests) > 5:
        print(f"... and {len(requests) - 5} more requests")