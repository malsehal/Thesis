"""
Defines a Node representing a location.
Each node is placed in a grid (with row and col) and “covers” one or more squares.
"""
class Node:
    def __init__(self, node_id, row, col, covered_squares):
        self.node_id = node_id
        self.row = row
        self.col = col
        self.covered_squares = set(covered_squares)  # set of square IDs this node touches
        self.active_assignments = []  # list of SpectrumAssignment objects

    def add_assignment(self, assignment):
        self.active_assignments.append(assignment)

    def remove_expired_assignments(self, current_time):
        self.active_assignments = [a for a in self.active_assignments if current_time < a.end_time]