import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label

from core.square import Square
from core.persistence import Persistence
from core.sandys_law import compute_Z, compute_Sigma, detect_RP

# =====================================================
# SESSION STATE
# =====================================================

if "square" not in st.session_state:
    st.session_state.square = None
    st.session_state.persist = None
    st.session_state.prev = None
    st.session_state.frame = 0

if "basin_memory" not in st.session_state:
    st.session_state.basin_memory = {}
    st.session_state.next_id = 0

# =====================================================
# Z-BASIN EXTRACTION
# =====================================================

def extract_z_basins(Z, z_thresh):
    """
    Returns list of basins, each basin is list of (r,c)
    """
    mask = Z >= z_thresh
    labeled, n = label(mask)

    basins = []
    for i in range(1, n + 1):
        coords = np.argwhere(labeled == i)
        if len(coords) > 0:
            basins.append([tuple(p) for p in coords])
    return basins

def centroid(points):
    pts = np.array(points)
    return np.mean(pts, axis=0)

# =====================================================
# APP CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("A7DO-D • Z-Basin Objects")
st.caption("Structure → Stress → Awareness (no event hallucination)")

# =====================================================
# SIDEBAR CONTROLS
# =====================================================

st.sidebar.header("World Control")
advance = st.sidebar.button("▶ Advance World")

st.sidebar.header("World Geometry")
size = st.sidebar.slider("Grid size", 16, 64, 32, step=4)

st.sidebar.header("Dynamics")
square_steps = st.sidebar.slider("Square updates per step", 1, 4, 1)

st.sidebar.header("Z-Basin Definition")
z_basin_thresh = st.sidebar.slider(
    "Z basin threshold",
    0.2, 0.8, 0.35, step=0.05
)

st.sidebar.header("Σ / Reaction Points")
s_thresh = st.sidebar.slider(
    "Σ threshold",
    0.05, 0.5, 0.10, step=0.05
)

st.sidebar.header("Persistence")
match_dist = st.sidebar.slider(
    "Basin match distance",
    1.0, 6.0, 3.0, step=0.5
)

if st.sidebar.button("Reset WORLD + MEMORY"):
    st.session_state.square = None
    st.session_state.persist = None
    st.session_state.prev = None
    st.session_state.basin_memory = {}
    st.session_state.next_id = 0
    st.session_state.frame = 0
    st.sidebar.success("Reset complete")

# =====================================================
# INITIALISE WORLD
# =====================================================

if st.session_state.square is None or st.session_state.square.size != size:
    st.session_state.square = Square(size=size)
    st.session_state.persist = Persistence(size)
    st.session_state.prev = st.session_state.square.grid.copy()

square = st.session_state.square
persist = st.session_state.persist
prev = st.session_state.prev

# =====================================================
# ADVANCE WORLD
# =====================================================

annotations = []

if advance:
    st.session_state.frame += 1

    for _ in range(square_steps):
        grid = square.step()
        pmap = persist.update(grid)

    Z = compute_Z(grid, pmap)
    Sigma = compute_Sigma(grid, prev)

    # --- Z-BASIN OBJECTS ---
    basins = extract_z_basins(Z, z_basin_thresh)

    new_memory = {}
    used_prev = set()

    for basin in basins:
        c = centroid(basin)

        best_id = None
        best_dist = None

        for obj_id, obj in st.session_state.basin_memory.items():
            d = np.linalg.norm(c - obj["centroid"])
            if d <= match_dist and (best_dist is None or d < best_dist):
                best_id = obj_id
                best_dist = d

        if best_id is not None:
            # SURVIVE
            new_memory[best_id] = {
                "centroid": c,
                "points": basin,
                "age": st.session_state.basin_memory[best_id]["age"] + 1
            }
            used_prev.add(best_id)
            annotations.append(("survive", basin))
        else:
            # BIRTH
            obj_id = st.session_state.next_id
            st.session_state.next_id += 1
            new_memory[obj_id] = {
                "centroid": c,
                "points": basin,
                "age": 1
            }
            annotations.append(("birth", basin))

    # DEATHS
    for obj_id, obj in st.session_state.basin_memory.items():
        if obj_id not in used_prev:
            annotations.append(("die", obj["points"]))

    st.session_state.basin_memory = new_memory
    st.session_state.prev = grid.copy()

else:
    grid = square.grid
    Z = compute_Z(grid, persist.update(grid))
    Sigma = compute_Sigma(grid, prev)

# =====================================================
# REACTION POINTS (ATTENTION ONLY)
# =====================================================

RP = detect_RP(Z, Sigma, z_thresh=0.0, s_thresh=s_thresh)
RP_coords = list(zip(RP[0], RP[1]))

# =====================================================
# VISUALS
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square")
    fig, ax = plt.subplots()
    ax.imshow(grid, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

with col2:
    st.subheader("Z (Structure)")
    fig, ax = plt.subplots()
    ax.imshow(Z, cmap="inferno")
    ax.axis("off")
    st.pyplot(fig)

with col3:
    st.subheader("Σ (Change)")
    fig, ax = plt.subplots()
    ax.imshow(Sigma, cmap="viridis")
    ax.axis("off")
    st.pyplot(fig)

# =====================================================
# Z-BASIN OBJECT VIEW
# =====================================================

st.divider()
st.subheader(f"Z-Basin Objects — Frame {st.session_state.frame}")

fig, ax = plt.subplots()
ax.imshow(grid, cmap="gray")

colors = {"birth": "lime", "survive": "cyan", "die": "red"}

for state, basin in annotations:
    pts = np.array(basin)
    ax.scatter(pts[:,1], pts[:,0], c=colors[state], s=25, alpha=0.9)

# Overlay attention (RP)
if RP_coords:
    rp = np.array(RP_coords)
    ax.scatter(rp[:,1], rp[:,0], c="white", s=8, alpha=0.4)

ax.set_title("Green=Birth • Cyan=Survive • Red=Death • White=Attention (Σ)")
ax.axis("off")
st.pyplot(fig)

# =====================================================
# SUMMARY
# =====================================================

st.divider()
st.subheader("System Summary")

births = sum(1 for s,_ in annotations if s == "birth")
survive = sum(1 for s,_ in annotations if s == "survive")
deaths = sum(1 for s,_ in annotations if s == "die")

ages = [obj["age"] for obj in st.session_state.basin_memory.values()]

colA, colB, colC = st.columns(3)

with colA:
    st.metric("Frame", st.session_state.frame)
    st.metric("Active Objects", len(ages))

with colB:
    st.metric("Births", births)
    st.metric("Deaths", deaths)

with colC:
    st.write("Object ages:", ages if ages else "—")

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "A7DO-D Phase II • Objects defined by structure (Z), not events (Σ). "
    "Stress reveals — it does not create."
)