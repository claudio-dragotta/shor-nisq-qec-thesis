"""
Genera le figure per il Capitolo 5 - Rumore Quantistico:
  - 14_bloch_channels.pdf  : effetto dei 4 canali sulla sfera di Bloch (sezione xz)
  - 15_psuccess_vs_n.pdf   : P_success vs n per diversi valori di epsilon
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────────────────────
# Figura 1: effetto dei 4 canali sulla sfera di Bloch (sezione xz)
# ──────────────────────────────────────────────────────────────

def draw_bloch_section(ax, title, rx_scale, rz_scale, rz_shift=0.0,
                       color="#2196F3", p_label=""):
    """
    Disegna la sezione xz della sfera di Bloch prima e dopo il canale.
    rx_scale : scala di r_x (e r_y implicito)
    rz_scale : scala di r_z
    rz_shift : traslazione di r_z (per amplitude damping)
    """
    theta = np.linspace(0, 2 * np.pi, 300)

    # Sfera originale (cerchio unitario in xz)
    x_orig = np.cos(theta)
    z_orig = np.sin(theta)
    ax.plot(x_orig, z_orig, color="lightgray", lw=1.2, ls="--", zorder=1)

    # Sfera trasformata (ellisse + traslazione)
    x_new = rx_scale * np.cos(theta)
    z_new = rz_scale * np.sin(theta) + rz_shift
    ax.fill(x_new, z_new, alpha=0.25, color=color, zorder=2)
    ax.plot(x_new, z_new, color=color, lw=2.0, zorder=3)

    # Assi e poli
    ax.axhline(0, color="black", lw=0.6, zorder=0)
    ax.axvline(0, color="black", lw=0.6, zorder=0)
    ax.plot(0,  1, 'k.', ms=5)
    ax.plot(0, -1, 'k.', ms=5)
    ax.text( 0.05,  1.05, r"$|0\rangle$", fontsize=8)
    ax.text( 0.05, -1.15, r"$|1\rangle$", fontsize=8)
    ax.text( 1.05,  0.05, r"$x$",         fontsize=8)
    ax.text( 0.05,  0,    r"",             fontsize=8)

    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    ax.axis("off")

    # Etichetta parametro
    if p_label:
        ax.text(0, -1.28, p_label, ha="center", fontsize=8, color="gray")


fig, axes = plt.subplots(2, 2, figsize=(8, 8))
fig.suptitle("Effetto dei quattro canali di rumore sulla sfera di Bloch\n"
             "(sezione nel piano $xz$, tratteggio = sfera ideale)",
             fontsize=11, y=0.98)

p = 0.35   # parametro esemplificativo per canali discreti
gamma = 0.5  # per amplitude damping

# Bit Flip: contrae r_y, r_z → in sezione xz contrae solo r_z
draw_bloch_section(axes[0, 0],
                   "Canale Bit Flip",
                   rx_scale=1.0,
                   rz_scale=1 - 2*p,
                   color="#E53935",
                   p_label=f"$p = {p}$")

# Phase Flip: contrae r_x, r_y → in sezione xz contrae r_x
draw_bloch_section(axes[0, 1],
                   "Canale Phase Flip",
                   rx_scale=1 - 2*p,
                   rz_scale=1.0,
                   color="#8E24AA",
                   p_label=f"$p = {p}$")

# Depolarizzante: contrae isotropicamente di (1 - 4p/3)
s = 1 - 4*p/3
draw_bloch_section(axes[1, 0],
                   "Canale Depolarizzante",
                   rx_scale=s,
                   rz_scale=s,
                   color="#F57C00",
                   p_label=f"$p = {p}$,  fattore $= 1-4p/3 = {s:.2f}$")

# Amplitude Damping: contrae verso |0> (polo nord, z=+1)
draw_bloch_section(axes[1, 1],
                   "Canale Amplitude Damping",
                   rx_scale=np.sqrt(1 - gamma),
                   rz_scale=(1 - gamma),
                   rz_shift=gamma,
                   color="#1E88E5",
                   p_label=f"$\\gamma = {gamma}$")

plt.tight_layout(rect=[0, 0, 1, 0.96])
out1 = os.path.join(OUTPUT_DIR, "14_bloch_channels.pdf")
plt.savefig(out1, bbox_inches="tight")
plt.close()
print(f"Salvato: {out1}")


# ──────────────────────────────────────────────────────────────
# Figura 2: P_success vs n per diversi valori di epsilon
# ──────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(7, 4.5))

n_vals = np.linspace(2, 30, 300)
epsilons = [1e-4, 5e-4, 1e-3, 5e-3, 1e-2]
colors   = ["#1565C0", "#1E88E5", "#F57C00", "#E53935", "#B71C1C"]
labels   = [r"$\epsilon = 10^{-4}$",
            r"$\epsilon = 5\times10^{-4}$",
            r"$\epsilon = 10^{-3}$",
            r"$\epsilon = 5\times10^{-3}$",
            r"$\epsilon = 10^{-2}$"]

for eps, col, lbl in zip(epsilons, colors, labels):
    L = n_vals ** 3          # numero di gate ~ O(n^3)
    P = (1 - eps) ** L
    ax.semilogy(n_vals, P, color=col, lw=2, label=lbl)

# Linea di riferimento al 50% e 5%
ax.axhline(0.5,  color="gray", ls=":",  lw=1)
ax.axhline(0.05, color="gray", ls="--", lw=1)
ax.text(30.2, 0.52,  "50%",  va="center", fontsize=8, color="gray")
ax.text(30.2, 0.052, "5%",   va="center", fontsize=8, color="gray")

# Punto specifico: n=15, eps=1e-3
eps_ref = 1e-3
n_ref   = 15
P_ref   = (1 - eps_ref) ** (n_ref**3)
ax.plot(n_ref, P_ref, "ko", ms=6, zorder=5)
ax.annotate(f"$n=15$, $\\epsilon=10^{{-3}}$\n$P_{{\\rm success}} \\approx {P_ref:.3f}$",
            xy=(n_ref, P_ref), xytext=(18, 0.015),
            fontsize=8,
            arrowprops=dict(arrowstyle="->", color="black", lw=1),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.8))

ax.set_xlabel("Numero di bit di $N$ (dimensione dell'input $n$)", fontsize=10)
ax.set_ylabel("$P_{\\mathrm{success}}$ (scala logaritmica)", fontsize=10)
ax.set_title("Probabilità di successo dell'algoritmo di Shor\n"
             r"in funzione di $n$, modello depolarizzante $\mathcal{E}_{dep}$",
             fontsize=10)
ax.legend(fontsize=9, loc="upper right")
ax.set_xlim(2, 30)
ax.set_ylim(1e-5, 1.1)
ax.grid(True, which="both", ls=":", alpha=0.4)

plt.tight_layout()
out2 = os.path.join(OUTPUT_DIR, "15_psuccess_vs_n.pdf")
plt.savefig(out2, bbox_inches="tight")
plt.close()
print(f"Salvato: {out2}")

print("Done.")
