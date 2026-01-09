import numpy as np

class Persistence:
    def __init__(self, size):
        self.map = np.zeros((size, size))

    def update(self, grid, threshold=0.02):
        delta = np.abs(grid - getattr(self, "last", grid))
        self.map[delta < threshold] += 1
        self.map[delta >= threshold] = 0
        self.last = grid.copy()
        return self.map