"""
Visualize trade space results for the high demand scenario.
"""
import os
import pandas as pd
import plotly.express as px
import numpy as np

RESULTS_FILE = "results/high_demand/event_driven_results_high.csv"
PLOT_DIR = "results/high_demand/plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# Load results from CSV
df = pd.read_csv(RESULTS_FILE)

# Normalize Coordination_Cost to [0, 1]
if 'Coordination_Cost' in df.columns:
    min_cost = df['Coordination_Cost'].min()
    max_cost = df['Coordination_Cost'].max()
    if max_cost > min_cost:
        df['Coordination_Cost_Normalized'] = (df['Coordination_Cost'] - min_cost) / (max_cost - min_cost)
    else:
        df['Coordination_Cost_Normalized'] = 0.0  # All values are the same

# Logarithmic normalization for Coordination_Cost
if 'Coordination_Cost' in df.columns:
    df['Log_Coordination_Cost'] = np.log1p(df['Coordination_Cost'])
    min_log = df['Log_Coordination_Cost'].min()
    max_log = df['Log_Coordination_Cost'].max()
    if max_log > min_log:
        df['Coordination_Cost_LogNorm'] = (df['Log_Coordination_Cost'] - min_log) / (max_log - min_log)
    else:
        df['Coordination_Cost_LogNorm'] = 0.0

# Diagnostic: Print number of loaded results and unique architectures
print(f"Loaded {len(df)} results from CSV.")
if 'architecture_id' in df.columns:
    print("Unique architectures:", df['architecture_id'].nunique())
    print("Sample architecture_ids:", df['architecture_id'].unique()[:5])
else:
    print("No 'architecture_id' column found. Columns are:", df.columns.tolist())

key_metrics = ["Correct_SUE", "Blocking_Prob", "Coordination_Cost", "Coordination_Cost_Normalized", "Coordination_Cost_LogNorm"]
for col in key_metrics:
    nan_count = df[col].isna().sum() if col in df.columns else 'N/A'
    print(f"NaNs in {col}: {nan_count}")

# If needed, convert architecture_id to string for hover labels
if 'architecture_id' in df.columns:
    df['label'] = df['architecture_id'].astype(str)
else:
    df['label'] = df.index.astype(str)

def format_metric_name(metric_name):
    return metric_name.replace("_", " ").title()

def plot_trade_space(df, x_metric, y_metric, color_by=None, save_path=None, html_path=None):
    color = color_by if color_by in df.columns else None
    fig = px.scatter(
        df, x=x_metric, y=y_metric, color=color, hover_name='label',
        title=f"High Demand: {format_metric_name(x_metric)} vs {format_metric_name(y_metric)}",
        labels={x_metric: format_metric_name(x_metric), y_metric: format_metric_name(y_metric)}
    )
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

plots = [
    ("Correct_SUE", "Blocking_Prob", "coordination_mode", "correct_sue_vs_blocking"),
    ("Correct_SUE", "Coordination_Cost", "coordination_mode", "correct_sue_vs_coordination"),
    ("Correct_SUE", "Coordination_Cost_Normalized", "coordination_mode", "correct_sue_vs_coordination_normalized"),
    ("Correct_SUE", "Coordination_Cost_LogNorm", "coordination_mode", "correct_sue_vs_coordination_lognorm"),
    ("Coordination_Cost", "Blocking_Prob", "coordination_mode", "coordination_vs_blocking"),
    ("Coordination_Cost_Normalized", "Blocking_Prob", "coordination_mode", "coordination_normalized_vs_blocking"),
    ("Coordination_Cost_LogNorm", "Blocking_Prob", "coordination_mode", "coordination_lognorm_vs_blocking"),
]

for x, y, color, name in plots:
    html_path = os.path.join(PLOT_DIR, f"{name}.html")
    img_path = os.path.join(PLOT_DIR, f"{name}.png")
    plot_trade_space(df, x, y, color_by=color, save_path=img_path, html_path=html_path)
