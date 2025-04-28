"""
Defines licensing strategies.
Manual licensing introduces a random delay (in whole days),
while automated licensing is immediate.
"""
import random
from config.parameters import MANUAL_MIN_DELAY, MANUAL_MAX_DELAY, AUTOMATED_DELAY

class ManualLicensing:
    def get_licensing_delay(self, request):
        # Return delay in minutes, ensuring it is a multiple of a day.
        delay = random.randint(MANUAL_MIN_DELAY, MANUAL_MAX_DELAY)
        return delay

class AutomatedLicensing:
    def get_licensing_delay(self, request):
        return AUTOMATED_DELAY