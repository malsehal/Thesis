"""
Test the Semi-Dynamic licensing mode queue and coordination cost.
"""
import unittest
from models.environment import Environment
from models.request import SpectrumRequest
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from core.simulation import Simulation
from morphology.architecture_enumerator import get_architecture_by_name

class TestSemiDynamicQueueCost(unittest.TestCase):
    def setUp(self):
        # Create a simple environment
        self.env = Environment(squares_rows=1, squares_cols=1)
        
        # Create an architecture with Semi-Dynamic licensing and Centralized coordination
        self.arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Semi-Dynamic",
            freq_plan="Sub Channels",
            interference="No Mitigation",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create metrics collector
        self.metrics = MetricsCollector()
        
        # Create spectrum manager
        self.manager = SpectrumManager(self.env, self.arch, self.metrics)
    
    def test_coordination_cost_at_daily_intervals(self):
        """Test that coordination cost increases only at 24-hour intervals for Semi-Dynamic mode."""
        # Create some requests
        requests = [
            SpectrumRequest(0, 0, 0, 40, "5G"),
            SpectrumRequest(1, 1, 0, 40, "IoT"),
            SpectrumRequest(2, 1440, 0, 40, "Federal")  # Request at day 1
        ]
        
        # Process initial requests (day 0)
        self.manager.process_arrivals(requests[:2], 0)
        initial_coord_cost = self.metrics.coord_queries
        
        # Verify cost was incurred for initial grants
        self.assertGreater(initial_coord_cost, 0, "Should have initial coordination cost")
        
        # Simulate ticks without renewal (should not increase cost)
        for tick in range(1, 1439):
            self.manager.tick_housekeeping(tick)
        
        # Check that cost hasn't increased
        self.assertEqual(self.metrics.coord_queries, initial_coord_cost, 
                         "Coordination cost should not increase before renewal interval")
        
        # Process tick 1440 (day 1) - should trigger renewals and increase cost
        self.manager.process_arrivals([requests[2]], 1440)
        self.manager.tick_housekeeping(1440)
        
        # Verify cost increased due to renewals
        self.assertGreater(self.metrics.coord_queries, initial_coord_cost, 
                           "Coordination cost should increase at daily renewal interval")
    
    def test_renewal_intervals(self):
        """Test that assignments are renewed at the correct intervals."""
        # Create a request at time 0
        request = SpectrumRequest(0, 0, 0, 40, "5G")
        self.manager.process_arrivals([request], 0)
        
        # Verify assignment was made
        self.assertEqual(len(self.manager.active), 1, "Should have 1 active assignment")
        assignment = self.manager.active[0]
        
        # Semi-Dynamic should set next_check_tick to day 1 (1440)
        self.assertEqual(assignment.next_check_tick, 1440, 
                         "Assignment should be renewed at day 1")
        
        # Simulate until just before renewal
        for tick in range(1, 1440):
            self.manager.tick_housekeeping(tick)
            # Check that next_check_tick hasn't changed
            self.assertEqual(assignment.next_check_tick, 1440,
                            "Assignment next_check_tick should not change before renewal")
        
        # Simulate renewal tick
        self.manager.tick_housekeeping(1440)
        
        # Verify that next_check_tick has been updated to day 2
        self.assertEqual(assignment.next_check_tick, 2880, 
                         "Assignment should be scheduled for renewal at day 2")

if __name__ == '__main__':
    unittest.main()
