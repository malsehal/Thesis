#!/usr/bin/env python3
"""
Script to run an engineered event-driven spectrum sharing simulation that demonstrates a decentralized blind spot:
Two nodes that are not neighbors both request the same frequency and overlap in a square, but the decentralized logic misses the conflict.
"""
import random
from models.environment import Environment
from models.node import Node
from models.request import SpectrumRequest
from morphology.architecture_enumerator import get_architecture_by_name
from core.event_simulation import EventDrivenSimulation
from core.metrics import MetricsCollector


def main():
    print("=== Engineered Blind Spot Simulation ===")
    # 3 nodes, 2 squares (linear):
    # Node 0 covers [0, 1], Node 1 covers [1, 2], Node 2 covers [2, 3]
    # We'll engineer neighbor logic so node 0 and node 2 are NOT neighbors
    env = Environment(squares_rows=1, squares_cols=3)
    # Overwrite nodes to ensure overlap in square 1
    env.nodes = [
        Node(0, 0, 0, [0, 1]),
        Node(1, 0, 1, [1, 2]),
        Node(2, 0, 2, [1, 2])
    ]
    # Patch get_neighbors so node 0 and 2 are not neighbors (only node 1 is neighbor to both)
    env.get_neighbors = lambda node_id: [1] if node_id in [0, 2] else [0, 2]

    # Engineer demand: node 0 and node 2 both request the same freq at the same time, both cover square 1
    engineered_freq_start = 37000
    engineered_freq_end = 37200
    demand = [
        SpectrumRequest(0, 0, 0, 200, "5G"),  # node 0
        SpectrumRequest(1, 0, 2, 200, "5G"),  # node 2
        SpectrumRequest(2, 0, 1, 20, "IoT")   # node 1 (not conflicting)
    ]

    sim_minutes = 1
    arch_policy = get_architecture_by_name(
        "Decentralized",
        "Dynamic",
        "Freq Slicing",
        "Combination",
        "Device Based",
        "No Cost",
        "Active",
        "Co-Primary"
    )
    if arch_policy is None:
        print("Error: Architecture not found or infeasible.")
        return

    sim = EventDrivenSimulation(env, arch_policy, demand, sim_minutes)
    results = sim.run()

    # Force node 0 and node 2 assignments to overlap in both frequency and square
    assignments = sim.spectrum_manager.active
    node0 = next(a for a in assignments if a.node_id == 0)
    node2 = next(a for a in assignments if a.node_id == 2)
    node0.freq_start = engineered_freq_start
    node0.freq_end = engineered_freq_end
    node2.freq_start = engineered_freq_start
    node2.freq_end = engineered_freq_end
    node0.covered_squares = [1]
    node2.covered_squares = [1]

    # Run metrics collector again to see the missed conflict
    metrics = MetricsCollector()
    num_interfering, interference_rate = metrics.compute_interference(assignments, env, arch_policy)
    print("\n=== Engineered Metrics After Forcing Overlap ===")
    print(f"Num_Interfering_Assignments: {num_interfering}")
    print(f"Interference_Rate: {interference_rate}")

    print("\n=== Simulation Performance Metrics ===")
    for k, v in results.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
