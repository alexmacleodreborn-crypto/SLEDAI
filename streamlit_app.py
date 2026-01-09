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

import matplotlib.pyplot as plt

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Square")
    fig, ax = plt.subplots()
    ax.imshow(grid, cmap="gray")
    ax.axis("off")
    st.pyplot(fig)

with col2:
    st.subheader("Z (Trap Strength)")
    fig, ax = plt.subplots()
    ax.imshow(Z, cmap="inferno")
    ax.axis("off")
    st.pyplot(fig)

with col3:
    st.subheader("Σ (Entropy)")
    fig, ax = plt.subplots()
    ax.imshow(Sigma, cmap="viridis")
    ax.axis("off")
    st.pyplot(fig)

st.subheader("Reaction Points")
st.write(f"RP count: {len(RP[0])}")