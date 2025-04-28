"""
Simulation configuration parameters.
"""
RANDOM_SEED = 42

# Request parameter bounds (in MHz)
MIN_BW_REQUEST = 10    # in MHz
MAX_BW_REQUEST = 100   # in MHz

# Licensing cost factors (arbitrary cost units)
COST_FACTOR_AUTO = 1.0
COST_FACTOR_MANUAL = 5.0

# Total available bandwidth (MHz)
TOTAL_BANDWIDTH_MHZ = 600

# Frequency base (MHz) – e.g., 37000 represents 37.000 GHz
FREQ_BASE_MHZ = 37000

# Licensing delays (in simulation steps, where 1 step = 1 minute)
# For manual licensing: delay between 1 day and 3 months (in minutes)
MANUAL_MIN_DELAY = 1440       # 1 day (in minutes)
MANUAL_MAX_DELAY = 129600     # 3 months (~90 days)
AUTOMATED_DELAY = 0

# Grant durations (in minutes)
SHORT_TERM_DURATION = 1      # re-evaluate every minute (automated mode)
MID_TERM_DURATION = 1440     # re-evaluate every day (automated mode)

# For manual licensing, we process requests only at daily intervals.
MANUAL_PROCESSING_INTERVAL = 1440  # 1 day

# Re-export of simulation minutes from scenarios
from config.scenarios import DEFAULT_SIM_MINUTES
LONG_TERM_DURATION = DEFAULT_SIM_MINUTES  # permanent assignment for automated mode

# Human operator parameters
HUMAN_MIN_PER_BATCH = 30      # minutes per manual batch
HUMAN_MIN_PER_REQUEST = 2     # minutes reviewer spends per request

# Channel step sizes based on frequency plan
DEFAULT_CHANNEL_STEP = {
    "Large Blocks": 200,
    "Sub Channels": 40,
    "Freq Slicing": 10
}

# Quality reduction factors for different interference mitigation strategies
QUALITY_FACTORS = {
    "Power Control": 0.8,
    "Beamforming": 0.8,
    "Frequency Hopping": 0.9,
    "Combination": 0.8
}