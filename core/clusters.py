import numpy as np
import networkx as nx

def compute_clusters(grid, thresh=0.6):
    G = nx.grid_2d_graph(*grid.shape)
    for (i, j) in list(G.nodes):
        if grid[i, j] < thresh:
            G.remove_node((i, j))

    clusters = list(nx.connected_components(G))
    return clusters