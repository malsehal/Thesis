#!/usr/bin/env python3
"""
controllers/manual_fcfs_simulator.py

This module implements a Manual First-Come-First-Serve (FCFS) licensing simulator
that incorporates frequency allocation, node coverage/conflict rules, and interference mitigation.

It processes pre‑generated demand requests (SpectrumRequest objects) based on a manual coordination delay.
Each request is assigned a random delay (in minutes) between MANUAL_MIN_DELAY and MANUAL_MAX_DELAY.
The request’s processing time is computed as:
    process_time = arrival_time + manual_delay

At the request’s process time (if not already processed), the simulator:
  1. Retrieves the request's node and its covered squares.
  2. Aggregates active assignments (with associated nodes) from all nodes that share at least one square.
  3. Uses the frequency allocator (passing the active assignments) to try to obtain a candidate frequency block.
         - If a candidate block is obtained (i.e. conflict‑free), it is immediately assigned and the request is granted.
  4. Otherwise, iterates over the active assignments: for each active assignment whose bandwidth is at least the incoming request's requested bandwidth,
         attempts interference mitigation between the incoming request and that active assignment.
         - If mitigation succeeds (i.e. the candidate block is “saved”), that block is used; if the active assignment is terminated by mitigation,
           a log entry is recorded.
         - The loop breaks upon the first successful mitigation.
  5. If no candidate block is saved via mitigation, the request is rejected.
  6. Otherwise, the accepted candidate block is assigned to the request and the request is added to its node's active assignments.

Even though the overall simulation runs minute‑by‑minute (SIMULATION_STEPS),
the manual processing is conceptually “daily” (i.e. delay values are whole days in minutes).

Configuration parameters used:
    SIMULATION_STEPS, MANUAL_MIN_DELAY, MANUAL_MAX_DELAY, FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ (from config.parameters)
    Frequency allocation is obtained via strategies.frequency_allocation.
    Interference mitigation is handled by strategies.interference_mitigation.
"""

import random
from config.parameters import SIMULATION_STEPS, MANUAL_MIN_DELAY, MANUAL_MAX_DELAY
from strategies.frequency_allocation import get_frequency_allocator
from strategies.interference_mitigation import mitigate_conflict

def assign_manual_delay(requests):
    """
    For each SpectrumRequest in the list, assign:
      - a random manual delay (in minutes) between MANUAL_MIN_DELAY and MANUAL_MAX_DELAY,
      - a process_time equal to arrival_time + manual_delay,
      - mark it as not yet processed.
    """
    for req in requests:
        delay = random.randint(MANUAL_MIN_DELAY, MANUAL_MAX_DELAY)
        req.manual_delay = delay
        req.process_time = req.arrival_time + delay
        req.processed = False

def run_manual_fcfs_simulation(requests, arch_policy, environment, simulation_end=SIMULATION_STEPS):
    """
    Runs the manual FCFS simulation from time t = 0 to simulation_end (in minutes).

    For each unprocessed request whose process_time equals t:
      1. Retrieve the request's node and its covered squares.
      2. Aggregate active assignments (with associated nodes) from all nodes that share at least one square.
      3. Use the frequency allocator (passing the active assignments) to try to obtain a candidate frequency block.
         - If a candidate block is obtained (i.e. conflict‑free), assign it immediately and grant the request.
      4. Otherwise, for each active assignment whose allocated bandwidth is at least the incoming request's requested bandwidth,
         attempt interference mitigation between the incoming request and that active assignment.
            - If mitigation succeeds, use that active assignment's frequency block as the candidate block.
            - If that active assignment was terminated due to mitigation, log that event.
            - Break out of the loop upon the first successful mitigation.
      5. If no candidate block is saved via mitigation, reject the request.
      6. If a candidate block is finally accepted, assign it to the request and add the request to its node's active assignments.

    Returns a list of log events describing each processing decision.
    """
    freq_allocator = get_frequency_allocator(arch_policy.freq_plan)
    log_events = []

    # Process each time step.
    for t in range(simulation_end):
        for req in requests:
            if not req.processed and req.process_time == t:
                # (1) Retrieve the request's node and its covered squares.
                req_node = environment.nodes[req.node_id]
                req_squares = set(req_node.covered_squares)

                # (2) Aggregate active assignments from all nodes that share at least one square.
                active_assignments = []
                for node in environment.nodes:
                    if req_squares.intersection(set(node.covered_squares)):
                        for assignment in node.active_assignments:
                            if hasattr(assignment, "freq_start") and hasattr(assignment, "freq_end"):
                                if getattr(assignment, "terminated", False):
                                    continue
                                active_assignments.append((node, assignment))

                # (3) Use the frequency allocator to try to obtain a candidate frequency block.
                candidate = freq_allocator.find_allocation([a for (n, a) in active_assignments],
                                                           req.requested_bw, arch_policy)
                if candidate is not None:
                    # Allocator found a conflict-free candidate; assign it immediately.
                    req.freq_allocation = candidate
                    req.freq_start, req.freq_end = candidate
                    req.processed = True
                    req.result = "granted"
                    req_node.active_assignments.append(req)
                    log_events.append(
                        f"Time {t}: Request {req.req_id} (arrival {req.arrival_time}, delay {req.manual_delay}) for node {req.node_id} GRANTED with frequency allocation {req.freq_allocation} (via allocator)."
                    )
                    continue

                # (4) No candidate from the allocator; iterate through active assignments for mitigation.
                mitigation_success = False
                candidate = None
                for (node, assignment) in active_assignments:
                    # Check if the active assignment's allocated bandwidth is at least the incoming request's requested bandwidth.
                    if (assignment.freq_end - assignment.freq_start) >= req.requested_bw:
                        # Attempt interference mitigation with this overlapping active assignment.
                        if mitigate_conflict(req_node, req, node, assignment, arch_policy):
                            mitigation_success = True
                            # Use the active assignment's (possibly adjusted) frequency block as the candidate.
                            candidate = (assignment.freq_start, assignment.freq_end)
                            # Log if the active assignment was terminated.
                            if getattr(assignment, "terminated", False):
                                log_events.append(
                                    f"Time {t}: Active assignment from request {assignment.req_id} on node {node.node_id} TERMINATED due to interference mitigation."
                                )
                            log_events.append(
                                f"Time {t}: Candidate block {candidate} saved via mitigation for Request {req.req_id}."
                            )
                            break

                if not mitigation_success:
                    req.processed = True
                    req.result = "rejected"
                    req.reject_reason = "No available frequency allocation after mitigation"
                    log_events.append(
                        f"Time {t}: Request {req.req_id} (arrival {req.arrival_time}, delay {req.manual_delay}) for node {req.node_id} REJECTED (reason: {req.reject_reason})."
                    )
                    continue

                # (6) Finalize assignment from mitigation.
                req.freq_allocation = candidate
                req.freq_start, req.freq_end = candidate
                req.processed = True
                req.result = "granted"
                req_node.active_assignments.append(req)
                log_events.append(
                    f"Time {t}: Request {req.req_id} (arrival {req.arrival_time}, delay {req.manual_delay}) for node {req.node_id} GRANTED with frequency allocation {req.freq_allocation} (after mitigation)."
                )
    return log_events