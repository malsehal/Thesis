#!/usr/bin/env python3
"""
morphology/architecture_enumerator.py

Generates and filters architectural decision combinations for the simulation
based on the updated morphological matrix.

The eight decision dimensions are:
  1. Coordination Topology: "Centralized", "Decentralized", "Hybrid"
  2. Licensing Mechanism: "Manual", "Semi-Dynamic", "Dynamic"
  3. Frequency Allocation Plan: "Large Blocks", "Sub Channels", "Freq Slicing"
  4. Interference Mitigation: "No Mitigation", "Power Control", "Beamforming", "Combination"
  5. Sensing: "Device Based", "Infrastructure Sensors", "Database Only"
  6. Pricing: "No Cost", "Usage Based", "Auction Based"
  7. Enforcement: "Active", "Passive"
  8. Access Priority: "Hierarchical", "Co-Primary", "Exclusive"
"""

import itertools

# Define the allowed options for each decision dimension.
COORDINATION_MODES = ["Centralized", "Decentralized", "Hybrid"]
LICENSING_MODES = ["Manual", "Semi-Dynamic", "Dynamic"]
FREQ_PLANS = ["Large Blocks", "Sub Channels", "Freq Slicing"]
INTERFERENCE_MITIGATIONS = ["No Mitigation", "Power Control", "Beamforming", "Combination"]
SENSING_MODES = ["Device Based", "Infrastructure Sensors", "Database Only"]
PRICING_MODES = ["No Cost", "Usage Based", "Auction Based"]
ENFORCEMENT_MODES = ["Active", "Passive"]
PRIORITY_MODES = ["Hierarchical", "Co-Primary", "Exclusive"]

def generate_all_architectures(apply_filter=True):
    """
    Generates all combinations of architectural decisions based on the eight-dimensional matrix.
    If apply_filter is True, infeasible combinations (as defined by the filtering rules) are removed.
    Returns a list of ArchitecturePolicy instances.
    """
    all_architectures = []
    # Generate combinations across all eight dimensions
    for combo in itertools.product(COORDINATION_MODES,
                                   LICENSING_MODES,
                                   FREQ_PLANS,
                                   INTERFERENCE_MITIGATIONS,
                                   SENSING_MODES,
                                   PRICING_MODES,
                                   ENFORCEMENT_MODES,
                                   PRIORITY_MODES):
        arch = ArchitecturePolicy(coordination_mode=combo[0],
                                  licensing_mode=combo[1],
                                  freq_plan=combo[2],
                                  interference_mitigation=combo[3],
                                  sensing_mode=combo[4],
                                  pricing_mode=combo[5],
                                  enforcement_mode=combo[6],
                                  priority_mode=combo[7])
        if apply_filter:
            if is_feasible(arch):
                all_architectures.append(arch)
        else:
            all_architectures.append(arch)
    return all_architectures

def is_feasible(arch):
    """
    Returns True if the given architecture combination is feasible.
    Filtering rules:
      1. Dynamic licensing may not be used with Database Only sensing.
      2. Dynamic licensing may not be paired with Auction Based pricing.
      3. Decentralized coordination may not be paired with Auction Based pricing.
      4. If priority is Exclusive, licensing must be Manual and coordination must be Centralized; otherwise that combo is infeasible.
      5. Dynamic licensing may not be paired with Passive enforcement.
    """
    # Rule 1: Dynamic licensing may not be used with Database Only sensing.
    if arch.licensing_mode == "Dynamic" and arch.sensing_mode == "Database Only":
        return False
    
    # Rule 2: Dynamic licensing may not be paired with Auction Based pricing.
    if arch.licensing_mode == "Dynamic" and arch.pricing_mode == "Auction Based":
        return False
    
    # Rule 3: Decentralized coordination may not be paired with Auction Based pricing.
    if arch.coordination_mode == "Decentralized" and arch.pricing_mode == "Auction Based":
        return False
    
    # Rule 4: If priority is Exclusive, licensing must be Manual and coordination must be Centralized; otherwise that combo is infeasible.
    if arch.priority_mode == "Exclusive" and (arch.licensing_mode != "Manual" or arch.coordination_mode != "Centralized"):
        return False
    
    # Rule 5: Dynamic licensing may not be paired with Passive enforcement.
    if arch.licensing_mode == "Dynamic" and arch.enforcement_mode == "Passive":
        return False
    
    return True

def get_architecture_by_name(coord_mode, licensing, freq_plan, interference, sensing, pricing, enforcement, priority):
    """
    Manually constructs an ArchitecturePolicy from the given parameters.
    Raises ValueError if the architecture is infeasible.
    """
    # Create the architecture
    arch = ArchitecturePolicy(coordination_mode=coord_mode,
                             licensing_mode=licensing,
                             freq_plan=freq_plan,
                             interference_mitigation=interference,
                             sensing_mode=sensing,
                             pricing_mode=pricing,
                             enforcement_mode=enforcement,
                             priority_mode=priority)
    
    # Check if the architecture is feasible
    if not is_feasible(arch):
        raise ValueError(f"Infeasible architecture combination: {arch}")
        
    return arch

class ArchitecturePolicy:
    def __init__(self, coordination_mode, licensing_mode, freq_plan, interference_mitigation, 
                 sensing_mode, pricing_mode, enforcement_mode, priority_mode):
        self.coordination_mode = coordination_mode             # "Centralized", "Decentralized", "Hybrid"
        self.licensing_mode = licensing_mode                   # "Manual", "Semi-Dynamic", "Dynamic"
        self.freq_plan = freq_plan                             # "Large Blocks", "Sub Channels", "Freq Slicing"
        self.interference_mitigation = interference_mitigation # "No Mitigation", "Power Control", "Beamforming", "Combination"
        self.sensing_mode = sensing_mode                       # "Device Based", "Infrastructure Sensors", "Database Only"
        self.pricing_mode = pricing_mode                       # "No Cost", "Usage Based", "Auction Based"
        self.enforcement_mode = enforcement_mode               # "Active", "Passive"
        self.priority_mode = priority_mode                     # "Hierarchical", "Co-Primary", "Exclusive"

    def __repr__(self):
        return (f"<ArchitecturePolicy coord={self.coordination_mode}, lic={self.licensing_mode}, "
                f"freq={self.freq_plan}, int_mitg={self.interference_mitigation}, "
                f"sensing={self.sensing_mode}, pricing={self.pricing_mode}, "
                f"enforce={self.enforcement_mode}, prio={self.priority_mode}>")