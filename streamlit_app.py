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
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("A7DO-D • Z-Anchored Proto-Objects")
st.caption("Objects emerge from sustained trap basins (Z), not events")

# =====================================================
# SIDEBAR CONTROLS
# =====================================================

st.sidebar.header("World Geometry")
size = st.sidebar.slider("Grid size", 16, 64, 32, step=4)

st.sidebar.header("World Motion")
square_steps = st.sidebar.slider("Square updates per frame", 1, 5, 1)

st.sidebar.header("Memory Evolution")
memory_steps = st.sidebar.slider("Persistence frames", 3, 20, 10)

st.sidebar.header("Reaction Point Thresholds")
z_thresh = st.sidebar.slider("Z threshold (RP)", 0.1, 0.9, 0.4, step=0.05)
s_thresh = st.sidebar.slider("Σ threshold", 0.05, 0.5, 0.15, step=0.05)

st.sidebar.header("Z-Anchoring (IMPORTANT)")
z_anchor = st.sidebar.slider(
    "Minimum mean Z per proto-object",
    0.1, 0.9, 0.55, step=0.05,
    help="Objects only exist in sustained trap basins"
)

st.sidebar.header("Proto-Object Clustering")
eps = st.sidebar.slider("Cluster radius ε", 1.0, 5.0, 2.5, step=0.5)
min_samples = st.sidebar.slider("Min RP per object", 2, 6, 3)

persist_scale = st.sidebar.slider("Match distance (×ε)", 1.0, 2.5, 1.6, step=0.1)

show_deaths = st.sidebar.checkbox("Show deaths (red)", True)

if st.sidebar.button("Reset WORLD + MEMORY"):
    st.session_state.square = None
    st.session_state.persist = None
    st.session_state.prev = None
    st.session_state.proto_memory = []
    st.session_state.next_id = 0
    st.sidebar.success("World and memory reset")

# =====================================================
# INITIALISE / RESTORE WORLD
# =====================================================

if st.session_state.square is None or st.session_state.square.size != size:
    st.session_state.square = Square(size=size)
    st.session_state.persist = Persistence(size)
    st.session_state.prev = st.session_state.square.grid.copy()

square = st.session_state.square
persist = st.session_state.persist
prev = st.session_state.prev

dist_thresh = eps * persist_scale

# =====================================================
# MEMORY EVOLUTION LOOP
# =====================================================

all_annotations = []
final_grid = final_Z = final_Sigma = None

for _ in range(memory_steps):

    for _ in range(square_steps):
        grid = square.step()
        pmap = persist.update(grid)

    Z = compute_Z(grid, pmap)
    Sigma = compute_Sigma(grid, prev)
    RP = detect_RP(Z, Sigma, z_thresh=z_thresh, s_thresh=s_thresh)
    RP_coords = list(zip(RP[0], RP[1]))

    # -------------------------------------------------
    # Z-ANCHORED PROTO-OBJECTS (KEY CHANGE)
    # -------------------------------------------------

    raw_clusters = cluster_reaction_points(
        RP_coords,
        eps=eps,
        min_samples=min_samples
    )

    anchored_clusters = []
    for cluster in raw_clusters:
        zs = [Z[r, c] for r, c in cluster]
        if np.mean(zs) >= z_anchor:
            anchored_clusters.append(cluster)

    st.session_state.proto_memory, annotations, st.session_state.next_id = (
        update_proto_persistence(
            anchored_clusters,
            st.session_state.proto_memory,
            st.session_state.next_id,
            dist_thresh
        )
    )

    all_annotations.extend(annotations)

    final_grid = grid
    final_Z = Z
    final_Sigma = Sigma
    prev = grid.copy()

st.session_state.prev = prev

# =====================================================
# VISUALISATION
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square")
    fig, ax = plt.subplots()
    ax.imshow(final_grid, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

with col2:
    st.subheader("Z — Trap Strength")
    fig, ax = plt.subplots()
    ax.imshow(final_Z, cmap="inferno")
    ax.axis("off")
    st.pyplot(fig)

with col3:
    st.subheader("Σ — Entropy")
    fig, ax = plt.subplots()
    ax.imshow(final_Sigma, cmap="viridis")
    ax.axis("off")
    st.pyplot(fig)

# =====================================================
# PERSISTENCE VIEW
# =====================================================

st.divider()
st.subheader("Proto-Object Persistence (Z-Anchored)")

births = sum(1 for s, _ in all_annotations if s == "birth")
survivals = sum(1 for s, _ in all_annotations if s == "survive")
deaths = sum(1 for s, _ in all_annotations if s == "die")

st.write(f"Births: **{births}** • Survive: **{survivals}** • Deaths: **{deaths}**")
st.write(f"Z-anchor threshold: **{z_anchor:.2f}**")

fig, ax = plt.subplots()
ax.imshow(final_grid, cmap="gray")

color_map = {"birth": "lime", "survive": "cyan", "die": "red"}

for state, points in all_annotations:
    if state == "die" and not show_deaths:
        continue
    pts = np.array(points)
    ax.scatter(pts[:, 1], pts[:, 0], c=color_map[state], s=30, alpha=0.7)

ax.axis("off")
st.pyplot(fig)

# =====================================================
# SUMMARY
# =====================================================

st.divider()
st.subheader("System Summary")

ages = [obj["age"] for obj in st.session_state.proto_memory]

colA, colB, colC = st.columns(3)

with colA:
    st.metric("Grid Size", f"{size}×{size}")
    st.metric("Square Updates / Frame", square_steps)

with colB:
    st.metric("Persistent Objects", len(ages))
    st.metric("Oldest Object Age", max(ages) if ages else 0)

with colC:
    st.write("Object ages:", ages if ages else "—")

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "A7DO-D • Sandy’s Law • Objects persist where Z dominates Σ"
)