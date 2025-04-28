import pickle
import plotly.express as px
import pandas as pd
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def load_results(filepath):
    """Load simulation results from a pickle file."""
    with open(filepath, 'rb') as f:
        return pickle.load(f)

def plot_sue_vs_blocking(results, html_path=None, save_path=None):
    """Plot SUE vs Blocking Probability for all architectures using Plotly."""
    # Convert results to DataFrame for easier handling
    df = pd.DataFrame(results)

    # Extract architecture decisions if present
    if 'architecture' in df.columns:
        arch_fields = [
            'coordination_mode',
            'licensing_mode',
            'freq_plan',
            'interference_mitigation',
            'sensing_mode',
            'pricing_mode',
            'enforcement_mode',
            'priority_mode'
        ]
        for field in arch_fields:
            df[field] = df['architecture'].apply(lambda a: getattr(a, field, None))
        # Optionally, create a summary string for hover
        df['arch_summary'] = df.apply(lambda row: '\n'.join([
            f"Coordination: {row['coordination_mode']}",
            f"Licensing: {row['licensing_mode']}",
            f"Freq Plan: {row['freq_plan']}",
            f"Interference: {row['interference_mitigation']}",
            f"Sensing: {row['sensing_mode']}",
            f"Pricing: {row['pricing_mode']}",
            f"Enforcement: {row['enforcement_mode']}",
            f"Priority: {row['priority_mode']}" ]), axis=1)
    else:
        df['arch_summary'] = ''

    fig = px.scatter(
        df,
        x='Blocking_Prob',
        y='SUE',
        title='SUE vs Blocking Probability (All Architectures)',
        labels={'Blocking_Prob': 'Blocking Probability', 'SUE': 'Spectral Use Efficiency (SUE)'},
        opacity=0.6,
        hover_data=['arch_summary']
    )
    fig.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(font=dict(size=14))

    # Save interactive HTML
    if html_path:
        fig.write_html(html_path)
        print(f"Plot saved as '{html_path}' (interactive HTML)")
    # Optionally save as PNG (requires kaleido)
    if save_path:
        try:
            fig.write_image(save_path)
            print(f"Plot saved as '{save_path}' (PNG)")
        except Exception as e:
            print(f"Could not save static image: {e}")
    # Always show in browser
    fig.show()

if __name__ == '__main__':
    file = 'trade_space_results.pkl'
    if os.path.exists(file):
        res = load_results(file)
        plot_sue_vs_blocking(res, html_path='sue_vs_blocking.html', save_path='sue_vs_blocking.png')
    else:
        print(f"Error: results file '{file}' not found.")
