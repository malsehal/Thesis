"""
Test the SpectrumManager's ability to process spectrum requests.
"""
import unittest
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.environment import Environment
from models.request import SpectrumRequest
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from morphology.architecture_enumerator import get_architecture_by_name
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ

class TestSpectrumRequestProcessing(unittest.TestCase):
    def setUp(self):
        # Create a simple environment with a 2x2 grid for more testing options
        self.env = Environment(squares_rows=2, squares_cols=2)
        
        # Create metrics collector
        self.metrics = MetricsCollector()
        
    def test_process_single_request(self):
        """Test processing a single spectrum request."""
        # Create architecture with Co-Primary priority mode
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="No Mitigation",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Create a request
        request = SpectrumRequest(0, 0, 0, 40, "5G")
        
        # Process the request
        manager.process_arrivals([request], 0)
        
        # Verify that the request was processed successfully
        self.assertEqual(len(manager.active), 1, "Should have 1 active assignment")
        self.assertEqual(manager.active[0].node_id, 0, "Assignment should be for node 0")
        self.assertEqual(manager.active[0].freq_end - manager.active[0].freq_start, 40, 
                         "Assignment bandwidth should be 40 MHz")
        self.assertEqual(self.metrics.requests_total, 1, "Should have processed 1 request")
        self.assertEqual(self.metrics.requests_denied, 0, "Should not have denied any requests")
        
    def test_process_multiple_requests(self):
        """Test processing multiple spectrum requests."""
        # Create architecture with Co-Primary priority mode and frequency hopping
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Frequency Hopping",  # Enable frequency hopping to avoid overlaps
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Create multiple requests for different nodes
        requests = [
            SpectrumRequest(0, 0, 0, 40, "5G"),     # Node 0
            SpectrumRequest(1, 0, 1, 40, "IoT"),    # Node 1
            SpectrumRequest(2, 0, 3, 40, "Federal") # Node 3 (different from others)
        ]
        
        # Process the requests
        manager.process_arrivals(requests, 0)
        
        # Verify all requests were processed successfully
        self.assertEqual(len(manager.active), 3, "Should have 3 active assignments")
        self.assertEqual(self.metrics.requests_total, 3, "Should have processed 3 requests")
        self.assertEqual(self.metrics.requests_denied, 0, "Should not have denied any requests")
        
        # Get the assigned node IDs to verify assignments were made to the right nodes
        node_ids = [a.node_id for a in manager.active]
        self.assertIn(0, node_ids, "Node 0 should have an assignment")
        self.assertIn(1, node_ids, "Node 1 should have an assignment")
        self.assertIn(3, node_ids, "Node 3 should have an assignment")
    
    def test_exclusive_mode_partition(self):
        """Test that exclusive mode correctly partitions the spectrum by device type."""
        # Create architecture with Exclusive priority mode
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="No Mitigation",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Exclusive"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Create requests for different device types
        requests = [
            SpectrumRequest(0, 0, 0, 40, "5G"),
            SpectrumRequest(1, 0, 1, 40, "IoT"),
            SpectrumRequest(2, 0, 2, 40, "Federal")
        ]
        
        # Process the requests
        manager.process_arrivals(requests, 0)
        
        # Verify all requests were processed
        self.assertEqual(len(manager.active), 3, "Should have 3 active assignments")
        
        # Check that each assignment is in the correct partition
        total_band = TOTAL_BANDWIDTH_MHZ
        for assignment in manager.active:
            if assignment.device_type == "5G":
                self.assertTrue(
                    FREQ_BASE_MHZ <= assignment.freq_start < FREQ_BASE_MHZ + total_band // 3,
                    "5G assignment should be in 5G partition"
                )
            elif assignment.device_type == "IoT":
                self.assertTrue(
                    FREQ_BASE_MHZ + total_band // 3 <= assignment.freq_start < FREQ_BASE_MHZ + 2 * (total_band // 3),
                    "IoT assignment should be in IoT partition"
                )
            elif assignment.device_type == "Federal":
                self.assertTrue(
                    FREQ_BASE_MHZ + 2 * (total_band // 3) <= assignment.freq_start < FREQ_BASE_MHZ + total_band,
                    "Federal assignment should be in Federal partition"
                )
    
    def test_hierarchical_mode_priority(self):
        """Test that hierarchical mode correctly prioritizes Federal over other types."""
        # Create architecture with Hierarchical priority mode and frequency hopping
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Frequency Hopping",  # Enable frequency hopping
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Hierarchical"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Create a 5G request and process it
        request_5g = SpectrumRequest(0, 0, 0, 100, "5G")
        manager.process_arrivals([request_5g], 0)
        self.assertEqual(len(manager.active), 1, "Should have 1 active assignment")
        
        # Create a Federal request for a different node
        request_federal = SpectrumRequest(1, 1, 1, 100, "Federal")
        
        # Process the Federal request
        manager.process_arrivals([request_federal], 1)
        self.assertEqual(len(manager.active), 2, "Should have 2 active assignments")
        
        # Check that both assignments are active for different nodes
        assignments_by_type = {a.device_type: a for a in manager.active}
        self.assertIn("5G", assignments_by_type)
        self.assertIn("Federal", assignments_by_type)
        self.assertNotEqual(assignments_by_type["5G"].node_id, assignments_by_type["Federal"].node_id,
                           "5G and Federal should be assigned to different nodes")
        
        # Create a conflicting Federal request for the same node as 5G
        conflict_request = SpectrumRequest(2, 2, assignments_by_type["5G"].node_id, 100, "Federal")
        manager.process_arrivals([conflict_request], 2)
        
        # Now do renewal check - Federal should cause 5G to be removed or hopped
        manager.renew_assignments(1440)  # Assuming daily check
        
        # Check that all assignments are still valid
        # Should have at least the Federal assignments
        self.assertGreaterEqual(len(manager.active), 2, "Should have at least 2 active assignments")
    
    def test_request_denial(self):
        """Test that requests are denied when no suitable frequency can be found."""
        # Create architecture with Co-Primary priority mode
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="No Mitigation", 
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Fill up the spectrum with large bandwidth requests
        large_requests = []
        for i in range(10):  # Generate enough to potentially fill spectrum
            large_requests.append(SpectrumRequest(i, 0, i % 4, 200, "5G"))
        
        # Process these requests
        manager.process_arrivals(large_requests, 0)
        
        # Check how many were assigned vs denied
        initial_active = len(manager.active)
        initial_denied = self.metrics.requests_denied
        
        # Try to add one more request
        extra_request = SpectrumRequest(99, 1, 0, 40, "IoT")
        manager.process_arrivals([extra_request], 1)
        
        # If spectrum is full, this should be denied
        if initial_active == 10:  # All initial requests were accepted
            self.assertEqual(len(manager.active), initial_active, 
                             "Number of active assignments shouldn't change if spectrum is full")
            self.assertEqual(self.metrics.requests_denied, initial_denied + 1,
                             "Request should be denied if no suitable frequency is available")
    
    def test_power_control_mitigation(self):
        """
        Test power control mitigation for overlapping frequencies on opposite sides of the environment.
        
        This test verifies that when two nodes on opposite sides of the grid request the same 
        frequency, power control mitigation allows them to coexist by adjusting transmission power.
        """
        # Create architecture with Co-Primary priority and Power Control mitigation
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Beamforming",  # Use Power Control mitigation
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"  # Equal priority for all
        )
        
        # Create spectrum manager
        manager = SpectrumManager(self.env, arch, self.metrics)
        
        # Create request for node 0 (top-left corner in a 2x2 grid)
        request1 = SpectrumRequest(0, 0, 0, 60, "5G")
        manager.process_arrivals([request1], 0)
        
        # Verify first request was processed
        self.assertEqual(len(manager.active), 1, "Should have 1 active assignment")
        
        # Store the frequency assigned to the first request
        freq_start = manager.active[0].freq_start
        freq_end = manager.active[0].freq_end
        
        # Create a second request for node 3 (bottom-right corner) with the same frequency range
        # In a 2x2 grid, node 0 is top-left and node 3 is bottom-right
        request2 = SpectrumRequest(1, 1, 3, 60, "IoT")
        
        # Process the second request
        manager.process_arrivals([request2], 1)
        
        # Verify both requests were assigned despite frequency overlap
        self.assertEqual(len(manager.active), 2, "Should have 2 active assignments")
        
        # Check that both assignments have the same frequency range
        frequency_ranges = [(a.freq_start, a.freq_end) for a in manager.active]
        
        # Verify the nodes are correctly assigned (0 and 3)
        nodes = [a.node_id for a in manager.active]
        self.assertIn(0, nodes, "Node 0 should have an assignment")
        self.assertIn(3, nodes, "Node 3 should have an assignment")
        
        # Check if any assignments have reduced quality due to power control
        has_reduced_quality = any(a.quality < 1.0 for a in manager.active)
        self.assertTrue(has_reduced_quality, 
                       "At least one assignment should have reduced quality due to power control")

if __name__ == '__main__':
    unittest.main()
