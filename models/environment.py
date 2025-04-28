"""
Defines the simulation environment.
It consists of a grid of squares. Nodes are placed at the intersections.
You can specify the number of squares (rows and columns) to allow scaling.
"""
from models.node import Node

class Environment:
    def __init__(self, squares_rows=1, squares_cols=1):
        self.squares_rows = squares_rows
        self.squares_cols = squares_cols
        self.num_nodes_rows = squares_rows + 1
        self.num_nodes_cols = squares_cols + 1
        self.nodes = self.generate_nodes()

    def generate_nodes(self):
        nodes = []
        node_id = 0
        for r in range(self.num_nodes_rows):
            for c in range(self.num_nodes_cols):
                # Determine which squares this node touches.
                covered = set()
                # Node at (r, c) touches square (r, c) if r < squares_rows and c < squares_cols.
                if r < self.squares_rows and c < self.squares_cols:
                    covered.add(r * self.squares_cols + c)
                if r > 0 and c < self.squares_cols:
                    covered.add((r-1) * self.squares_cols + c)
                if c > 0 and r < self.squares_rows:
                    covered.add(r * self.squares_cols + (c-1))
                if r > 0 and c > 0:
                    covered.add((r-1) * self.squares_cols + (c-1))
                node = Node(node_id, r, c, list(covered))
                nodes.append(node)
                node_id += 1
        return nodes

    def remove_expired_assignments(self, current_time):
        for node in self.nodes:
            node.remove_expired_assignments(current_time)

    def get_neighbors(self, node_id):
        """
        Returns the node_ids of all immediate neighbors (up, down, left, right) for the given node_id.
        """
        node = self.nodes[node_id]
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
        neighbors = []
        for dr, dc in directions:
            nr, nc = node.row + dr, node.col + dc
            if 0 <= nr < self.num_nodes_rows and 0 <= nc < self.num_nodes_cols:
                neighbor_id = nr * self.num_nodes_cols + nc
                if neighbor_id != node_id:
                    neighbors.append(neighbor_id)
        return neighbors

    @property
    def num_squares(self):
        return self.squares_rows * self.squares_cols