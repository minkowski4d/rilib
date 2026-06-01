"""
3D chart: Trading Book Size vs. Instruments (up to 5,000) and Price (EUR 0.01–400).

avg_inventory_notional = N × avg_shares × price
K-NPR = 0.16 × avg_inventory_notional

Both axes use log scale to handle the wide parameter ranges.
Colour = K-NPR / K-DTF ratio  (green = lean, red = dominant).
Includes realistic 80/20 distribution overlay.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401

MIN_INVENTORY_SHARES = 2
MAX_INVENTORY_SHARES = 5
AVG_INVENTORY_SHARES = (MAX_INVENTORY_SHARES + MIN_INVENTORY_SHARES) / 2   # 3.5
K_NPR_RATE           = 0.16
K_DTF_FIXED_EUR      = 43_200
FOR_LEVELS_EUR       = [500_000, 1_000_000, 2_000_000, 3_000_000]

# Log-spaced grids
prices      = np.logspace(np.log10(0.01), np.log10(400), 300)
instruments = np.logspace(np.log10(10), np.log10(5_000), 300)
P, N        = np.meshgrid(prices, instruments)

avg_inv     = N * AVG_INVENTORY_SHARES * P
k_npr       = avg_inv * K_NPR_RATE
ratio       = k_npr / K_DTF_FIXED_EUR

bounds  = [0, 0.5, 1.0, 2.0, ratio.max() * 1.05]
colours = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
cmap    = plt.matplotlib.colors.ListedColormap(colours)
norm    = BoundaryNorm(bounds, cmap.N)

fig = plt.figure(figsize=(18, 13), facecolor="#f8f9fa")
fig.suptitle(
    "Trading Book — Inventory Size: Notional and K-NPR Capital\n"
    r"inventory $= N \times \bar{s} \times P$"
    f"   [$\\bar{{s}}$ = {AVG_INVENTORY_SHARES} shares,  "
    f"N up to 5,000,  price EUR 0.01–400,  log–log axes]",
    fontsize=12, fontweight="bold", color="#2c3e50", y=0.98
)

# ── Panel 1: 3D surface ───────────────────────────────────────────────────────
ax3d = fig.add_subplot(221, projection="3d")
N_log = np.log10(N)
P_log = np.log10(P)
Z_k   = np.clip(avg_inv / 1_000, 0, 5_000)   # EUR thousands, cap at 5m

surf = ax3d.plot_surface(P_log, N_log, Z_k,
                         facecolors=cmap(norm(ratio)),
                         alpha=0.88, linewidth=0, antialiased=True)

# K-NPR = K-DTF iso-surface
iso = K_DTF_FIXED_EUR / K_NPR_RATE / 1_000
ax3d.plot_surface(*np.meshgrid(np.log10(prices), np.log10(instruments)),
                  np.full((300, 300), iso),
                  alpha=0.12, color="#2980b9", linewidth=0)

xtick_vals = [0.01, 0.1, 1, 10, 50, 200, 400]
ytick_vals = [10, 50, 100, 500, 1000, 5000]
ax3d.set_xticks([np.log10(v) for v in xtick_vals])
ax3d.set_xticklabels([f"€{v:g}" for v in xtick_vals], fontsize=6, rotation=15)
ax3d.set_yticks([np.log10(v) for v in ytick_vals])
ax3d.set_yticklabels([str(v) for v in ytick_vals], fontsize=6)
ax3d.set_xlabel("Avg price (log)", labelpad=8, fontsize=8)
ax3d.set_ylabel("N instruments (log)", labelpad=8, fontsize=8)
ax3d.set_zlabel("Avg inventory (EUR k)", labelpad=8, fontsize=8)
ax3d.view_init(elev=28, azim=-45)
ax3d.tick_params(axis="z", labelsize=7)
ax3d.set_title("3D — log–log axes  |  colour = K-NPR/K-DTF", fontsize=9,
               color="#7f8c8d", pad=6)

legend_els = [
    Patch(facecolor="#2ecc71", label="K-NPR < 0.5× K-DTF"),
    Patch(facecolor="#f1c40f", label="K-NPR 0.5–1× K-DTF"),
    Patch(facecolor="#e67e22", label="K-NPR 1–2× K-DTF"),
    Patch(facecolor="#e74c3c", label="K-NPR > 2× K-DTF"),
]
ax3d.legend(handles=legend_els, loc="upper left", fontsize=7, framealpha=0.85)

# ── Panel 2: 2D heatmap ───────────────────────────────────────────────────────
ax2d = fig.add_subplot(222)
cf = ax2d.contourf(prices, instruments, np.clip(k_npr / 1_000, 0, 2_000),
                   levels=np.linspace(0, 2_000, 200),
                   cmap="RdYlGn_r", alpha=0.92)
cbar = fig.colorbar(cf, ax=ax2d, fraction=0.046, pad=0.04)
cbar.set_label("K-NPR capital (EUR k)", fontsize=9)
cbar.ax.tick_params(labelsize=8)

ax2d.set_xscale("log")
ax2d.set_yscale("log")

# K-NPR = K-DTF iso-line
cs_eq = ax2d.contour(prices, instruments, k_npr,
                     levels=[K_DTF_FIXED_EUR],
                     colors=["#2980b9"], linewidths=2.5, linestyles="--")
ax2d.clabel(cs_eq, fmt=f"K-NPR=K-DTF\n€{K_DTF_FIXED_EUR:,}", fontsize=7.5)

# FOR reference iso-lines (K-NPR = 25% of FOR)
for for_val, ls in zip(FOR_LEVELS_EUR, [":", "-.", "--", "-"]):
    cs = ax2d.contour(prices, instruments, k_npr,
                      levels=[for_val * 0.25],
                      colors=["#8e44ad"], linewidths=1.3, linestyles=[ls])
    ax2d.clabel(cs, fmt=f"K-NPR=25%%\nFOR €{for_val/1e6:.0f}m", fontsize=6.5)

# Realistic universe marker: 80% cheap (avg €25) + 20% expensive (avg €200), N=5000
# Mark the two sub-populations on the chart
ax2d.scatter([25],  [4000], marker="*", s=200, color="#e74c3c",
             zorder=7, label="80%×5k instruments  @ €25")
ax2d.scatter([200], [1000], marker="*", s=200, color="#3498db",
             zorder=7, label="20%×5k instruments  @ €200")

ax2d.axvline(50, color="#e74c3c", lw=1.4, ls="-", alpha=0.5, label="EUR 50 (80% threshold)")
ax2d.set_xlabel("Average share price (EUR)", fontsize=9)
ax2d.set_ylabel("Number of instruments", fontsize=9)
ax2d.set_xlim(0.01, 400)
ax2d.set_ylim(10, 5_000)
ax2d.tick_params(labelsize=8)
ax2d.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:g}"))
ax2d.legend(fontsize=7.5, loc="upper left", framealpha=0.88)
ax2d.grid(alpha=0.2, which="both", color="#95a5a6")
ax2d.set_title("2D — K-NPR vs. K-DTF and FOR references  (log–log)",
               fontsize=9, color="#7f8c8d")
ax2d.text(0.02, 4000, "CHEAP\nLEAN K-NPR", fontsize=7.5,
          color="#27ae60", fontweight="bold", alpha=0.8)
ax2d.text(200, 4000, "K-NPR\nDOMINANT", fontsize=7.5,
          color="#c0392b", fontweight="bold", alpha=0.8)

# ── Panel 3: Window width sensitivity (log price) ────────────────────────────
ax_win = fig.add_subplot(223)
window_configs = [
    (1, 3,   2.0,  "#2ecc71", "min=1, max=3  (avg 2.0)"),
    (2, 5,   3.5,  "#3498db", "min=2, max=5  (avg 3.5)  ← current"),
    (3, 8,   5.5,  "#e67e22", "min=3, max=8  (avg 5.5)"),
    (5, 15,  10.0, "#e74c3c", "min=5, max=15 (avg 10.0)"),
]
n_fixed = 200
for _, _, avg_s, col, lbl in window_configs:
    inv_line = n_fixed * avg_s * prices
    k_line   = inv_line * K_NPR_RATE
    ax_win.plot(prices, k_line / 1_000, color=col, lw=2.2, label=lbl)

ax_win.axhline(K_DTF_FIXED_EUR / 1_000, color="#2980b9", lw=2, ls="--",
               label=f"K-DTF  (€{K_DTF_FIXED_EUR:,} @ €40m/day)")
for for_val, ls in zip([1_000_000, 2_000_000], [":", "-."]):
    ax_win.axhline(for_val * 0.25 / 1_000, color="#8e44ad", lw=1.4, ls=ls,
                   label=f"25% FOR  (FOR=€{for_val/1e6:.0f}m)")

ax_win.axvline(50, color="#e74c3c", lw=1.2, ls="-", alpha=0.4, label="EUR 50")
ax_win.set_xscale("log")
ax_win.set_xlabel("Average share price (EUR, log)", fontsize=9)
ax_win.set_ylabel("K-NPR capital (EUR k)", fontsize=9)
ax_win.set_title(f"Window Width Effect on K-NPR  (N = {n_fixed} instruments,  log price)",
                 fontsize=9, color="#7f8c8d")
ax_win.legend(fontsize=7.5, loc="upper left", framealpha=0.88)
ax_win.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:g}"))
ax_win.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x:.0f}k"))
ax_win.set_xlim(0.01, 400)
ax_win.grid(alpha=0.25, color="#95a5a6", which="both")
ax_win.fill_between(prices, 0, K_DTF_FIXED_EUR / 1_000, alpha=0.05, color="#2ecc71")

# ── Panel 4: K-NPR as % of total K-factor ────────────────────────────────────
ax_pct = fig.add_subplot(224)
k_asa_fixed = 400_000   # EUR 1bn AUM × 0.04%
n_range     = np.logspace(np.log10(10), np.log10(5_000), 300)
prices_sel  = [5, 25, 100, 400]
colors_sel  = ["#9b59b6", "#2ecc71", "#3498db", "#e74c3c"]
for px, col in zip(prices_sel, colors_sel):
    k_npr_n  = n_range * AVG_INVENTORY_SHARES * px * K_NPR_RATE
    k_total  = k_asa_fixed + k_npr_n + K_DTF_FIXED_EUR
    pct      = k_npr_n / k_total * 100
    ax_pct.plot(n_range, pct, color=col, lw=2.2, label=f"€{px}/share")

ax_pct.axhline(50, color="#7f8c8d", lw=1.2, ls="--", alpha=0.6)
ax_pct.set_xscale("log")
ax_pct.set_xlabel("Number of instruments (log)", fontsize=9)
ax_pct.set_ylabel("K-NPR / Total K-factor  (%)", fontsize=9)
ax_pct.set_title(
    f"K-NPR Share of Total K-factor\n"
    f"(K-ASA = €{k_asa_fixed/1e3:.0f}k,  K-DTF = €{K_DTF_FIXED_EUR/1e3:.0f}k,  N up to 5,000)",
    fontsize=9, color="#7f8c8d"
)
ax_pct.legend(fontsize=8, loc="lower right", framealpha=0.88)
ax_pct.set_xlim(10, 5_000)
ax_pct.set_ylim(0, 100)
ax_pct.grid(alpha=0.25, color="#95a5a6", which="both")
ax_pct.fill_between(n_range, 0, 25, alpha=0.07, color="#2ecc71")
ax_pct.fill_between(n_range, 25, 50, alpha=0.07, color="#f1c40f")
ax_pct.fill_between(n_range, 50, 100, alpha=0.07, color="#e74c3c")

# Mark realistic 80/20 universe point
# Weighted avg price = 0.8×25 + 0.2×200 = 60 EUR
k_npr_real = 5000 * AVG_INVENTORY_SHARES * 60 * K_NPR_RATE
k_tot_real = k_asa_fixed + k_npr_real + K_DTF_FIXED_EUR
pct_real   = k_npr_real / k_tot_real * 100
ax_pct.scatter([5000], [pct_real], marker="*", s=200, color="#2c3e50",
               zorder=7, label=f"5k instr. @ €60 avg → {pct_real:.0f}%")
ax_pct.legend(fontsize=7.5, loc="lower right", framealpha=0.88)

plt.tight_layout(pad=2.5)
out_path = "models/trading_book_inventory_chart.png"
plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved → {out_path}")
try:
    plt.show()
except Exception:
    pass
