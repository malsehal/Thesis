"""
Test the Exclusive partition mode functionality.
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
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ

class TestExclusivePartition(unittest.TestCase):
    def setUp(self):
        # Create a simple environment
        self.env = Environment(squares_rows=1, squares_cols=1)
        
        # Create an architecture with Exclusive mode
        self.arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Manual",
            freq_plan="Large Blocks",
            interference="No Mitigation",
            sensing="Database Only",
            pricing="No Cost",
            enforcement="Active",
            priority="Exclusive"
        )
        
        # Create metrics collector
        self.metrics = MetricsCollector()
        
        # Create spectrum manager
        self.manager = SpectrumManager(self.env, self.arch, self.metrics)
        
        # Define expected partitions (each 200 MHz in a 600 MHz band)
        third = TOTAL_BANDWIDTH_MHZ // 3
        self.partitions = {
            "5G": (FREQ_BASE_MHZ, FREQ_BASE_MHZ + third),
            "IoT": (FREQ_BASE_MHZ + third, FREQ_BASE_MHZ + 2 * third),
            "Federal": (FREQ_BASE_MHZ + 2 * third, FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ)
        }
    
    def test_exclusive_partition_assignments(self):
        """Test that assignments stay within their respective partitions."""
        # Create one request for each device type
        requests = [
            SpectrumRequest(0, 0, 0, 100, "5G"),
            SpectrumRequest(1, 0, 0, 100, "IoT"),
            SpectrumRequest(2, 0, 0, 100, "Federal")
        ]
        
        # Process the requests
        self.manager.process_arrivals(requests, 0)
        
        # Verify that assignments were made
        self.assertEqual(len(self.manager.active), 3, "Should have 3 active assignments")
        
        # Check that each assignment is in the correct partition
        for assignment in self.manager.active:
            partition_start, partition_end = self.partitions[assignment.device_type]
            
            self.assertGreaterEqual(
                assignment.freq_start, 
                partition_start, 
                f"{assignment.device_type} assignment starts outside its partition"
            )
            
            self.assertLessEqual(
                assignment.freq_end, 
                partition_end, 
                f"{assignment.device_type} assignment ends outside its partition"
            )
    
    def test_partition_separation(self):
        """Test that assignments from different device types don't overlap in frequency."""
        # Create requests with maximum bandwidth for each device type
        requests = [
            SpectrumRequest(0, 0, 0, 200, "5G"),
            SpectrumRequest(1, 0, 0, 200, "IoT"),
            SpectrumRequest(2, 0, 0, 200, "Federal")
        ]
        
        # Process the requests
        self.manager.process_arrivals(requests, 0)
        
        # Verify that assignments were made
        self.assertEqual(len(self.manager.active), 3, "Should have 3 active assignments")
        
        # Get assignments by device type
        assignments_by_type = {}
        for assignment in self.manager.active:
            assignments_by_type[assignment.device_type] = assignment
        
        # Check that assignments from different device types don't overlap
        for type1, assignment1 in assignments_by_type.items():
            for type2, assignment2 in assignments_by_type.items():
                if type1 != type2:
                    self.assertTrue(
                        assignment1.freq_end <= assignment2.freq_start or
                        assignment1.freq_start >= assignment2.freq_end,
                        f"Assignment for {type1} overlaps with assignment for {type2}"
                    )

if __name__ == '__main__':
    unittest.main()
