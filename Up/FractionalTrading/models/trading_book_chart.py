"""
3D chart: Order Throughput vs. Average Share Price (EUR 0.01–400) and Daily Flow.

trades/sec = F_total / (avg_price × replenishment_size × T_seconds)

Price axis uses a log scale — range spans 4 orders of magnitude (0.01 to 400).
Cheap stocks (<EUR 50) generate extreme throughput with a fixed 3-share window.
Price-adaptive replenishment lines show the mitigation.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401

REPLENISHMENT_SIZE      = 3
TRADING_SECONDS_PER_DAY = 7 * 3_600
CAPACITY_LOW            = 10
CAPACITY_HIGH           = 20
BASE_FLOW               = 40e6

# Log-spaced price grid
prices = np.logspace(np.log10(0.01), np.log10(400), 300)
flows  = np.linspace(5e6, 150e6, 200)
P, F   = np.meshgrid(prices, flows)
Z      = F / (P * REPLENISHMENT_SIZE * TRADING_SECONDS_PER_DAY)
Z_cap  = np.clip(Z, 0, 500)   # cap display at 500 trades/sec for readability

# Colour: green <10, amber 10-20, red >20
bounds  = [0, CAPACITY_LOW, CAPACITY_HIGH, 501]
colours = ["#2ecc71", "#f39c12", "#e74c3c"]
cmap    = plt.matplotlib.colors.ListedColormap(colours)
norm    = BoundaryNorm(bounds, cmap.N)

fig = plt.figure(figsize=(18, 8), facecolor="#f8f9fa")
fig.suptitle(
    "Trading Book — Order Throughput: Trades/sec vs. Share Price and Daily Flow\n"
    r"$\mathrm{trades/sec} = F_{\mathrm{total}} / (\,P \times r \times T\,)$"
    f"   [r = {REPLENISHMENT_SIZE} shares,  T = 7h,  price range EUR 0.01–400,  capped at 500/sec for display]",
    fontsize=11, fontweight="bold", color="#2c3e50", y=1.01
)

# ── Left: 3D surface ──────────────────────────────────────────────────────────
ax3d = fig.add_subplot(121, projection="3d")
P_log = np.log10(P)
surf = ax3d.plot_surface(P_log, F / 1e6, Z_cap,
                         facecolors=cmap(norm(Z)),
                         alpha=0.88, linewidth=0, antialiased=True)

# Capacity planes
p_log_range = [np.log10(0.01), np.log10(400)]
f_range     = [5, 150]
for cap, col in [(CAPACITY_LOW, "#2980b9"), (CAPACITY_HIGH, "#8e44ad")]:
    xx, yy = np.meshgrid(p_log_range, f_range)
    zz = np.full_like(xx, float(cap))
    ax3d.plot_surface(xx, yy, zz, alpha=0.15, color=col, linewidth=0)

# Base flow slice
base_z = np.clip(BASE_FLOW / (prices * REPLENISHMENT_SIZE * TRADING_SECONDS_PER_DAY),
                 0, 500)
ax3d.plot(np.log10(prices), np.full_like(prices, BASE_FLOW / 1e6), base_z,
          color="#2c3e50", lw=2.5, zorder=5, label=f"EUR {BASE_FLOW/1e6:.0f}m/day")

# X-tick labels in EUR (log spaced)
xtick_vals = [0.01, 0.1, 1, 5, 20, 50, 100, 200, 400]
ax3d.set_xticks([np.log10(v) for v in xtick_vals])
ax3d.set_xticklabels([f"€{v}" for v in xtick_vals], fontsize=6, rotation=20)
ax3d.set_xlabel("Avg price (log scale)", labelpad=10, fontsize=8)
ax3d.set_ylabel("Daily flow (EUR m)", labelpad=10, fontsize=8)
ax3d.set_zlabel("Trades / second", labelpad=10, fontsize=8)
ax3d.set_zlim(0, 500)
ax3d.view_init(elev=28, azim=-55)
ax3d.tick_params(axis="y", labelsize=7)
ax3d.tick_params(axis="z", labelsize=7)

legend_els = [
    Patch(facecolor="#2ecc71", label=f"< {CAPACITY_LOW}/sec  comfortable"),
    Patch(facecolor="#f39c12", label=f"{CAPACITY_LOW}–{CAPACITY_HIGH}/sec  within limit"),
    Patch(facecolor="#e74c3c", label=f"> {CAPACITY_HIGH}/sec  over capacity"),
    plt.Line2D([0], [0], color="#2c3e50", lw=2.5, label=f"EUR {BASE_FLOW/1e6:.0f}m/day slice"),
]
ax3d.legend(handles=legend_els, loc="upper right", fontsize=7.5, framealpha=0.85)
ax3d.set_title("3D — log(price) axis  |  Z capped at 500/sec", fontsize=9,
               color="#7f8c8d", pad=6)

# ── Right: 2D heatmap ─────────────────────────────────────────────────────────
ax2d = fig.add_subplot(122)
cf = ax2d.contourf(prices, flows / 1e6, Z_cap,
                   levels=np.linspace(0, 200, 200),
                   cmap="RdYlGn_r", alpha=0.92)
cbar = fig.colorbar(cf, ax=ax2d, fraction=0.046, pad=0.04)
cbar.set_label("Trades / second  (capped 200)", fontsize=9)
cbar.ax.tick_params(labelsize=8)

ax2d.set_xscale("log")

# Capacity contours
for cap, col, lbl in [
    (CAPACITY_LOW,  "#2980b9", f"{CAPACITY_LOW}/sec"),
    (CAPACITY_HIGH, "#8e44ad", f"{CAPACITY_HIGH}/sec"),
]:
    cs = ax2d.contour(prices, flows / 1e6, Z, levels=[cap],
                      colors=[col], linewidths=2.2, linestyles="--")
    ax2d.clabel(cs, fmt=lbl, fontsize=8)

# Base flow line
ax2d.axhline(BASE_FLOW / 1e6, color="#2c3e50", lw=1.8, ls="-",
             label=f"EUR {BASE_FLOW/1e6:.0f}m/day")

# Price-adaptive replenishment min-price verticals
replenishment_tiers = [(3, "#555", "--"), (10, "#888", ":"),
                       (30, "#aaa", "-."), (100, "#bbb", "-")]
for r, col, ls in replenishment_tiers:
    p_min = BASE_FLOW / (r * CAPACITY_HIGH * TRADING_SECONDS_PER_DAY)
    ax2d.axvline(p_min, color=col, lw=1.3, ls=ls,
                 label=f"Min price r={r}: €{p_min:.2f}")

# EUR 50 reference
ax2d.axvline(50, color="#e74c3c", lw=1.5, ls="-", alpha=0.5,
             label="EUR 50 (80% threshold)")

# Zone labels
ax2d.text(0.02, 130, "EXTREME\n>200/sec", fontsize=8, color="#c0392b",
          fontweight="bold", alpha=0.85)
ax2d.text(100,  20, "COMFORTABLE\n<10/sec", fontsize=8, color="#27ae60",
          fontweight="bold", alpha=0.85)
ax2d.text(30,   20, "WITHIN\nLIMITS", fontsize=7.5, color="#d35400",
          fontweight="bold", alpha=0.8)

ax2d.set_xlabel("Average share price (EUR, log scale)", fontsize=9)
ax2d.set_ylabel("Daily order flow (EUR million)", fontsize=9)
ax2d.set_xlim(0.01, 400)
ax2d.set_ylim(5, 150)
ax2d.tick_params(labelsize=8)
ax2d.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:g}"))
ax2d.legend(fontsize=7, loc="upper right", framealpha=0.88, ncol=2)
ax2d.grid(alpha=0.2, which="both", color="#95a5a6")
ax2d.set_title("2D Heatmap — log price axis  |  adaptive replenishment thresholds",
               fontsize=9, color="#7f8c8d")

plt.tight_layout(pad=2.0)
out_path = "models/trading_book_throughput_chart.png"
plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved → {out_path}")
try:
    plt.show()
except Exception:
    pass
