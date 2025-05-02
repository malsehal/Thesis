"""
Defines Assignment classes for spectrum management.
"""
from dataclasses import dataclass
from typing import Optional, Set
import numpy as np

@dataclass
class Assignment:
    """
    Represents a frequency assignment to a node.
    
    Attributes:
        assignment_id: Sequential identifier
        node_id: Index in Environment.nodes
        freq_start: Start frequency in MHz
        freq_end: End frequency in MHz
        device_type: Type of device ("5G", "IoT", "Federal")
        quality: Signal quality factor (default=1.0)
        next_check_tick: When to check for renewal (None for permanent)
        priority_tier: Priority level (0 = highest)
    """
    assignment_id: int
    node_id: int
    freq_start: int
    freq_end: int
    device_type: str
    quality: float = 1.0
    next_check_tick: Optional[int] = None
    priority_tier: int = 0
    
    def conflicts_with(self, other, environment):
        """
        Determines if this assignment conflicts with another assignment.
        
        Args:
            other: Another Assignment instance
            environment: The Environment instance containing nodes
            
        Returns:
            True if there's a spatial and spectral overlap, False otherwise
        """
        # Check for frequency overlap first (most efficient)
        if self.freq_end <= other.freq_start or self.freq_start >= other.freq_end:
            return False
            
        # Get the nodes
        this_node = environment.nodes[self.node_id]
        other_node = environment.nodes[other.node_id]
        
        # Check for spatial overlap through shared squares
        shared_squares = this_node.covered_squares.intersection(other_node.covered_squares)
        return len(shared_squares) > 0
    
    def get_node_relationship(self, other, environment):
        """
        Determine the spatial relationship between nodes.
        
        Args:
            other: Another Assignment instance
            environment: The Environment instance containing nodes
            
        Returns:
            String: "same" if same node, "adjacent" if adjacent nodes, 
                   "opposite" if diagonal/opposite, "none" if no overlap
        """
        # Get the nodes
        this_node = environment.nodes[self.node_id]
        other_node = environment.nodes[other.node_id]
        
        # Check if same node
        if this_node.node_id == other_node.node_id:
            return "same"
            
        # Check for shared squares (if no shared squares, then "none")
        shared_squares = this_node.covered_squares.intersection(other_node.covered_squares)
        if not shared_squares:
            return "none"
            
        # Special case for 1-square environment: all nodes overlap, so only diagonally opposite nodes are 'opposite', others are 'adjacent'
        # Assume square is 2x2 nodes (node IDs: 0,1,2,3) for 1-square environment
        if len(environment.nodes) == 4 and len(shared_squares) == 1:
            pairs_opposite = {(0,3), (3,0), (1,2), (2,1)}
            if (this_node.node_id, other_node.node_id) in pairs_opposite:
                return "opposite"
            else:
                return "adjacent"
        # Calculate Manhattan distance between nodes
        manhattan_dist = abs(this_node.row - other_node.row) + abs(this_node.col - other_node.col)
        # Adjacent nodes are 1 unit away (either same row or same column)
        if manhattan_dist == 1:
            return "adjacent"
        # Diagonal/opposite nodes are either 2 units away diagonally or across a square 
        else:
            return "opposite"
    
    def apply_mitigation(self, other, arch_policy, environment):
        """
        Applies interference mitigation based on the architecture policy.
        
        Args:
            other: Another Assignment instance
            arch_policy: The ArchitecturePolicy instance
            environment: The Environment instance
            
        Returns:
            True if assignments can coexist (with possible quality reduction),
            False if they still conflict
        """
        mitigation = arch_policy.interference_mitigation
        # No mitigation - assignments still conflict
        if mitigation == "No Mitigation":
            return False
        relationship = self.get_node_relationship(other, environment)
        if mitigation == "Power Control":
            if relationship == "opposite":
                quality_factor = 0.7
                self.quality *= quality_factor
                other.quality *= quality_factor
                return True
            else:
                return False
        elif mitigation == "Beamforming":
            if relationship == "opposite":
                quality_factor = 0.7
                self.quality *= quality_factor
                other.quality *= quality_factor
                return True
            else:
                return False
        elif mitigation == "Combination":
            if relationship == "opposite":
                quality_factor = 0.7
                self.quality *= quality_factor
                other.quality *= quality_factor
                return True
            elif relationship == "adjacent":
                quality_factor = 0.5
                self.quality *= quality_factor
                other.quality *= quality_factor
                return True
            else:
                return False
        # Frequency hopping doesn't resolve spatial overlap directly
        if mitigation == "Frequency Hopping":
            return False
        # Default - still conflict
        return False

    def __repr__(self):
        return (f"<Assignment id={self.assignment_id} node={self.node_id} "
                f"freq=({self.freq_start}-{self.freq_end}) type={self.device_type} "
                f"quality={self.quality:.2f} priority={self.priority_tier} "
                f"next_check={self.next_check_tick}>")