"""
Event-driven simulation engine for spectrum management.
"""
import heapq
from collections import namedtuple
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from config.scenarios import DEFAULT_SIM_MINUTES
from config.parameters import TOTAL_BANDWIDTH_MHZ

# Define event types with a tie-breaker counter
Event = namedtuple('Event', ['time', 'event_type', 'counter', 'payload'])
# event_type: 'ARRIVAL', 'PROCESS_MANUAL', 'RENEWAL'

class EventDrivenSimulation:
    def __init__(self, environment, architecture_policy, demand_list, sim_minutes=DEFAULT_SIM_MINUTES):
        self.environment = environment
        self.architecture_policy = architecture_policy
        self.demand_list = demand_list
        self.sim_minutes = sim_minutes
        self.metrics = MetricsCollector()
        self.spectrum_manager = SpectrumManager(environment, architecture_policy, self.metrics)
        self.results = None
        self.event_queue = []
        self.current_time = 0
        self.active_assignments = set()  # Track assignment IDs for renewal scheduling
        self._event_counter = 0  # Tie-breaker for event queue

    def schedule_event(self, event_time, event_type, payload):
        self._event_counter += 1
        heapq.heappush(self.event_queue, Event(event_time, event_type, self._event_counter, payload))

    def run(self):
        # Schedule all demand arrivals
        for req in self.demand_list:
            self.schedule_event(req.arrival_time, 'ARRIVAL', req)

        # For manual mode, assign process_time to each request
        if self.architecture_policy.licensing_mode == 'Manual':
            for req in self.demand_list:
                delay = getattr(req, 'manual_delay', None)
                if delay is None:
                    # Centralized: 30 days (43200 minutes), Hybrid: 20 days (28800), Decentralized: 10 days (14400)
                    if self.architecture_policy.coordination_mode == 'Hybrid':
                        delay = 28800  # 20 days
                    elif self.architecture_policy.coordination_mode == 'Centralized':
                        delay = 43200  # 30 days
                    else:
                        delay = 14400  # Decentralized: 10 days
                    req.manual_delay = delay
                    req.process_time = req.arrival_time + delay
                self.schedule_event(req.process_time, 'PROCESS_MANUAL', req)

        last_update_time = 0
        renewal_interval = None
        last_semi_dynamic_update = 0  # Track last time cost was updated for Semi-Dynamic
        if self.architecture_policy.licensing_mode == 'Semi-Dynamic':
            renewal_interval = 1440  # 24 hours
            last_semi_dynamic_update = 0
        # Dynamic mode: no renewal_interval, only arrival events

        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            # Update metrics for the interval since last event
            delta_t = event.time - last_update_time
            if delta_t > 0:
                if self.architecture_policy.licensing_mode == 'Dynamic':
                    n_active = len(self.spectrum_manager.active)
                    increment = n_active * delta_t
                    self.metrics.coordination_cost += increment
                    self.metrics.coord_queries += increment
                    self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)
                elif self.architecture_policy.licensing_mode == 'Semi-Dynamic':
                    n_active = len(self.spectrum_manager.active)
                    # Only increment for each full day elapsed since last update
                    days_elapsed = (event.time - last_semi_dynamic_update) // 1440
                    if days_elapsed > 0:
                        increment = n_active * days_elapsed
                        self.metrics.coordination_cost += increment
                        self.metrics.coord_queries += increment
                        last_semi_dynamic_update += days_elapsed * 1440
                    self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)
                else:
                    self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)
            last_update_time = event.time
            self.current_time = event.time
            if self.current_time > self.sim_minutes:
                break
            if event.event_type == 'ARRIVAL':
                if self.architecture_policy.licensing_mode == 'Semi-Dynamic':
                    self.spectrum_manager.process_arrivals([event.payload], self.current_time)
                    # Schedule next universal renewal at next 24h boundary if not already scheduled
                    next_renewal_time = ((self.current_time // renewal_interval) + 1) * renewal_interval
                    if next_renewal_time <= self.sim_minutes:
                        self.schedule_event(next_renewal_time, 'RENEWAL', None)
                elif self.architecture_policy.licensing_mode == 'Dynamic':
                    self.spectrum_manager.process_arrivals([event.payload], self.current_time)
                # For manual, arrivals are queued and processed at process_time
            elif event.event_type == 'PROCESS_MANUAL':
                self.spectrum_manager.process_arrivals([event.payload], self.current_time)
                # Add human minutes: each processed manual request incurs the coordination delay as human review time
                if hasattr(event.payload, 'manual_delay'):
                    self.metrics.human_minutes += event.payload.manual_delay
                else:
                    # Fallback to default if not set
                    if self.architecture_policy.coordination_mode == 'Hybrid':
                        self.metrics.human_minutes += 28800
                    elif self.architecture_policy.coordination_mode == 'Centralized':
                        self.metrics.human_minutes += 43200
                    else:
                        self.metrics.human_minutes += 14400
            elif event.event_type == 'RENEWAL':
                # Only for semi-dynamic
                if self.architecture_policy.licensing_mode == 'Semi-Dynamic':
                    self.spectrum_manager.renew_assignments(self.current_time)
                    # Schedule next renewal if there are still active assignments
                    if renewal_interval is not None:
                        next_renewal_time = self.current_time + renewal_interval
                        if next_renewal_time <= self.sim_minutes:
                            self.schedule_event(next_renewal_time, 'RENEWAL', None)

        # Final update for any remaining time until sim_minutes
        if last_update_time < self.sim_minutes:
            delta_t = self.sim_minutes - last_update_time
            if self.architecture_policy.licensing_mode == 'Dynamic':
                n_active = len(self.spectrum_manager.active)
                increment = n_active * delta_t
                self.metrics.coordination_cost += increment
                self.metrics.coord_queries += increment
                self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)
            elif self.architecture_policy.licensing_mode == 'Semi-Dynamic':
                n_active = len(self.spectrum_manager.active)
                # Only increment for each full day elapsed since last update
                days_elapsed = (self.sim_minutes - last_semi_dynamic_update) // 1440
                if days_elapsed > 0:
                    increment = n_active * days_elapsed
                    self.metrics.coordination_cost += increment
                    self.metrics.coord_queries += increment
                    last_semi_dynamic_update += days_elapsed * 1440
                self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)
            else:
                self.metrics.update_usage(self.spectrum_manager.active, self.environment, delta_t)

        # After all events processed, compute metrics with final active assignments
        # Ensure we pass only real Assignment objects with assignment_id and freq info
        real_assignments = [a for a in self.spectrum_manager.active if hasattr(a, 'assignment_id') and a.assignment_id is not None and hasattr(a, 'freq_start') and a.freq_start is not None]
        if len(real_assignments) == 0:
            print("[WARNING] No real assignments with IDs and frequencies found in self.spectrum_manager.active. Using all assignments as fallback.")
            real_assignments = self.spectrum_manager.active
        total_band_mhz = TOTAL_BANDWIDTH_MHZ
        total_area_km2 = self.environment.num_squares if hasattr(self.environment, 'num_squares') else 1
        sim_minutes = self.sim_minutes
        final_active_assignments = real_assignments
        self.results = self.metrics.final_report(
            total_band_mhz,
            total_area_km2,
            sim_minutes,
            final_active_assignments=final_active_assignments,
            environment=self.environment,
            arch_policy=self.architecture_policy,
            mitigated_conflicts=getattr(self.spectrum_manager, "mitigated_conflicts", None)
        )
        self.results.update({
            "architecture_id": f"{self.architecture_policy.coordination_mode}-{self.architecture_policy.licensing_mode}-{self.architecture_policy.freq_plan}",
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
        import os, csv
        if self.results is None:
            raise ValueError("No results to save. Run simulation first.")
        self.results["scenario"] = scenario_key
        os.makedirs(results_dir, exist_ok=True)
        csv_path = os.path.join(results_dir, "simulation_results_event.csv")
        file_exists = os.path.isfile(csv_path)
        with open(csv_path, 'a', newline='') as csvfile:
            fieldnames = list(self.results.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(self.results)
