#!/usr/bin/env python3
"""
Interference Mitigation Module
Implements interference mitigation strategies.
Interference is defined as overlapping active assignments in the same square.
Mitigation considers geometry (diagonal vs adjacent) and access priority.
"""

import random
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ

def is_diagonal(node1, node2):
    return abs(node1.row - node2.row) == 1 and abs(node1.col - node2.col) == 1

def _get_priority(device_type, priority_mode):
    """
    Returns a numeric priority based on the device type.
    For Hierarchical mode, assume:
      - "5G" has higher priority (value 2) than "IoT" (value 1).
    For Co-Primary, both are equal (value 1).
    """
    if priority_mode == "Hierarchical":
        return 2 if device_type == "5G" else 1
    else:
        return 1

def mitigate_conflict(incoming_node, incoming_assignment, existing_node, existing_assignment, arch_policy):
    """
    Attempts to mitigate a conflict between two overlapping assignments.
    
    Returns True if mitigation was successfully applied, False otherwise.
    
    "Termination" is represented by setting assignment.terminated = True.
    """
    option = arch_policy.interference_mitigation
    # print(incoming_assignment.freq_end)
    # print(existing_assignment.freq_end)

    # Determine priorities.
    incoming_priority = _get_priority(incoming_assignment.device_type, arch_policy.priority_mode)
    existing_priority = _get_priority(existing_assignment.device_type, arch_policy.priority_mode)
    diagonal = is_diagonal(incoming_node, existing_node)

    # Determine which assignment (if any) is higher priority.
    if incoming_priority > existing_priority:
        higher_assignment, lower_assignment = incoming_assignment, existing_assignment
        higher_node, lower_node = incoming_node, existing_node
    elif incoming_priority < existing_priority:
        higher_assignment, lower_assignment = existing_assignment, incoming_assignment
        higher_node, lower_node = existing_node, incoming_node
    else:
        higher_assignment = None  # Equal priority.
        lower_assignment = None

    # --- Power Control ---
    if option == "Power_Control":
        if diagonal:
            if higher_assignment is not None:
                # Lower priority assignment is terminated.
                lower_assignment.terminated = True
                return True
            else:
                # Equal priority: both reduce power.
                incoming_assignment.power_reduced = True
                existing_assignment.power_reduced = True
                incoming_assignment.quality = 0.5
                existing_assignment.quality = 0.5
                return True
        else:
            return False

    # --- Beamforming ---
    elif option == "Beamforming":
        if diagonal:
            if higher_assignment is not None:
                # Lower priority assignment is terminated.
                lower_assignment.terminated = True
                return True
            else:
                # Equal priority: both beamform.
                incoming_assignment.sector = 1
                existing_assignment.sector = 1
                incoming_assignment.quality = 0.8
                existing_assignment.quality = 0.8
                return True
        else:
            return False

    # --- Combination ---
    elif option == "Combination":
        if higher_assignment is not None:
            # Lower priority assignment must frequency hop.
            return False
        else:
            # Equal priority.
            if diagonal:
                # Randomly choose between power control and beamforming for both.
                if random.choice([True, False]):
                    incoming_assignment.power_reduced = True
                    existing_assignment.power_reduced = True
                    incoming_assignment.quality = 0.5
                    existing_assignment.quality = 0.5
                else:
                    incoming_assignment.sector = 1
                    existing_assignment.sector = 1
                    incoming_assignment.quality = 0.8
                    existing_assignment.quality = 0.8
                return True
            else:
                # Not diagonal: apply both power control and beamforming.
                incoming_assignment.power_reduced = True
                existing_assignment.power_reduced = True
                incoming_assignment.sector = 1
                existing_assignment.sector = 1
                incoming_assignment.quality = 0.65
                existing_assignment.quality = 0.65
                return True

    # --- No Mitigation ---
    elif option == "No_Mitigation":
        if higher_assignment is not None:
            lower_assignment.terminated = True
            return True
        else:
            # Equal priority: reject the incoming assignment.
            return False

    return False