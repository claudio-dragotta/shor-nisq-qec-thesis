"""
Genera due figure:
  1. circuit_bell.png  — circuito che prepara lo stato di Bell |Φ+⟩
  2. circuit_gates.png — tavola dei simboli delle porte principali
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def wire(ax, x0, x1, y, lw=1.6, color='black'):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, zorder=1)

def gate_box(ax, x, y, label, w=0.55, h=0.45, fs=13):
    rect = mpatches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                   boxstyle="round,pad=0.04",
                                   linewidth=1.4, edgecolor='black',
                                   facecolor='white', zorder=3)
    ax.add_patch(rect)
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fs, zorder=4)

def measure_sym(ax, x, y, w=0.55, h=0.45):
    rect = mpatches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                   boxstyle="round,pad=0.04",
                                   linewidth=1.4, edgecolor='black',
                                   facecolor='lightyellow', zorder=3)
    ax.add_patch(rect)
    t = np.linspace(np.pi, 0, 80)
    r = 0.13
    ax.plot(x + r*np.cos(t), y - h/4 + r*np.sin(t),
            color='black', lw=1.2, zorder=5)
    ax.annotate('', xy=(x + 0.16, y + 0.08),
                xytext=(x, y - h/4),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.2),
                zorder=5)

def cnot_gate(ax, xc, yctrl, ytgt):
    ax.plot(xc, yctrl, 'o', color='black', markersize=8, zorder=4)
    ax.plot([xc, xc], [yctrl, ytgt], color='black', lw=1.6, zorder=2)
    r = 0.22
    circle = plt.Circle((xc, ytgt), r, color='white',
                         ec='black', lw=1.6, zorder=3)
    ax.add_patch(circle)
    ax.plot([xc - r, xc + r], [ytgt, ytgt], color='black', lw=1.4, zorder=4)
    ax.plot([xc, xc], [ytgt - r, ytgt + r], color='black', lw=1.4, zorder=4)

# ─────────────────────────────────────────────
# FIGURA 1: Circuito stato di Bell |Φ+⟩
# ─────────────────────────────────────────────
fig1, ax1 = plt.subplots(figsize=(7.5, 3.2))
ax1.set_xlim(0, 7.5)
ax1.set_ylim(-0.6, 1.8)
ax1.axis('off')

y0, y1 = 1.2, 0.2

ax1.text(0.15, y0, r'$|0\rangle$', ha='left', va='center', fontsize=13)
ax1.text(0.15, y1, r'$|0\rangle$', ha='left', va='center', fontsize=13)

wire(ax1, 0.7, 7.2, y0)
wire(ax1, 0.7, 7.2, y1)

gate_box(ax1, 1.8, y0, r'$H$', fs=14)
cnot_gate(ax1, 3.2, y0, y1)
measure_sym(ax1, 5.0, y0)
measure_sym(ax1, 5.0, y1)

for dy in [-0.04, 0.04]:
    ax1.plot([5.28, 6.8], [y0 + dy, y0 + dy], color='black', lw=1.0)
    ax1.plot([5.28, 6.8], [y1 + dy, y1 + dy], color='black', lw=1.0)

ax1.text(6.9, y0, r'$c_0$', ha='left', va='center', fontsize=12)
ax1.text(6.9, y1, r'$c_1$', ha='left', va='center', fontsize=12)

ax1.text(2.5, 1.65, r'$H\otimes I$', ha='center', va='center',
         fontsize=10, color='gray')
ax1.text(3.2, 1.65, r'$\mathrm{CNOT}$', ha='center', va='center',
         fontsize=10, color='gray')
ax1.annotate('', xy=(2.5, y0 + 0.24), xytext=(2.5, 1.58),
             arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))
ax1.annotate('', xy=(3.2, (y0+y1)/2 + 0.24), xytext=(3.2, 1.58),
             arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))

ax1.text(3.75, -0.38,
         r'Output: $|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$',
         ha='center', va='center', fontsize=12,
         bbox=dict(boxstyle='round,pad=0.3', fc='#f0f8ff', ec='steelblue', lw=1))

ax1.set_title(r'Circuito di preparazione dello stato di Bell $|\Phi^+\rangle$',
              fontsize=13, pad=10)

fig1.tight_layout()
fig1.savefig('circuit_bell.pdf', dpi=300, bbox_inches='tight',
             facecolor='white', format='pdf')
fig1.savefig('circuit_bell.png', dpi=300, bbox_inches='tight',
             facecolor='white')
print("Bell circuit saved.")

# ─────────────────────────────────────────────
# FIGURA 2: Tavola simboli porte — layout unico, niente inset
# ─────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(11, 4.2))
ax2.set_xlim(0, 11)
ax2.set_ylim(-0.9, 3.4)
ax2.axis('off')

# ── Riga 1: porte a singolo qubit ──
y_sq = 2.5   # y del filo singolo qubit — più in alto per dare spazio alle etichette
xs = [1.2, 2.9, 4.6, 6.3, 8.0]
labels_sq  = [r'$X$', r'$Y$', r'$Z$', r'$H$', r'$R_\phi$']
descs_sq   = ['NOT / Bit Flip', 'Pauli-Y', 'Phase Flip', 'Hadamard', 'Gate di Fase']

wire(ax2, 0.3, 9.3, y_sq)
for x, lbl, desc in zip(xs, labels_sq, descs_sq):
    gate_box(ax2, x, y_sq, lbl, w=0.6, h=0.46, fs=14)
    ax2.text(x, y_sq - 0.52, desc, ha='center', va='top', fontsize=9,
             color='#333333')

# Titoletto riga
ax2.text(0.0, y_sq + 0.58, 'Porte a singolo qubit:',
         ha='left', va='center', fontsize=10, color='#555555', style='italic')

# ── Riga 2: porta CNOT a due qubit ──
y_ctrl = 0.70
y_tgt  = -0.10
x_cnot = 1.6

# fili
wire(ax2, 0.3, 3.2, y_ctrl)
wire(ax2, 0.3, 3.2, y_tgt)

ax2.text(0.22, y_ctrl, r'$q_c$', ha='right', va='center', fontsize=11)
ax2.text(0.22, y_tgt,  r'$q_t$', ha='right', va='center', fontsize=11)
cnot_gate(ax2, x_cnot, y_ctrl, y_tgt)

ax2.text(x_cnot, y_tgt - 0.38, 'CNOT  (Controlled-NOT)',
         ha='center', va='top', fontsize=9, color='#333333')

ax2.text(0.0, y_ctrl + 0.42, 'Porta a due qubit:',
         ha='left', va='center', fontsize=10, color='#555555', style='italic')

# separatore orizzontale — posizionato a metà tra le due righe
ax2.plot([0.0, 10.8], [1.30, 1.30], color='#cccccc', lw=1.0, ls='--')

ax2.set_title('Principali porte quantistiche: simboli circuitali',
              fontsize=12, pad=10)

fig2.savefig('circuit_gates.pdf', dpi=300, bbox_inches='tight',
             facecolor='white', format='pdf')
fig2.savefig('circuit_gates.png', dpi=300, bbox_inches='tight',
             facecolor='white')
print("Gates figure saved.")
