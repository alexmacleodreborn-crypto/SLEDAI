import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from core.square import Square
from core.persistence import Persistence
from core.sandys_law import compute_Z, compute_Sigma, detect_RP
from core.proto_objects import cluster_reaction_points

# =====================================================
# SESSION STATE — WORLD + MEMORY
# =====================================================

if "square" not in st.session_state:
    st.session_state.square = None
    st.session_state.persist = None
    st.session_state.prev = None
    st.session_state.frame = 0

if "proto_memory" not in st.session_state:
    st.session_state.proto_memory = []
    st.session_state.next_id = 0

# =====================================================
# HELPER — PROTO-OBJECT PERSISTENCE
# =====================================================

def update_proto_persistence(current_clusters, memory, next_id, dist_thresh):
    def centroid(cluster):
        return np.mean(cluster, axis=0)

    current = [
        {"centroid": centroid(c), "points": c, "matched": False}
        for c in current_clusters
    ]

    updated_memory = []
    annotations = []

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
            best["matched"] = True
            updated_memory.append({
                "id": obj["id"],
                "centroid": best["centroid"],
                "points": best["points"],
                "age": obj["age"] + 1
            })
            annotations.append(("survive", best["points"]))
        else:
            annotations.append(("die", obj["points"]))

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
# APP CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("A7DO-D • Z-Anchored Proto-Objects")
st.caption("Pre-symbolic cognition • No background time • Manual evolution")

# =====================================================
# SIDEBAR CONTROLS
# =====================================================

st.sidebar.header("World Control")
advance = st.sidebar.button("▶ Advance World")

st.sidebar.header("World Geometry")
size = st.sidebar.slider("Grid size", 16, 64, 32, step=4)

st.sidebar.header("World Motion")
square_steps = st.sidebar.slider("Square updates per advance", 1, 5, 1)

st.sidebar.header("Reaction Point Thresholds")
z_thresh = st.sidebar.slider("Z threshold (RP)", 0.1, 0.9, 0.4, step=0.05)
s_thresh = st.sidebar.slider("Σ threshold", 0.05, 0.5, 0.10, step=0.05)

st.sidebar.header("Z Anchoring")
z_anchor = st.sidebar.slider(
    "Minimum mean Z per object",
    0.1, 0.9, 0.45, step=0.05
)

st.sidebar.header("Clustering")
eps = st.sidebar.slider("Cluster radius ε", 1.0, 5.0, 2.5, step=0.5)
min_samples = st.sidebar.slider("Min RP