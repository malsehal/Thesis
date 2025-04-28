"""
Simulation scenarios configuration.
Defines three deterministic demand scenarios with varying arrival patterns.
"""
from typing import Dict, List, Tuple, Mapping
from collections import namedtuple
from types import MappingProxyType

# Constants
_MIN_PER_DAY = 1440
_SIM_MINUTES = 180 * _MIN_PER_DAY  # 6-month horizon
DEFAULT_SIM_MINUTES = _SIM_MINUTES

# Scenario definition type
Scenario = namedtuple('Scenario', [
    'arrival_minutes',  # List of minutes when requests arrive
    'device_dist',      # Distribution of device types (device_type, probability)
    'bw_dist'           # Bandwidth distribution per device type {device_type: [(bw, probability)]}
])

# Scenario definitions
_scenarios = {
    "low": Scenario(
        arrival_minutes=list(range(0, _SIM_MINUTES, (_MIN_PER_DAY * 7) // 2)),  # 2 users per week (every 3.5 days)
        device_dist=[("5G", 0.5), ("IoT", 0.35), ("Federal", 0.15)],
        bw_dist={
            "5G": [(100, 0.6), (200, 0.4)],
            "IoT": [(20, 0.7), (40, 0.3)],
            "Federal": [(40, 0.5), (100, 0.5)]
        }
    ),
    "medium": Scenario(
        arrival_minutes=list(range(0, _SIM_MINUTES, _MIN_PER_DAY)),  # 1 user per day
        device_dist=[("5G", 0.5), ("IoT", 0.35), ("Federal", 0.15)],
        bw_dist={
            "5G": [(100, 0.6), (200, 0.4)],
            "IoT": [(20, 0.7), (40, 0.3)],
            "Federal": [(40, 0.5), (100, 0.5)]
        }
    ),
    "high": Scenario(
        arrival_minutes=list(range(0, _SIM_MINUTES, _MIN_PER_DAY // 2)),  # 2 users per day (every 12 hours)
        device_dist=[("5G", 0.5), ("IoT", 0.35), ("Federal", 0.15)],
        bw_dist={
            "5G": [(100, 0.6), (200, 0.4)],
            "IoT": [(20, 0.7), (40, 0.3)],
            "Federal": [(40, 0.5), (100, 0.5)]
        }
    )
}

# Create an immutable mapping for the scenarios
SCENARIOS = MappingProxyType(_scenarios)
