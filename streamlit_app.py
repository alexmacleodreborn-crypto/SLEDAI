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
    annotations: list of tuples (state, points) where state in {"birth","survive","die"}
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
            updated_memory.append(
                {
                    "id": obj["id"],
                    "centroid": best["centroid"],
                    "points": best["points"],
                    "age": obj["age"] + 1,
                }
            )
            annotations.append(("survive", best["points"]))
        else:
            # DEATH (show last known points)
            annotations.append(("die", obj["points"]))

    # Unmatched current clusters are births
    for c in current:
        if not c["matched"]:
            updated_memory.append(
                {"id": next_id, "centroid": c["centroid"], "points": c["points"], "age": 1}
            )
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
steps = st.sidebar.slider("Square updates", 1, 50, 10)

st.sidebar.header("Reaction Point Thresholds")
z_thresh = st.sidebar.slider("Z threshold", 0.1, 0.9, 0.4, step=0.05)
s_thresh = st.sidebar.slider("Σ threshold", 0.05, 0.5, 0.15, step=0.05)

st.sidebar.header("Proto-Object Clustering")
eps = st.sidebar.slider("Cluster radius (ε)", 1.0, 5.0, 2.5, step=0.5)
min_samples = st.sidebar.slider("Min RP per object", 2, 6, 3)

st.sidebar.header("Persistence (Memory)")
persist_scale = st.sidebar.slider("Match distance scale (×ε)", 0.6, 2.5, 1.2, step=0.1)
show_deaths = st.sidebar.checkbox("Show deaths (red)", value=True)
reset_memory = st.sidebar.button("Reset proto-memory")

if reset_memory:
    st.session_state.proto_memory = []
    st.session_state.next_id = 0
    st.sidebar.success("Proto-memory reset.")

# =====================================================
# INITIALISE SYSTEM
# =====================================================

square = Square(size=size)
persist = Persistence(size)

prev = square.grid.copy()

# =====================================================
# RUN SQUARE UPDATES
# =====================================================

for _ in range(steps):
    grid = square.step()
    pmap = persist.update(grid)

# =====================================================
# SANDY’S LAW METRICS
# =====================================================

Z = compute_Z(grid, pmap)
Sigma = compute_Sigma(grid, prev)
RP = detect_RP(Z, Sigma, z_thresh=z_thresh, s_thresh=s_thresh)
T_info = compute_T_info(Z, Sigma)

RP_coords = list(zip(RP[0], RP[1]))

# =====================================================
# PROTO-OBJECTS (LAYER 2)
# =====================================================

proto_objects = cluster_reaction_points(
    RP_coords,
    eps=eps,
    min_samples=min_samples
)

# =====================================================
# PERSISTENCE UPDATE (LAYER 2.5)
# =====================================================

dist_thresh = eps * persist_scale

st.session_state.proto_memory, annotations, st.session_state.next_id = update_proto_persistence(
    proto_objects,
    st.session_state.proto_memory,
    st.session_state.next_id,
    dist_thresh=dist_thresh
)

# =====================================================
# VISUALISATION
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square (Structure)")
    fig, ax = plt.subplots()
    ax.imshow(grid, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

with col2:
    st.subheader("Z — Trap Strength")
    fig, ax = plt.subplots()
    ax.imshow(Z, cmap="inferno")
    ax.axis("off")
    st.pyplot(fig)

with col3:
    st.subheader("Σ — Entropy / Change")
    fig, ax = plt.subplots()
    ax.imshow(Sigma, cmap="viridis")
    ax.axis("off")
    st.pyplot(fig)

# =====================================================
# REACTION POINTS
# =====================================================

st.divider()
st.subheader("Reaction Points (Birth Sites)")
st.write(f"RP count: **{len(RP_coords)}**")

fig, ax = plt.subplots()
ax.imshow(grid, cmap="gray")
ax.scatter(RP[1], RP[0], c="red", s=12)
ax.set_title("Square + Reaction Points")
ax.axis("off")
st.pyplot(fig)

# =====================================================
# PROTO-OBJECT OVERLAY (CURRENT FRAME)
# =====================================================

st.divider()
st.subheader("Proto-Objects (Current Frame)")

st.write(f"Total Proto-Objects (current): **{len(proto_objects)}**")

fig, ax = plt.subplots()
ax.imshow(grid, cmap="gray")

colors = [
    "red", "cyan", "yellow", "magenta",
    "lime", "orange", "deepskyblue", "gold"
]

for i, cluster in enumerate(proto_objects):
    pts = np.array(cluster)
    ax.scatter(
        pts[:, 1],
        pts[:, 0],
        c=colors[i % len(colors)],
        s=25,
        label=f"Obj {i}"
    )

ax.set_title("Square + Proto-Objects (current)")
ax.axis("off")

if proto_objects:
    ax.legend(loc="upper right", fontsize=8)

st.pyplot(fig)

# =====================================================
# PERSISTENCE VIEW (BIRTH / SURVIVE / DEATH)
# =====================================================

st.divider()
st.subheader("Proto-Object Persistence (Memory)")

births = sum(1 for s, _ in annotations if s == "birth")
survivals = sum(1 for s, _ in annotations if s == "survive")
deaths = sum(1 for s, _ in annotations if s == "die")

st.write(f"Births: **{births}** • Survive: **{survivals}** • Deaths: **{deaths}**")
st.write(f"Match distance: **{dist_thresh:.2f}** cells (ε × {persist_scale})")

fig, ax = plt.subplots()
ax.imshow(grid, cmap="gray")

color_map = {"birth": "lime", "survive": "cyan", "die": "red"}

for state, points in annotations:
    if state == "die" and not show_deaths:
        continue
    pts = np.array(points)
    ax.scatter(
        pts[:, 1],
        pts[:, 0],
        c=color_map[state],
        s=30,
        alpha=0.85,
        label=state
    )

ax.set_title("Green=Birth • Cyan=Survive • Red=Death")
ax.axis("off")

# De-duplicate legend
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
if by_label:
    ax.legend(by_label.values(), by_label.keys(), fontsize=8, loc="upper right")

st.pyplot(fig)

# =====================================================
# SUMMARY METRICS
# =====================================================

st.divider()
st.subheader("System Summary")

colA, colB, colC = st.columns(3)

with colA:
    st.metric("Grid Size", f"{size}×{size}")
    st.metric("Square Updates", steps)

with colB:
    st.metric("Reaction Points", len(RP_coords))
    st.metric("Proto-Objects (current)", len(proto_objects))
    st.metric("Persistent Objects", len(st.session_state.proto_memory))

with colC:
    ages = [obj["age"] for obj in st.session_state.proto_memory]
    if ages:
        st.write("Object ages:", ages)
        st.write("Oldest age:", max(ages))
    else:
        st.write("No persistent objects yet (increase ε or lower min_samples).")

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "A7DO-D • Sandy’s Law compliant • Trap → Transition → Escape • "
    "Proto-object memory before language"
)