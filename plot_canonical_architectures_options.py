import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import seaborn as sns
from adjustText import adjust_text

# For radar plot
from math import pi

# Data
architectures = [
    "Static/Manual",
    "TVWS",
    "AFC",
    "CBRS",
    "DSMS"
]
sue = [1e-6, 78e-6, 93e-6, 62e-6, 107e-6]
cindex = [43200, 10, 10.26, 10.8, 15552]
bl = [98, 7.5, 5, 2.5, 0]
sue_scaled = [x * 1e6 for x in sue]  # SUE in micro-units for clarity

# Manual label offsets for each architecture (tuned for clarity)
# Format: (x_offset, y_offset, ha, va)
label_offsets = {
    "Static/Manual":   (-3, 2000, 'right', 'bottom'),
    "TVWS":            (0, -1100, 'center', 'top'),
    "AFC":             (0, 1100, 'center', 'bottom'),
    "CBRS":            (0, -1100, 'center', 'top'),
    "DSMS":            (6, 0, 'left', 'center'),
}

# Custom label placement for each architecture
label_placement = {
    "Static/Manual":   {'ha': 'left',  'va': 'center', 'dx': 5,   'dy': 0},
    "CBRS":           {'ha': 'center','va': 'bottom', 'dx': 0,   'dy': 1200},
    "AFC":            {'ha': 'center','va': 'bottom', 'dx': 0,   'dy': 1200},
    "TVWS":           {'ha': 'center','va': 'bottom', 'dx': 0,   'dy': 1200},
    "DSMS":           {'ha': 'right', 'va': 'center', 'dx': -5,  'dy': 0},
}

def get_smart_offset(x, y, xvals, yvals):
    # Compute relative position in the plot
    x_min, x_max = min(xvals), max(xvals)
    y_min, y_max = min(yvals), max(yvals)
    # Default offset values
    dx, dy = 0, 0
    ha, va = 'center', 'center'
    # Horizontal placement
    if x < x_min + 0.2*(x_max-x_min):
        ha = 'left'; dx = 5
    elif x > x_max - 0.2*(x_max-x_min):
        ha = 'right'; dx = -5
    else:
        ha = 'center'; dx = 0
    # Vertical placement
    if y > y_max - 0.2*(y_max-y_min):
        va = 'bottom'; dy = -5
    elif y < y_min + 0.2*(y_max-y_min):
        va = 'top'; dy = 5
    else:
        va = 'center'; dy = 0
    return dx, dy, ha, va

# --- 1. 2D Scatter Plot with Color and Size Encoding ---
plt.figure(figsize=(8,6))
scatter = plt.scatter(sue_scaled, cindex, c=bl, s=120, cmap='coolwarm', edgecolor='black')
for i, name in enumerate(architectures):
    opts = label_placement[name]
    plt.text(sue_scaled[i] + opts['dx'], cindex[i] + opts['dy'], name, fontsize=10, ha=opts['ha'], va=opts['va'], fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
# Add utopia point (max SUE, min cindex, min BL)
utopia_sue = max(sue_scaled)
utopia_cindex = min(cindex)
utopia_bl = min(bl)
plt.scatter([utopia_sue], [utopia_cindex], marker='*', s=300, c='gold', edgecolor='black', label='Utopia Point', zorder=5)
plt.xlabel('SUE (users per MHz·km²·day × 1e-6)')
plt.ylabel('Coordination Index')
cbar = plt.colorbar(scatter)
cbar.set_label('Blocking Probability (%)')
plt.title('By Hand Trade Space')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# --- 2. Pairwise 2D Plots as Separate Figures with User-Specified Label Placement ---
# SUE vs Coordination Index
plt.figure(figsize=(7,5))
axs0 = plt.gca()
axs0.scatter(sue_scaled, cindex, c='tab:blue')
# User-specified label placement
sue_ci_labels = {
    "Static/Manual": {'dx': 5,  'dy': 0,    'ha': 'left',   'va': 'center'},
    "CBRS":         {'dx': 0,  'dy': 1400, 'ha': 'center', 'va': 'bottom'},
    "AFC":          {'dx': 0,  'dy': 1400, 'ha': 'center', 'va': 'bottom'},
    "TVWS":         {'dx': 0,  'dy': 1400, 'ha': 'center', 'va': 'bottom'},
    "DSMS":         {'dx': -5, 'dy': 0,    'ha': 'right',  'va': 'center'},
}
for i, name in enumerate(architectures):
    opts = sue_ci_labels[name]
    axs0.text(sue_scaled[i] + opts['dx'], cindex[i] + opts['dy'], name, fontsize=10, ha=opts['ha'], va=opts['va'], fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
axs0.scatter([utopia_sue], [utopia_cindex], marker='*', s=300, c='gold', edgecolor='black', label='Utopia Point', zorder=5)
axs0.set_xlabel('SUE (users per MHz·km²·day × 1e-6)')
axs0.set_ylabel('Coordination Index')
axs0.set_title('SUE vs Coordination Index')
axs0.legend()
axs0.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# SUE vs BL
plt.figure(figsize=(7,5))
axs1 = plt.gca()
axs1.scatter(sue_scaled, bl, c='tab:orange')
# User-specified label placement
sue_bl_labels = {
    "Static/Manual": {'dx': 5,  'dy': 0,   'ha': 'left',   'va': 'center'},
    "CBRS":         {'dx': 0,  'dy': 2.5, 'ha': 'center', 'va': 'bottom'},
    "AFC":          {'dx': 0,  'dy': 2.5, 'ha': 'center', 'va': 'bottom'},
    "TVWS":         {'dx': 0,  'dy': 2.5, 'ha': 'center', 'va': 'bottom'},
    "DSMS":         {'dx': 5, 'dy': 0,   'ha': 'left',  'va': 'center'},
}
for i, name in enumerate(architectures):
    opts = sue_bl_labels[name]
    axs1.text(sue_scaled[i] + opts['dx'], bl[i] + opts['dy'], name, fontsize=10, ha=opts['ha'], va=opts['va'], fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
# Move utopia point to bottom right corner
utopia_sue_bl_x = max(sue_scaled) + 20
utopia_sue_bl_y = min(bl) - 10
axs1.scatter([utopia_sue_bl_x], [utopia_sue_bl_y], marker='*', s=300, c='gold', edgecolor='black', label='Utopia Point', zorder=5)
axs1.set_xlabel('SUE (users per MHz·km²·day × 1e-6)')
axs1.set_ylabel('Blocking Level (%)')
axs1.set_title('SUE vs BL')
axs1.legend()
axs1.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# BL vs Coordination Index
plt.figure(figsize=(7,5))
axs2 = plt.gca()
axs2.scatter(bl, cindex, c='tab:green')
# User-specified label placement
bl_ci_labels = {
    "Static/Manual": {'dx': -5,  'dy': 0,    'ha': 'right',   'va': 'center'},
    "DSMS":         {'dx': 5,  'dy': 0,    'ha': 'left',   'va': 'center'},
    "AFC":          {'dx': 3,  'dy': 1400, 'ha': 'right', 'va': 'bottom'},
    "TVWS":         {'dx': -8,  'dy': -1400, 'ha': 'center', 'va': 'top'},
    "CBRS":         {'dx': 8,  'dy': -1400, 'ha': 'left', 'va': 'bottom'},
}
for i, name in enumerate(architectures):
    opts = bl_ci_labels[name]
    axs2.text(bl[i] + opts['dx'], cindex[i] + opts['dy'], name, fontsize=10, ha=opts['ha'], va=opts['va'], fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))
# Move utopia point to bottom right corner
utopia_bl_ci_x = min(bl)
utopia_bl_ci_y = min(cindex) - 5000
axs2.scatter([utopia_bl_ci_x], [utopia_bl_ci_y], marker='*', s=300, c='gold', edgecolor='black', label='Utopia Point', zorder=5)
axs2.set_xlabel('Blocking Level (%)')
axs2.set_ylabel('Coordination Index')
axs2.set_title('BL vs Coordination Index')
axs2.legend()
axs2.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# --- 3. Enhanced 3D Scatter Plot ---
# fig = plt.figure(figsize=(10,8))
# ax = fig.add_subplot(111, projection='3d')
# sc = ax.scatter(sue_scaled, cindex, bl, c=bl, cmap='plasma', s=120, depthshade=True, edgecolor='k')
# for i, name in enumerate(architectures):
#     dx, dy, dz, ha, va = label_offsets[name][0], label_offsets[name][1], 2, label_offsets[name][2], label_offsets[name][3]
#     ax.text(sue_scaled[i] + dx, cindex[i] + dy, bl[i] + dz, name, fontsize=10, ha=ha, va=va, fontweight='bold', zorder=5)
# ax.set_xlabel('SUE (users per MHz·km²·day × 1e-6)')
# ax.set_ylabel('Coordination Index')
# ax.set_zlabel('Blocking Level (%)')
# ax.set_title('3D Trade Space')
# cb = fig.colorbar(sc, ax=ax, pad=0.1, shrink=0.7)
# cb.set_label('Blocking Level (%)')
# plt.tight_layout()
# plt.show()

# --- 4. Radar/Spider Plot ---
# sue_norm = [(x - min(sue_scaled))/(max(sue_scaled)-min(sue_scaled)) for x in sue_scaled]
# cindex_norm = [(x - min(cindex))/(max(cindex)-min(cindex)) for x in cindex]
# bl_norm = [(x - min(bl))/(max(bl)-min(bl)) for x in bl]
# metrics = ['SUE', 'Coordination Index', 'Blocking Level']
# values = list(zip(sue_norm, cindex_norm, bl_norm))
# N = len(metrics)
# angles = [n / float(N) * 2 * pi for n in range(N)]
# angles += angles[:1]  # Complete the loop
# plt.figure(figsize=(8,8))
# for i, arch in enumerate(architectures):
#     vals = list(values[i])
#     vals += vals[:1]
#     plt.polar(angles, vals, label=arch, linewidth=2)
# plt.xticks(angles[:-1], metrics)
# plt.title('Radar Plot: Normalized Metrics')
# plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
# plt.tight_layout()
# plt.show()
