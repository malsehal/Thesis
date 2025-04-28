"""
Visualization tool for spectrum manager tests.
This script provides visual representation of spectrum assignments to verify test results.
"""
import sys
import os
import matplotlib.pyplot as plt
import numpy as np

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.environment import Environment
from models.request import SpectrumRequest
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from morphology.architecture_enumerator import get_architecture_by_name
from config.parameters import FREQ_BASE_MHZ, TOTAL_BANDWIDTH_MHZ


def create_spectrum_visualization(manager, title, show_partitions=False):
    """
    Create a visualization of spectrum assignments.
    
    Args:
        manager: SpectrumManager instance with active assignments
        title: Title for the plot
        show_partitions: Whether to display partition boundaries (for Exclusive mode)
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Set up the plot
    ax.set_xlim(FREQ_BASE_MHZ, FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ)
    ax.set_ylim(-0.5, len(manager.active) + 0.5 if manager.active else 1)
    
    # Plot frequency range
    ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Assignment')
    ax.set_title(title)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Show partitions if in Exclusive mode
    if show_partitions and manager.arch_policy.priority_mode == "Exclusive":
        for device_type, (start, end) in manager.band_partitions.items():
            ax.axvspan(start, end, alpha=0.1, 
                      color='red' if device_type == "Federal" else 
                             'blue' if device_type == "5G" else 'green')
            ax.text((start + end) / 2, len(manager.active) + 0.2, 
                   device_type, ha='center', va='bottom', fontsize=10)
    
    # Plot each assignment
    y_pos = 0
    device_colors = {"5G": "blue", "IoT": "green", "Federal": "red"}
    
    for i, assignment in enumerate(manager.active):
        # Get assignment properties
        start = assignment.freq_start
        end = assignment.freq_end
        node = assignment.node_id
        device = assignment.device_type
        quality = getattr(assignment, 'quality', 1.0)  # Get quality if it exists
        
        # Plot the assignment as a horizontal bar
        color = device_colors.get(device, "gray")
        bar = ax.barh(i, end - start, left=start, height=0.5, 
                     color=color, alpha=0.7, edgecolor='black')
        
        # Add text labels
        quality_text = f"\nQuality: {quality:.2f}" if quality < 1.0 else ""
        ax.text(start + (end - start) / 2, i, 
               f"Node {node}\n{device}{quality_text}", 
               ha='center', va='center', color='white', fontweight='bold')
        
        # Add frequency range at the top of each bar
        ax.text(start, i + 0.3, 
               f"{start}", 
               ha='center', va='bottom', fontsize=8)
        ax.text(end, i + 0.3, 
               f"{end}", 
               ha='center', va='bottom', fontsize=8)
    
    # Add a legend
    handles = [plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.7) 
              for color in device_colors.values()]
    labels = list(device_colors.keys())
    ax.legend(handles, labels, loc='upper right')
    
    # Adjust layout
    plt.tight_layout()
    return fig


def visualize_environment_grid(env, nodes, title="Environment Grid"):
    """
    Visualize the environment grid with nodes.
    
    Args:
        env: Environment object
        nodes: List of node IDs to highlight
        title: Title for the plot
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Set up the plot
    rows, cols = env.squares_rows, env.squares_cols
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(-0.5, rows - 0.5)
    ax.set_title(title)
    
    # Draw grid
    for i in range(cols + 1):
        ax.axvline(i - 0.5, color='black', linestyle='-', alpha=0.3)
    for i in range(rows + 1):
        ax.axhline(i - 0.5, color='black', linestyle='-', alpha=0.3)
    
    # Place nodes on the grid
    for node_id in range(rows * cols):
        row = node_id // cols
        col = node_id % cols
        
        # Display coordinates
        ax.text(col, rows - 1 - row, f"Node {node_id}", 
               ha='center', va='center', 
               color='black' if node_id not in nodes else 'red',
               fontweight='normal' if node_id not in nodes else 'bold')
    
    # Adjust layout
    plt.tight_layout()
    return fig


def visualize_test_case(test_name):
    """
    Visualize a specific test case to understand frequency assignments.
    
    Args:
        test_name: Name of the test to visualize
    """
    # Create environment and metrics
    env = Environment(squares_rows=2, squares_cols=2)
    metrics = MetricsCollector()
    
    if test_name == "single_request":
        # Create architecture
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
        manager = SpectrumManager(env, arch, metrics)
        
        # Create a request
        request = SpectrumRequest(0, 0, 0, 40, "5G")
        
        # Process the request
        manager.process_arrivals([request], 0)
        
        # Create visualization
        fig = create_spectrum_visualization(
            manager, "Single Spectrum Request Test")
        
        return fig, metrics
        
    elif test_name == "multiple_requests":
        # Create architecture
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Frequency Hopping",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(env, arch, metrics)
        
        # Create multiple requests
        requests = [
            SpectrumRequest(0, 0, 0, 40, "5G"),     # Node 0
            SpectrumRequest(1, 0, 1, 40, "IoT"),    # Node 1
            SpectrumRequest(2, 0, 3, 40, "Federal") # Node 3
        ]
        
        # Process the requests
        manager.process_arrivals(requests, 0)
        
        # Create visualization
        fig = create_spectrum_visualization(
            manager, "Multiple Spectrum Requests Test")
        
        return fig, metrics
    
    elif test_name == "exclusive_mode":
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
        manager = SpectrumManager(env, arch, metrics)
        
        # Create requests for different device types
        requests = [
            SpectrumRequest(0, 0, 0, 40, "5G"),
            SpectrumRequest(1, 0, 1, 40, "IoT"),
            SpectrumRequest(2, 0, 2, 40, "Federal")
        ]
        
        # Process the requests
        manager.process_arrivals(requests, 0)
        
        # Create visualization
        fig = create_spectrum_visualization(
            manager, "Exclusive Mode Spectrum Partitioning", show_partitions=True)
        
        return fig, metrics
    
    elif test_name == "hierarchical_mode":
        # Create architecture with Hierarchical priority mode
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Frequency Hopping",
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Hierarchical"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(env, arch, metrics)
        
        # Create a 5G request and process it
        request_5g = SpectrumRequest(0, 0, 0, 100, "5G")
        manager.process_arrivals([request_5g], 0)
        
        # Create a Federal request for a different node
        request_federal = SpectrumRequest(1, 1, 1, 100, "Federal")
        manager.process_arrivals([request_federal], 1)
        
        # Create visualization of initial state
        fig1 = create_spectrum_visualization(
            manager, "Hierarchical Mode - Initial State")
        
        # Create a Federal request for the same node as 5G
        conflict_node = next(a.node_id for a in manager.active if a.device_type == "5G")
        conflict_request = SpectrumRequest(2, 2, conflict_node, 100, "Federal")
        manager.process_arrivals([conflict_request], 2)
        
        # Force a renewal to test preemption/hopping
        manager.renew_assignments(1440)
        
        # Create visualization of final state
        fig2 = create_spectrum_visualization(
            manager, "Hierarchical Mode - After Preemption/Hopping")
        
        return [fig1, fig2], metrics
        
    elif test_name == "request_denial":
        # Create architecture
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
        manager = SpectrumManager(env, arch, metrics)
        
        # Fill up the spectrum with large bandwidth requests
        large_requests = []
        for i in range(5):  # Generate enough to potentially fill spectrum
            large_requests.append(SpectrumRequest(i, 0, i % 4, 200, "5G"))
        
        # Process these requests
        manager.process_arrivals(large_requests, 0)
        
        # Create visualization of initial state
        fig1 = create_spectrum_visualization(
            manager, "Request Denial Test - Initial State")
        
        # Record metrics before attempting to add more
        initial_active = len(manager.active)
        initial_denied = metrics.requests_denied
        
        # Try to add one more request
        extra_request = SpectrumRequest(99, 1, 0, 120, "IoT")
        manager.process_arrivals([extra_request], 1)
        
        # Create visualization of final state
        fig2 = create_spectrum_visualization(
            manager, f"Request Denial Test - After Extra Request\nDenied: {metrics.requests_denied > initial_denied}")
        
        return [fig1, fig2], metrics
        
    elif test_name == "power_control":
        # Create architecture with Beamforming mitigation
        arch = get_architecture_by_name(
            coord_mode="Centralized",
            licensing="Dynamic",
            freq_plan="Sub Channels",
            interference="Beamforming",  # Use Beamforming mitigation instead of Power Control
            sensing="Device Based",
            pricing="No Cost",
            enforcement="Active",
            priority="Co-Primary"
        )
        
        # Create spectrum manager
        manager = SpectrumManager(env, arch, metrics)
        
        # Create visualization of the environment grid
        grid_fig = visualize_environment_grid(env, [0, 3], "2x2 Grid with Nodes 0 and 3")
        
        # Create request for node 0 (top-left corner)
        request1 = SpectrumRequest(0, 0, 0, 60, "5G")
        manager.process_arrivals([request1], 0)
        
        # Create visualization after first request
        fig1 = create_spectrum_visualization(
            manager, "Beamforming Test - After First Request (Node 0)")
        
        # Create a second request for node 3 (bottom-right corner) with the same frequency range
        request2 = SpectrumRequest(1, 1, 3, 60, "IoT")
        manager.process_arrivals([request2], 1)
        
        # Create visualization after second request
        fig2 = create_spectrum_visualization(
            manager, "Beamforming Test - After Second Request (Node 3)\nNote: Quality < 1.0 indicates beamforming adjustment")
        
        return [grid_fig, fig1, fig2], metrics


def display_metrics(metrics):
    """Display key metrics from the test."""
    print("\nMetrics:")
    print(f"Total Requests: {metrics.requests_total}")
    print(f"Requests Denied: {metrics.requests_denied}")
    print(f"Coordination Queries: {metrics.coord_queries}")
    if hasattr(metrics, 'quality_measurements') and metrics.quality_measurements:
        avg_quality = sum(metrics.quality_measurements) / len(metrics.quality_measurements)
        print(f"Average Quality: {avg_quality:.2f}")


def run_visualizations():
    """Run all visualizations."""
    test_cases = [
        "single_request",
        "multiple_requests",
        "exclusive_mode", 
        "hierarchical_mode",
        "request_denial",
        "power_control"  # This uses Beamforming now
    ]
    
    for test_name in test_cases:
        print(f"\nVisualizing test: {test_name}")
        
        result, metrics = visualize_test_case(test_name)
        
        # Show metrics
        display_metrics(metrics)
        
        # Display figures
        if isinstance(result, list):
            for i, fig in enumerate(result):
                plt.figure(fig.number)
                plt.savefig(f"{test_name}_{i+1}.png")
                print(f"Saved visualization to {test_name}_{i+1}.png")
        else:
            plt.figure(result.number)
            plt.savefig(f"{test_name}.png")
            print(f"Saved visualization to {test_name}.png")
    
    # Show all figures
    plt.show()


if __name__ == "__main__":
    run_visualizations()
