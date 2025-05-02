#!/usr/bin/env python3
"""
test_environment.py

Creates an Environment (grid of squares) and visualizes the nodes and square boundaries.
"""

import matplotlib.pyplot as plt
from models.environment import Environment

def plot_environment(squares_rows, squares_cols):
    # Create the environment with the specified number of squares.
    env = Environment(squares_rows, squares_cols)
    
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Plot each node as a point and label it with its node_id.
    for node in env.nodes:
        # In our visualization, use (col, row) as (x, y).
        x, y = node.col, node.row
        ax.plot(x, y, 'ko')  # black circle for node
        ax.text(x, y, str(node.node_id), color='red', fontsize=10,
                ha='center', va='center')
    
    # Draw the squares (grid cells)
    for r in range(squares_rows):
        for c in range(squares_cols):
            # Each square has width and height of 1.
            square = plt.Rectangle((c, r), 1, 1, fill=False, edgecolor='blue', lw=2)
            ax.add_patch(square)
    
    # Set plot limits and labels.
    ax.set_xlim(-0.5, squares_cols + 0.5)
    ax.set_ylim(-0.5, squares_rows + 0.5)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.set_title(f"Environment: {squares_rows} x {squares_cols} Squares\n"
                 f"({env.num_nodes_rows} x {env.num_nodes_cols} Nodes)")
    ax.set_aspect('equal')
    # Optionally invert the y-axis if you want the origin at the top-left:
    # ax.invert_yaxis()
    
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    # Example: visualize an environment with 3 squares by 3 squares.
    plot_environment(squares_rows=1, squares_cols=1)