import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from core.square import Square
from core.persistence import Persistence
from core.sandys_law import compute_Z, compute_Sigma, detect_RP
from core.proto_objects import cluster_reaction_points

# =====================================================
# SESSION STATE (PROTO-OBJECT MEMORY)
# =====================================================

if "proto_memory" not in st.session_state:
    st.session_state.proto_memory = []
    st.session_state.next_id = 0

# =====================================================
# HELPERS
# =====================================================

def update_proto_persistence(current_clusters, memory, next_id, dist_thresh=4.0):
    """
    Physics-first proto-object persistence via centroid continuity.
    """

    def centroid(cluster):
        return np.mean(cluster, axis=0)

    current = [
        {"centroid": centroid(c), "points": c, "matched": False}
        for c in current_clusters
    ]

    updated_memory = []
    annotations = []

    # Match previous objects to current clusters
    for obj in memory:
        prev_c = obj["centroid"]
        best = None
        best_dist = None

        for c in current:
            if c["matched"]:
                continue
            d = np.linalg.norm(prev_c - c["centroid"])
            if best is None or d < best_dist:
                best = c
                best_dist = d

        if best is not None and best_dist <= dist_thresh:
            # SURVIVAL
            best["matched"] = True
            updated_memory.append({
                "id": obj["id"],
                "centroid": best["centroid"],
                "points": best["points"],
                "age": obj["age"] + 1
            })
            annotations.append(("survive", best["points"]))
        else:
            # DEATH
            annotations.append(("die", obj["points"]))

    # Births
    for c in current:
        if not c["matched"]:
            updated_memory.append({
                "id": next_id,
                "centroid": c["centroid"],
                "points": c["points"],
                "age": 1
            })
            annotations.append(("birth", c["points"]))
            next_id += 1

    return updated_memory, annotations, next_id

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("A7DO-D • Square × Sandy’s Law")
st.caption("Pre-symbolic cognition • Structure → Stress → Memory")

# =====================================================
# SIDEBAR CONTROLS (TUNED)
# =====================================================

st.sidebar.header("World Geometry")
size = st.sidebar.slider("Grid size", 16, 64, 32, step=4)

st.sidebar.header("World Motion (IMPORTANT)")
square_steps =