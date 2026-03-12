"""
Genera diagramma insiemistico delle classi di complessità:
P ⊆ BPP ⊆ BQP ⊆ PSPACE
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.set_xlim(0, 8)
ax.set_ylim(0, 5.5)
ax.axis('off')

cx, cy = 4.0, 2.8

# (larghezza, altezza, colore, nome)
ellipses = [
    (7.4, 4.2, '#cce5f7', 'PSPACE'),
    (5.6, 3.2, '#99ccee', 'BQP'),
    (3.8, 2.2, '#66b2e5', 'BPP'),
    (2.0, 1.2, '#3399dc', 'P'),
]

for (w, h, color, name) in ellipses:
    e = mpatches.Ellipse((cx, cy), width=w, height=h,
                          facecolor=color, edgecolor='#1a5a8a',
                          linewidth=1.8,
                          zorder=ellipses.index((w, h, color, name)))
    ax.add_patch(e)

# Etichette — in alto dentro ogni ellisse
label_offsets = [
    (0,  1.75),   # PSPACE
    (0,  1.25),   # BQP
    (0,  0.78),   # BPP
    (0,  0.38),   # P
]
for (w, h, color, name), (dx, dy) in zip(ellipses, label_offsets):
    ax.text(cx + dx, cy + dy, r'$\mathbf{' + name + '}$',
            ha='center', va='center', fontsize=14,
            color='#0d2d4a', fontweight='bold')

# ── Annotazione: Shor e Grover in BQP ma fuori BPP ──
ax.annotate('Algoritmi di Shor\ne Grover $\\in$ BQP',
            xy=(cx + 2.0, cy + 0.3),
            xytext=(cx + 3.4, cy + 2.2),
            fontsize=10, color='#8b0000',
            ha='center',
            arrowprops=dict(arrowstyle='->', color='#8b0000',
                            lw=1.5, connectionstyle='arc3,rad=-0.2'),
            bbox=dict(boxstyle='round,pad=0.25', fc='#fff0f0',
                      ec='#cc0000', lw=0.8))

# ── Annotazione: algoritmi classici randomizzati in BPP ──
ax.annotate('Algoritmi classici\nrandomizzati $\\in$ BPP',
            xy=(cx - 1.4, cy - 0.15),
            xytext=(cx - 3.2, cy - 1.8),
            fontsize=10, color='#1a5c1a',
            ha='center',
            arrowprops=dict(arrowstyle='->', color='#1a5c1a',
                            lw=1.5, connectionstyle='arc3,rad=0.2'),
            bbox=dict(boxstyle='round,pad=0.25', fc='#f0fff0',
                      ec='#228b22', lw=0.8))

# ── Formula in basso ──
ax.text(cx, 0.35,
        r'$\mathbf{P} \subseteq \mathbf{BPP} \subseteq \mathbf{BQP} \subseteq \mathbf{PSPACE}$',
        ha='center', va='center', fontsize=12,
        bbox=dict(boxstyle='round,pad=0.4', fc='#fffbe6',
                  ec='goldenrod', lw=1.4))

ax.set_title('Gerarchia delle classi di complessità nel calcolo quantistico',
             fontsize=13, pad=12)

fig.tight_layout()
fig.savefig('complexity_classes.pdf', dpi=300, bbox_inches='tight',
            facecolor='white', format='pdf')
fig.savefig('complexity_classes.png', dpi=300, bbox_inches='tight',
            facecolor='white')
print("Complexity diagram saved.")
