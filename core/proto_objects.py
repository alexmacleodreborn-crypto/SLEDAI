import numpy as np
from sklearn.cluster import DBSCAN

def cluster_reaction_points(RP_coords, eps=2.5, min_samples=3):
    """
    RP_coords: array of shape (N, 2) -> [(row, col), ...]
    returns: list of proto-object clusters (each cluster = list of points)
    """
    if len(RP_coords) == 0:
        return []

    X = np.array(RP_coords)

    db = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    labels = db.labels_

    clusters = []
    for label in set(labels):
        if label == -1:
            continue  # noise
        cluster = X[labels == label]
        clusters.append(cluster)

    return clusters