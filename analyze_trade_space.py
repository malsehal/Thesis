#!/usr/bin/env python3
"""
Analyze Trade Space

This script:
1. Simulates the high demand scenario across all feasible architectural configurations
2. Collects performance metrics for each architecture
3. Visualizes the trade space with scatter plots showing how different architectures
   perform across key metrics

Key metrics analyzed:
- Spectral Use Efficiency (SUE)
- Coordination Cost
- Blocking Probability
- Mean Quality
"""
import os
import sys
import numpy as np
import plotly.express as px
import matplotlib.patches as mpatches
from collections import defaultdict
import time
import pickle
from tqdm import tqdm

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models.environment import Environment
from models.request import SpectrumRequest
from utils.demand_generator import generate_demand
from core.metrics import MetricsCollector
from core.spectrum_manager import SpectrumManager
from core.simulation import Simulation
from morphology.architecture_enumerator import generate_all_architectures
from config.scenarios import DEFAULT_SIM_MINUTES

# Constants for the simulation
SIM_DAYS = 30  # Run for 30 days
MINUTES_PER_DAY = 1440
SIM_MINUTES = SIM_DAYS * MINUTES_PER_DAY

# Cache file for saving simulation results to avoid re-running
CACHE_FILE = "trade_space_results.pkl"

def run_simulation(architecture, environment, demand):
    """
    Run a simulation with the given architecture, environment, and demand.
    
    Args:
        architecture: An ArchitecturePolicy instance
        environment: An Environment instance
        demand: List of SpectrumRequests
        
    Returns:
        Dictionary with metrics
    """
    # Create a simulation with the architecture
    simulation = Simulation(environment, architecture, demand, SIM_MINUTES)
    
    # Define how to handle manual licensing mode
    if architecture.licensing_mode == "Manual":
        # For Manual mode, extract the manager from the simulation for direct handling
        manager = simulation.spectrum_manager
        
        # For Manual mode, we need to queue requests and process them with delay
        pending_requests = []
        manual_processing_delay = 30 * MINUTES_PER_DAY  # 30-day delay
        
        for day in range(SIM_DAYS):
            day_start = day * MINUTES_PER_DAY
            day_end = (day + 1) * MINUTES_PER_DAY
            
            # Get requests arriving on this day
            day_requests = [req for req in demand if day_start <= req.arrival_time < day_end]
            
            # Queue new requests with processing delay
            for req in day_requests:
                processing_time = req.arrival_time + manual_processing_delay
                pending_requests.append((req, processing_time))
            
            # Process any pending requests that are due
            requests_to_process = []
            remaining_pending = []
            
            for req, proc_time in pending_requests:
                if proc_time < day_end:
                    requests_to_process.append(req)
                else:
                    remaining_pending.append((req, proc_time))
            
            pending_requests = remaining_pending
            
            # Process due requests
            if requests_to_process:
                manager.process_arrivals(requests_to_process, day_end - 1)
            
            # Run ticks for the day
            for tick in range(day_start, day_end):
                manager.tick_housekeeping(tick)
    else:
        # For Semi-Dynamic and Dynamic modes, just run the normal simulation
        simulation.run()
    
    # Get metrics after simulation is complete
    metrics = simulation.metrics
    
    # Generate a report
    total_band_mhz = 600  # MHz
    total_area_km2 = environment.num_squares  # Assume 1 km² per square
    report = metrics.final_report(total_band_mhz, total_area_km2, sim_minutes=SIM_MINUTES)
    
    # Add architecture info to the report
    report["architecture"] = architecture
    return report

def extract_arch_features(architecture):
    """
    Extract a tuple of features from an architecture for categorization.
    """
    return (
        architecture.coordination_mode,
        architecture.licensing_mode,
        architecture.priority_mode
    )

def plot_trade_space(results, x_metric, y_metric, color_by=None, save_path=None, html_path=None):
    """
    Plot a trade space with the given metrics using Plotly for interactive visualization.
    
    Args:
        results: List of dictionaries with metrics
        x_metric: Name of the metric to plot on x-axis
        y_metric: Name of the metric to plot on y-axis
        color_by: Field to color points by ('coordination', 'licensing', or 'priority')
        save_path: Path to save the static PNG plot to (optional)
        html_path: Path to save the interactive HTML plot to (optional)
    """
    if not results:
        print(f"Warning: No results available for trade space plot of {x_metric} vs {y_metric}")
        return

    # Prepare data for Plotly
    import pandas as pd
    df = pd.DataFrame(results)
    
    # Handle architecture column if present
    if 'architecture' in df.columns:
        # Extract features for labeling
        df['coordination'] = df['architecture'].apply(lambda a: getattr(a, 'coordination_mode', None))
        df['licensing'] = df['architecture'].apply(lambda a: getattr(a, 'licensing_mode', None))
        df['priority'] = df['architecture'].apply(lambda a: getattr(a, 'priority_mode', None))
        df['label'] = df['architecture'].apply(lambda a: str(a))
    else:
        df['label'] = df.index.astype(str)
    
    # Set color
    color = color_by if color_by in df.columns else None
    
    # Create Plotly scatter plot
    fig = px.scatter(
        df, x=x_metric, y=y_metric, color=color, hover_name='label',
        title=f"Architecture Trade Space: {format_metric_name(x_metric)} vs {format_metric_name(y_metric)}",
        labels={x_metric: format_metric_name(x_metric), y_metric: format_metric_name(y_metric)}
    )
    fig.update_traces(marker=dict(size=12, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(legend_title=color_by.capitalize() if color_by else None)
    
    # Save interactive HTML
    if html_path:
        fig.write_html(html_path)
        print(f"Saved interactive plot to {html_path}")
    # Optionally save as PNG (requires kaleido)
    if save_path:
        try:
            fig.write_image(save_path)
            print(f"Saved static plot to {save_path}")
        except Exception as e:
            print(f"Could not save static image: {e}")
    # Always show in browser
    fig.show()

def format_metric_name(metric_name):
    """Format a metric name for display in plots."""
    name_map = {
        "SUE": "Spectral Use Efficiency",
        "Avg_Daily_Users": "Average Daily Users",
        "Coordination_Cost": "Coordination Cost",
        "Blocking_Prob": "Blocking Probability",
        "Mean_Quality": "Mean Quality",
        "requests_total": "Total Requests",
        "requests_denied": "Denied Requests"
    }
    return name_map.get(metric_name, metric_name)

def plot_architectural_breakdown(results, metric, save_path=None):
    """
    Plot a breakdown of how different architectural dimensions affect a metric.
    
    Args:
        results: List of dictionaries with metrics
        metric: Name of the metric to analyze
        save_path: Path to save the plot to
    """
    if not results:
        print(f"Warning: No results available for architectural breakdown of {metric}")
        return
        
    import matplotlib.pyplot as plt
    plt.figure(figsize=(14, 10))
    
    # Group results by architectural dimensions
    by_coord = defaultdict(list)
    by_license = defaultdict(list)
    by_priority = defaultdict(list)
    
    for report in results:
        arch = report["architecture"]
        value = report[metric]
        by_coord[arch.coordination_mode].append(value)
        by_license[arch.licensing_mode].append(value)
        by_priority[arch.priority_mode].append(value)
    
    # Create subplots
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    
    # Plot for coordination mode
    coords = sorted(by_coord.keys())
    coord_means = [np.mean(by_coord[k]) for k in coords]
    coord_stds = [np.std(by_coord[k]) for k in coords]
    ax1.bar(coords, coord_means, yerr=coord_stds, alpha=0.7, capsize=5)
    ax1.set_title(f"By Coordination Mode")
    ax1.set_ylabel(format_metric_name(metric))
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot for licensing mode
    licenses = sorted(by_license.keys())
    license_means = [np.mean(by_license[k]) for k in licenses]
    license_stds = [np.std(by_license[k]) for k in licenses]
    ax2.bar(licenses, license_means, yerr=license_stds, alpha=0.7, capsize=5)
    ax2.set_title(f"By Licensing Mode")
    ax2.grid(axis='y', alpha=0.3)
    
    # Plot for priority mode
    priorities = sorted(by_priority.keys())
    priority_means = [np.mean(by_priority[k]) for k in priorities]
    priority_stds = [np.std(by_priority[k]) for k in priorities]
    ax3.bar(priorities, priority_means, yerr=priority_stds, alpha=0.7, capsize=5)
    ax3.set_title(f"By Priority Mode")
    ax3.grid(axis='y', alpha=0.3)
    
    plt.suptitle(f"Impact of Architectural Dimensions on {format_metric_name(metric)}")
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved breakdown plot to {save_path}")
    else:
        plt.show()

def analyze_metrics_sensitivity(results):
    """
    Analyze which architectural dimensions have the most impact on each metric.
    """
    metrics = ["SUE", "Coordination_Cost", "Blocking_Prob", "Mean_Quality", "Avg_Daily_Users"]
    dimensions = ["coordination_mode", "licensing_mode", "priority_mode", 
                "freq_plan", "interference_mitigation", "sensing_mode", 
                "pricing_mode", "enforcement_mode"]
    
    print("\nSensitivity Analysis: Which dimensions matter most for each metric?\n")
    print("-" * 80)
    
    for metric in metrics:
        print(f"\nMetric: {format_metric_name(metric)}")
        
        # For each dimension, calculate variance of the metric across different values of the dimension
        dimension_variances = []
        
        for dim in dimensions:
            # Group by this dimension
            by_dim = defaultdict(list)
            for report in results:
                arch = report["architecture"]
                value = report[metric]
                dim_value = getattr(arch, dim)
                by_dim[dim_value].append(value)
            
            # Calculate variance between groups (how much this dimension matters)
            if by_dim:  # Skip empty dimensions
                group_means = [np.mean(values) for values in by_dim.values()]
                dim_variance = np.var(group_means)
                dimension_variances.append((dim, dim_variance))
        
        # Sort dimensions by variance (impact)
        dimension_variances.sort(key=lambda x: x[1], reverse=True)
        
        # Print results
        print(f"  {'Dimension':<20} {'Impact':<10}")
        print(f"  {'-'*20} {'-'*10}")
        for dim, var in dimension_variances:
            impact = "High" if var > 0.1 else "Medium" if var > 0.01 else "Low"
            print(f"  {dim:<20} {impact:<10}")
        
        print("-" * 80)

def main():
    """Run the simulation for all feasible architectures and analyze the results."""
    print("Analyzing Trade Space for Spectrum Management Architectures")
    print("=" * 80)
    
    # Check if cached results exist
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached results from {CACHE_FILE}")
        with open(CACHE_FILE, 'rb') as f:
            results = pickle.load(f)
    else:
        # Setup environment (3x3 grid, smaller for faster development)
        environment = Environment(squares_rows=3, squares_cols=3)
        
        # Generate high demand scenario
        print("Generating high demand scenario")
        demand = generate_demand("high", environment, sim_minutes=SIM_MINUTES)
        print(f"Generated {len(demand)} requests over {SIM_DAYS} days")
        
        # Get all feasible architectures
        print("Generating feasible architectures")
        architectures = generate_all_architectures(apply_filter=True)
        print(f"Found {len(architectures)} feasible architectures")
        
        # Run simulations for all feasible architectures
        print(f"Running simulations for all {len(architectures)} feasible architectures")
        results = []
        
        for arch in tqdm(architectures, desc="Simulating architectures"):
            try:
                report = run_simulation(arch, environment, demand)
                results.append(report)
            except Exception as e:
                print(f"Error with architecture {arch}: {e}")
        
        # Save results to cache
        print(f"Saving results to {CACHE_FILE}")
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(results, f)
    
    # Print summary
    print(f"\nAnalyzed {len(results)} architectures")
    
    # Create directory for saving plots
    os.makedirs("trade_space_plots", exist_ok=True)
    
    # Create trade space plots
    key_metrics = [
        ("SUE", "Coordination_Cost"),
        ("SUE", "Blocking_Prob"),
        ("SUE", "Mean_Quality"),
        ("Blocking_Prob", "Mean_Quality"),
        ("Coordination_Cost", "Mean_Quality"),
        ("Avg_Daily_Users", "Coordination_Cost"),
    ]
    
    for x_metric, y_metric in key_metrics:
        for color_by in ['coordination', 'licensing', 'priority']:
            title = f"{x_metric}_vs_{y_metric}_by_{color_by}"
            save_path = f"trade_space_plots/{title}.png"
            html_path = f"trade_space_plots/{title}.html"
            plot_trade_space(results, x_metric, y_metric, color_by, save_path, html_path)
    
    # Plot architectural breakdown for key metrics
    for metric in ["SUE", "Coordination_Cost", "Blocking_Prob", "Mean_Quality", "Avg_Daily_Users"]:
        save_path = f"trade_space_plots/{metric}_breakdown.png"
        plot_architectural_breakdown(results, metric, save_path)
    
    # Analyze sensitivity
    if results:
        analyze_metrics_sensitivity(results)
    else:
        print("No results to analyze - check for errors in simulation")
    
    print("\nAnalysis complete - see trade_space_plots directory for visualizations")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds")
