import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Architecture names
architectures = [
    "Static/Manual",
    "TVWS",
    "AFC",
    "CBRS",
    "Fully DSMS"
]

# Hand-calculated metrics (from user)
# SUE values (user/(MHz·km²·day))
sue = [1e-6, 78e-6, 93e-6, 62e-6, 62e-6]

# Coordination Index (Coordination Cost)
cindex = [43200, 10, 10.26, 10.8, 15552]

# Blocking Level (%)
bl = [98, 7.5, 5, 2.5, 0]

# For better visualization, scale SUE to micro-units (1e-6)
sue_scaled = [x * 1e6 for x in sue]  # now "users per MHz·km²·day × 1e-6"

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Scatter plot
sc = ax.scatter(sue_scaled, cindex, bl, c=bl, cmap='viridis', s=100, depthshade=True)

# Annotate each point with architecture name
for i, name in enumerate(architectures):
    ax.text(sue_scaled[i], cindex[i], bl[i]+2, name, fontsize=10, ha='center')

ax.set_xlabel('SUE (users per MHz·km²·day × 1e-6)')
ax.set_ylabel('Coordination Index')
ax.set_zlabel('Blocking Level (%)')
ax.set_title('Trade Space of Canonical Spectrum Management Architectures')

# Colorbar for BL
cb = fig.colorbar(sc, ax=ax, pad=0.1, shrink=0.7)
cb.set_label('Blocking Level (%)')

plt.tight_layout()
plt.show()
