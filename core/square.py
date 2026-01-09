import numpy as np

class Square:
    def __init__(self, size=32, noise=0.02):
        self.size = size
        self.grid = np.random.rand(size, size)
        self.noise = noise

    def step(self):
        # Structural crowding update (no time semantics)
        kernel = np.array([[0.05, 0.1, 0.05],
                           [0.1,  0.4, 0.1 ],
                           [0.05, 0.1, 0.05]])
        padded = np.pad(self.grid, 1, mode="wrap")
        new = np.zeros_like(self.grid)

        for i in range(self.size):
            for j in range(self.size):
                patch = padded[i:i+3, j:j+3]
                new[i, j] = np.sum(patch * kernel)

        self.grid = new + np.random.normal(0, self.noise, self.grid.shape)
        self.grid = np.clip(self.grid, 0, 1)

        return self.grid