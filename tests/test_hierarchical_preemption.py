"""
Test the Hierarchical priority preemption functionality.
"""
import unittest
import sys
import os
# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.environment import Environment
from models.request import SpectrumRequest
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from morphology.architecture_enumerator import get_architecture_by_name

class TestHierarchicalPreemption(unittest.TestCase):
    def setUp(self):
        # Create a simple environment
        self.env = Environment(squares_rows=1, squares_cols=1)
        
        # Create an architecture with Hierarchical priority and Dynamic licensing
        self.arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="No Mitigation",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Hierarchical"
        )
        
        # Create metrics collector
        self.metrics = MetricsCollector()
        
        # Create spectrum manager
        self.manager = SpectrumManager(self.env, self.arch, self.metrics)
    
    def test_federal_preempts_5g(self):
        """Test that Federal request preempts a 5G assignment when they conflict."""
        # Create a 5G request first
        five_g_request = SpectrumRequest(0, 0, 0, 100, "5G")
        self.manager.process_arrivals([five_g_request], 0)
        
        # Verify 5G assignment was made
        self.assertEqual(len(self.manager.active), 1, "Should have 1 active assignment")
        five_g_assignment = self.manager.active[0]
        self.assertEqual(five_g_assignment.device_type, "5G", "Should be a 5G assignment")
        
        # Record frequency range of 5G assignment
        freq_start = five_g_assignment.freq_start
        freq_end = five_g_assignment.freq_end
        
        # Create a Federal request that overlaps with the 5G assignment
        federal_request = SpectrumRequest(1, 1, 0, 100, "Federal")
        federal_request.desired_frequency = (freq_start, freq_end)
        federal_request.freq_start = freq_start
        federal_request.freq_end = freq_end
        
        # Process the Federal request
        self.manager.process_arrivals([federal_request], 1)
        
        # Check next tick housekeeping (should trigger review of 5G assignment)
        self.manager.tick_housekeeping(1)
        
        # Expect Federal to be assigned and 5G to be revoked or hopped
        federal_count = 0
        five_g_count = 0
        
        for assignment in self.manager.active:
            if assignment.device_type == "Federal":
                federal_count += 1
            elif assignment.device_type == "5G":
                five_g_count += 1
        
        # Verify Federal assignment is present
        self.assertEqual(federal_count, 1, "Should have 1 Federal assignment")
        
        # 5G should either be revoked or hopped to a different frequency
        if five_g_count == 1:
            # Find the 5G assignment
            for assignment in self.manager.active:
                if assignment.device_type == "5G":
                    # Verify it's not in the same frequency range
                    self.assertTrue(
                        assignment.freq_end <= freq_start or assignment.freq_start >= freq_end,
                        "5G assignment should have hopped to a non-conflicting frequency"
                    )
        else:
            # 5G assignment was revoked
            self.assertEqual(five_g_count, 0, "5G assignment should have been revoked")
    
    def test_priority_tiers(self):
        """Test that priority tiers are assigned correctly."""
        # Create requests of different types
        requests = [
            SpectrumRequest(0, 0, 0, 40, "Federal"),
            SpectrumRequest(1, 0, 0, 40, "5G"),
            SpectrumRequest(2, 0, 0, 40, "IoT")
        ]
        
        # Process the requests
        self.manager.process_arrivals(requests, 0)
        
        # Verify that assignments were made with correct priority tiers
        for assignment in self.manager.active:
            if assignment.device_type == "Federal":
                self.assertEqual(assignment.priority_tier, 0, "Federal should have priority tier 0 (highest)")
            elif assignment.device_type == "5G":
                self.assertEqual(assignment.priority_tier, 1, "5G should have priority tier 1")
            elif assignment.device_type == "IoT":
                self.assertEqual(assignment.priority_tier, 2, "IoT should have priority tier 2")

if __name__ == '__main__':
    unittest.main()
