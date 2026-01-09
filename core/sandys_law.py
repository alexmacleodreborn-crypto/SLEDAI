import numpy as np

def compute_Z(grid, persistence):
    # Trap strength = crowding + rigidity
    crowding = np.abs(grid - grid.mean())
    Z = np.clip(crowding + persistence / (persistence.max() + 1e-6), 0, 1)
    return Z

def compute_Sigma(grid, prev_grid):
    Sigma = np.abs(grid - prev_grid)
    return Sigma

def detect_RP(Z, Sigma, z_thresh=0.4, s_thresh=0.15):
    return np.where((Z > z_thresh) & (Sigma > s_thresh))

def compute_T_info(Z, Sigma):
    T = np.zeros_like(Z)
    T[(Z < 0.3) & (Sigma > 0.2)] = -1   # decohered
    T[(Z > 0.5) & (Sigma < 0.1)] = +1   # coherent
    return T