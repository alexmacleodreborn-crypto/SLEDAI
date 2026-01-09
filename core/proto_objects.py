import numpy as np

def cluster_reaction_points(RP_coords, eps=2.5, min_samples=3):
    """
    Physics-first clustering of Reaction Points.
    No ML, no sklearn.

    RP_coords: list of (row, col)
    eps: spatial radius
    min_samples: minimum points to form a proto-object
    """

    if len(RP_coords) == 0:
        return []

    RP = np.array(RP_coords)
    used = np.zeros(len(RP), dtype=bool)
    clusters = []

    for i in range(len(RP)):
        if used[i]:
            continue

        # Find neighbours within radius
        dists = np.linalg.norm(RP - RP[i], axis=1)
        neighbours = np.where(dists <= eps)[0]

        if len(neighbours) < min_samples:
            continue

        # Grow cluster
        cluster = set(neighbours.tolist())
        changed = True

        while changed:
            changed = False
            for idx in list(cluster):
                dists = np.linalg.norm(RP - RP[idx], axis=1)
                new = set(np.where(dists <= eps)[0])
                if len(new) >= min_samples:
                    if not new.issubset(cluster):
                        cluster |= new
                        changed = True

        cluster = list(cluster)
        for idx in cluster:
            used[idx] = True

        clusters.append(RP[cluster])

    return clusters