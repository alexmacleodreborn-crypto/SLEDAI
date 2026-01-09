import streamlit as st
import numpy as np
from core.square import Square
from core.persistence import Persistence
from core.clusters import compute_clusters
from core.sandys_law import compute_Z, compute_Sigma, detect_RP, compute_T_info

st.set_page_config(layout="wide")
st.title("A7DO-D • Square × Sandy’s Law")

size = st.sidebar.slider("Grid size", 16, 64, 32)
steps = st.sidebar.slider("Steps", 1, 50, 10)

square = Square(size=size)
persist = Persistence(size)

prev = square.grid.copy()

for _ in range(steps):
    grid = square.step()
    pmap = persist.update(grid)

Z = compute_Z(grid, pmap)
Sigma = compute_Sigma(grid, prev)
RP = detect_RP(Z, Sigma)
T_info = compute_T_info(Z, Sigma)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square")
    st.imshow(grid, cmap="gray")

with col2:
    st.subheader("Z (Trap Strength)")
    st.imshow(Z, cmap="inferno")

with col3:
    st.subheader("Σ (Entropy)")
    st.imshow(Sigma, cmap="viridis")

st.subheader("Reaction Points")
st.write(f"RP count: {len(RP[0])}")