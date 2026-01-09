import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from core.square import Square
from core.persistence import Persistence
from core.sandys_law import compute_Z, compute_Sigma, detect_RP, compute_T_info
from core.proto_objects import cluster_reaction_points

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
# VISUALISATION
# =====================================================

col1, col2, col3 = st.columns(3)

# ---------------- Square ----------------
with col1:
    st.subheader("Square (Structure)")
    fig, ax = plt.subplots()
    ax.imshow(grid, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

# ---------------- Z ----------------
with col2:
    st.subheader("Z — Trap Strength")
    fig, ax = plt.subplots()
    ax.imshow(Z, cmap="inferno")
    ax.axis("off")
    st.pyplot(fig)

# ---------------- Σ ----------------
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
# PROTO-OBJECT OVERLAY
# =====================================================

st.divider()
st.subheader("Proto-Objects (Sensory Emergence)")

st.write(f"Total Proto-Objects: **{len(proto_objects)}**")

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

ax.set_title("Square + Proto-Objects")
ax.axis("off")

if proto_objects:
    ax.legend(loc="upper right", fontsize=8)

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
    st.metric("Proto-Objects", len(proto_objects))

with colC:
    if proto_objects:
        sizes = [len(c) for c in proto_objects]
        st.write("Proto-Object sizes:", sizes)
    else:
        st.write("No stable proto-objects detected")

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "A7DO-D • Sandy’s Law compliant • Trap → Transition → Escape • "
    "Language-free sensory emergence"
)