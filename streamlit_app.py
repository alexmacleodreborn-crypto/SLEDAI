import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from core.square import Square
from core.persistence import Persistence
from core.sandys_law import compute_Z, compute_Sigma, detect_RP, compute_T_info
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

def update_proto_persistence(current_clusters, memory, next_id, dist_thresh=3.0):
    """
    Match current proto-objects to previous ones by centroid distance.
    Returns updated memory, annotations, and next_id.
    annotations: list of tuples (state, points)
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
                "age": obj["age"] + 1,
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
                "age": 1,
            })
            annotations.append(("birth", c["points"]))
            next_id += 1

    return updated_memory, annotations, next_id

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("A7DO-D • Square × Sandy’s Law")
st.caption("Developmental AI • Structure-first • No language required")

# =====================================================
# SIDEBAR CONTROLS
# =====================================================

st.sidebar.header("Simulation Controls")
size = st.sidebar.slider("Grid size", 16, 64, 32, step=4)
square_steps = st.sidebar.slider("Square updates per frame", 1, 20, 3)

st.sidebar.header("Memory Evolution")
memory_steps = st.sidebar.slider(
    "Persistence steps (frames)",
    1, 20, 6,
    help="Number of successive frames for proto-object memory"
)

st.sidebar.header("Reaction Point Thresholds")
z_thresh = st.sidebar.slider("Z threshold", 0.1, 0.9, 0.4, step=0.05)
s_thresh = st.sidebar.slider("Σ threshold", 0.05, 0.5, 0.15, step=0.05)

st.sidebar.header("Proto-Object Clustering")
eps = st.sidebar.slider("Cluster radius (ε)", 1.0, 5.0, 2.5, step=0.5)
min_samples = st.sidebar.slider("Min RP per object", 2, 6, 3)

st.sidebar.header("Persistence Matching")
persist_scale = st.sidebar.slider("Match distance (×ε)", 0.6, 2.5, 1.2, step=0.1)
show_deaths = st.sidebar.checkbox("Show deaths (red)", value=True)

if st.sidebar.button("Reset proto-memory"):
    st.session_state.proto_memory = []
    st.session_state.next_id = 0
    st.sidebar.success("Proto-memory reset")

# =====================================================
# INITIALISE WORLD
# =====================================================

square = Square(size=size)
persist = Persistence(size)
prev = square.grid.copy()

# =====================================================
# MEMORY EVOLUTION LOOP (THIS IS THE FIX)
# =====================================================

all_annotations = []
final_grid = None
final_Z = None
final_Sigma = None
final_RP_coords = []
final_proto_objects = []

dist_thresh = eps * persist_scale

for step in range(memory_steps):

    # Advance world slightly
    for _ in range(square_steps):
        grid = square.step()
        pmap = persist.update(grid)

    Z = compute_Z(grid, pmap)
    Sigma = compute_Sigma(grid, prev)
    RP = detect_RP(Z, Sigma, z_thresh=z_thresh, s_thresh=s_thresh)
    RP_coords = list(zip(RP[0], RP[1]))

    proto_objects = cluster_reaction_points(
        RP_coords,
        eps=eps,
        min_samples=min_samples
    )

    st.session_state.proto_memory, annotations, st.session_state.next_id = (
        update_proto_persistence(
            proto_objects,
            st.session_state.proto_memory,
            st.session_state.next_id,
            dist_thresh=dist_thresh
        )
    )

    all_annotations.extend(annotations)

    # Store last frame for display
    final_grid = grid
    final_Z = Z
    final_Sigma = Sigma
    final_RP_coords = RP_coords
    final_proto_objects = proto_objects
    prev = grid.copy()

# =====================================================
# VISUALISATION
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square (Structure)")
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
    st.subheader("Σ — Entropy / Change")
    fig, ax = plt.subplots()
    ax.imshow(final_Sigma, cmap="viridis")
    ax.axis("off")
    st.pyplot(fig)

# =====================================================
# REACTION POINTS
# =====================================================

st.divider()
st.subheader("Reaction Points")
st.write(f"RP count (final frame): **{len(final_RP_coords)}**")

fig, ax = plt.subplots()
ax.imshow(final_grid, cmap="gray")
if final_RP_coords:
    r, c = zip(*final_RP_coords)
    ax.scatter(c, r, c="red", s=12)
ax.axis("off")
st.pyplot(fig)

# =====================================================
# PERSISTENCE VIEW
# =====================================================

st.divider()
st.subheader("Proto-Object Persistence (Memory)")

births = sum(1 for s, _ in all_annotations if s == "birth")
survivals = sum(1 for s, _ in all_annotations if s == "survive")
deaths = sum(1 for s, _ in all_annotations if s == "die")

st.write(
    f"Births: **{births}** • "
    f"Survive: **{survivals}** • "
    f"Deaths: **{deaths}**"
)
st.write(f"Match distance: **{dist_thresh:.2f}** cells")

fig, ax = plt.subplots()
ax.imshow(final_grid, cmap="gray")

color_map = {"birth": "lime", "survive": "cyan", "die": "red"}

for state, points in all_annotations:
    if state == "die" and not show_deaths:
        continue
    pts = np.array(points)
    ax.scatter(
        pts[:, 1],
        pts[:, 0],
        c=color_map[state],
        s=30,
        alpha=0.7,
        label=state
    )

ax.axis("off")

handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
if by_label:
    ax.legend(by_label.values(), by_label.keys(), fontsize=8)

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
    st.metric("Memory Frames", memory_steps)

with colB:
    st.metric("Persistent Objects", len(ages))
    st.metric("Oldest Object Age", max(ages) if ages else 0)

with colC:
    if ages:
        st.write("Object ages:", ages)
    else:
        st.write("No persistent objects yet")

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "A7DO-D • Sandy’s Law compliant • "
    "Proto-object memory emerges before language"
)