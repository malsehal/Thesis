"""
Visualize trade space results for the low demand scenario.
"""
import os
import pandas as pd
import plotly.express as px
import numpy as np

RESULTS_FILE = "results/low_demand/event_driven_results_low.csv"
PLOT_DIR = "results/low_demand/plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# Load results from CSV
df = pd.read_csv(RESULTS_FILE)

# Normalize Coordination_Index to [0, 1]
if 'Coordination_Index' in df.columns:
    min_cost = df['Coordination_Index'].min()
    max_cost = df['Coordination_Index'].max()
    if max_cost > min_cost:
        df['Coordination_Index_Normalized'] = (df['Coordination_Index'] - min_cost) / (max_cost - min_cost)
    else:
        df['Coordination_Index_Normalized'] = 0.0  # All values are the same

# Logarithmic normalization for Coordination_Index
if 'Coordination_Index' in df.columns:
    df['Log_Coordination_Index'] = np.log1p(df['Coordination_Index'])
    min_log = df['Log_Coordination_Index'].min()
    max_log = df['Log_Coordination_Index'].max()
    if max_log > min_log:
        df['Coordination_Index_LogNorm'] = (df['Log_Coordination_Index'] - min_log) / (max_log - min_log)
    else:
        df['Coordination_Index_LogNorm'] = 0.0

key_metrics = ["SUE", "Blocking_Prob", "Coordination_Index", "Coordination_Index_Normalized", "Coordination_Index_LogNorm"]
for col in key_metrics:
    nan_count = df[col].isna().sum() if col in df.columns else 'N/A'
    print(f"NaNs in {col}: {nan_count}")

# If needed, convert architecture_id to string for hover labels
if 'architecture_id' in df.columns:
    df['label'] = df['architecture_id'].astype(str)
else:
    df['label'] = df.index.astype(str)

def format_metric_name(metric_name):
    # Add user-specified units for known metrics
    units = {
        "SUE": "(Users/MHz·Km²·day)",
        "Blocking_Prob": "(%)",
        "Coordination_Index": "",
        "Coordination_Index_Normalized": "(normalized)",
        "Coordination_Index_LogNorm": "(log-normalized)",
        "Human_Minutes": "(minutes)",
        "coord_queries": "(queries)",
    }
    base = metric_name.replace("_", " ").title()
    return f"{base} {units.get(metric_name, '')}".strip()

def plot_trade_space(df, x_metric, y_metric, color_by=None, save_path=None, html_path=None):
    color = color_by if color_by in df.columns else None
    # --- JITTER: Add small random noise to x/y to distinguish overlapping architectures ---
    jitter_strength = 0.01  # Adjust as needed for clarity
    x_jitter = np.random.uniform(-jitter_strength, jitter_strength, size=len(df))
    y_jitter = np.random.uniform(-jitter_strength, jitter_strength, size=len(df))
    x_jittered_col = f"{x_metric}_jittered"
    y_jittered_col = f"{y_metric}_jittered"
    df[x_jittered_col] = df[x_metric] + x_jitter if np.issubdtype(df[x_metric].dtype, np.number) else df[x_metric]
    df[y_jittered_col] = df[y_metric] + y_jitter if np.issubdtype(df[y_metric].dtype, np.number) else df[y_metric]
    fig = px.scatter(
        df, x=x_jittered_col, y=y_jittered_col, color=color, hover_name='label',
        title=f"Low Demand: {format_metric_name(x_metric)} vs {format_metric_name(y_metric)}",
        labels={x_jittered_col: format_metric_name(x_metric), y_jittered_col: format_metric_name(y_metric)}
    )
    fig.update_xaxes(title=format_metric_name(x_metric))
    fig.update_yaxes(title=format_metric_name(y_metric))
    fig.update_traces(marker=dict(size=12, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(legend_title=color_by.capitalize() if color_by else None)
    if html_path:
        fig.write_html(html_path)
        print(f"Saved interactive plot to {html_path}")
    if save_path:
        try:
            fig.write_image(save_path)
            print(f"Saved static plot to {save_path}")
        except Exception as e:
            print(f"Could not save static image: {e}")

# --- Additional plots for deeper analysis and clustering ---
from plotly.express import scatter_matrix, parallel_coordinates

def plot_pairwise_matrix(df, metrics, color_by=None, save_path=None, html_path=None):
    color = color_by if color_by in df.columns else None
    fig = scatter_matrix(
        df,
        dimensions=metrics,
        color=color,
        hover_name='label',
        title="Pairwise Metric Scatter Matrix",
        labels={m: format_metric_name(m) for m in metrics}
    )
    if html_path:
        fig.write_html(html_path)
        print(f"Saved interactive matrix plot to {html_path}")
    if save_path:
        try:
            fig.write_image(save_path)
            print(f"Saved static matrix plot to {save_path}")
        except Exception as e:
            print(f"Could not save static image: {e}")

def plot_parallel_coords(df, metrics, color_by=None, save_path=None, html_path=None):
    # Map categorical color_by to numeric for plotly parallel_coordinates
    if color_by and color_by in df.columns:
        color_map = {k: v for v, k in enumerate(df[color_by].unique())}
        color_numeric = df[color_by].map(color_map)
        color_tickvals = list(color_map.values())
        color_ticktext = list(color_map.keys())
    else:
        color_numeric = None
        color_tickvals = None
        color_ticktext = None
    fig = parallel_coordinates(
        df,
        dimensions=metrics,
        color=color_numeric,
        labels={m: format_metric_name(m) for m in metrics},
        title="Parallel Coordinates Plot"
    )
    # Add tick labels for color axis if using categorical mapping
    if color_numeric is not None and hasattr(fig.data[0], 'line'):
        fig.data[0].line.colorbar = dict(
            tickvals=color_tickvals,
            ticktext=color_ticktext,
            title=color_by
        )
    if html_path:
        fig.write_html(html_path)
        print(f"Saved interactive parallel plot to {html_path}")
    if save_path:
        try:
            fig.write_image(save_path)
            print(f"Saved static parallel plot to {save_path}")
        except Exception as e:
            print(f"Could not save static image: {e}")

# Plots to generate
plots = [
    ("SUE", "Blocking_Prob", "coordination_mode", "sue_vs_blocking"),
    ("SUE", "Coordination_Index", "coordination_mode", "sue_vs_coordination"),
    ("SUE", "Coordination_Index_Normalized", "coordination_mode", "sue_vs_coordination_normalized"),
    ("SUE", "Coordination_Index_LogNorm", "coordination_mode", "sue_vs_coordination_lognorm"),
    ("Coordination_Index", "Blocking_Prob", "coordination_mode", "coordination_vs_blocking"),
    ("Coordination_Index_Normalized", "Blocking_Prob", "coordination_mode", "coordination_normalized_vs_blocking"),
    ("Coordination_Index_LogNorm", "Blocking_Prob", "coordination_mode", "coordination_lognorm_vs_blocking"),
]

for x, y, color, name in plots:
    html_path = os.path.join(PLOT_DIR, f"{name}.html")
    img_path = os.path.join(PLOT_DIR, f"{name}.png")
    plot_trade_space(df, x, y, color_by=color, save_path=img_path, html_path=html_path)

# --- Additional trade space plots by licensing mechanism and architectural decisions ---
# Licensing mechanism column is likely 'licensing_mode'
if 'licensing_mode' in df.columns:
    for x, y, _, name in plots:
        html_path = os.path.join(PLOT_DIR, f"{name}_by_licensing_mode.html")
        img_path = os.path.join(PLOT_DIR, f"{name}_by_licensing_mode.png")
        print(f"Generating trade space plot: {name} colored by licensing_mode")
        plot_trade_space(df, x, y, color_by='licensing_mode', save_path=img_path, html_path=html_path)

# Architectural decisions (from simulation.py: freq_plan, interference_mitigation, sensing_mode, pricing_mode, enforcement_mode, priority_mode, grant_duration)
arch_decisions = [
    'coordination_mode', 'licensing_mode', 'freq_plan', 'interference_mitigation',
    'sensing_mode', 'pricing_mode', 'enforcement_mode', 'priority_mode', 'grant_duration'
]
# Only plot for those columns present in df and not 'coordination_mode' (already in default plots)
for decision in arch_decisions:
    if decision in df.columns and decision != 'coordination_mode':
        for x, y, _, name in plots:
            html_path = os.path.join(PLOT_DIR, f"{name}_by_{decision}.html")
            img_path = os.path.join(PLOT_DIR, f"{name}_by_{decision}.png")
            print(f"Generating trade space plot: {name} colored by {decision}")
            plot_trade_space(df, x, y, color_by=decision, save_path=img_path, html_path=html_path)

# Example usage for deeper analysis
pairwise_metrics = ["SUE", "Blocking_Prob", "Coordination_Index", "Human_Minutes", "coord_queries"]
plot_pairwise_matrix(df, pairwise_metrics, color_by="coordination_mode", html_path=os.path.join(PLOT_DIR, "pairwise_matrix.html"))
plot_parallel_coords(df, pairwise_metrics, color_by="coordination_mode", html_path=os.path.join(PLOT_DIR, "parallel_coords.html"))
