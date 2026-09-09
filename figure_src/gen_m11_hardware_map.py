"""
gen_m11_hardware_map.py — Figura M11: mappa hardware FakeSherbrooke con layout sovrapposto.

Mostra la coupling map del processore a 127 qubit (IBM Eagle r3 / FakeSherbrooke)
con i 12 qubit usati dai due layout selezionati evidenziati:
  - verde (diamante) : layout 35, selezionato per fidelità hardware
  - arancio (quadrato): layout 48, selezionato per score sul train
  - viola (cerchio)  : qubit condivisi da entrambi i layout
  - grigio           : qubit non usati

Due pannelli affiancati: sinistro = layout 35, destro = layout 48.

Uso (ambiente canonico):
    /home/claudio/quantum-env/bin/python figure_src/gen_m11_hardware_map.py
"""
import json
import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

# ── Percorsi ─────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
ARTIFACT = os.path.join(
    _ROOT,
    "Extra/experiments/M11_layout/artifacts/v2_20260819",
    "results_M11_pilota_v2_20260826_222137.json",
)
OUT_DIR = os.path.join(_ROOT, "file_latex", "figure")
PNG_DIR = os.path.join(_HERE, "anteprime")

# ── Layout selezionati ────────────────────────────────────────────────────────
with open(ARTIFACT) as f:
    data = json.load(f)

stats = data["statistics"]
SEL_FID   = stats["selected_by_fidelity_layout_id"]   # 35
SEL_TRAIN = stats["selected_on_train_layout_id"]       # 48

def get_layout_qubits(points, layout_id):
    return next(p["layout"] for p in points if p["layout_id"] == layout_id)

qubits_fid   = get_layout_qubits(data["points"], SEL_FID)    # layout 35
qubits_train = get_layout_qubits(data["points"], SEL_TRAIN)  # layout 48
shared_qubits = set(qubits_fid) & set(qubits_train)

# ── Coupling map da qiskit ────────────────────────────────────────────────────
def _get_coupling_edges():
    """Restituisce la lista di archi della coupling map di FakeSherbrooke."""
    try:
        from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
        backend = FakeSherbrooke()
        return list(backend.coupling_map)
    except ImportError:
        pass
    try:
        from qiskit.providers.fake_provider import FakeSherbrooke
        backend = FakeSherbrooke()
        return list(backend.coupling_map)
    except ImportError:
        pass
    # Fallback: heavy-hex parziale IBM Eagle (bordo superiore, qubit 95-126)
    # Sufficiente per visualizzare la regione usata dai layout 35 e 48
    edges = []
    # Riga top: 100-101-...-112 (13 qubit)
    for i in range(100, 112): edges += [(i, i+1), (i+1, i)]
    # Riga mid: 113-114-...-126
    for i in range(113, 126): edges += [(i, i+1), (i+1, i)]
    # Connessioni verticali heavy-hex (approssimate)
    for top, mid in [(100,113),(102,114),(104,115),(106,116),(108,117),(110,118),(112,119)]:
        edges += [(top, mid), (mid, top)]
    for mid, lo in [(113,95),(115,96),(117,97),(119,98),(121,99),(123,100),(125,101)]:
        edges += [(mid, lo), (lo, mid)]
    return edges

coupling_edges = _get_coupling_edges()

# ── Costruzione grafo ─────────────────────────────────────────────────────────
# Teniamo solo i qubit nella regione 95-126 (dove vivono i nostri layout)
# più i loro vicini nella coupling map
all_used = set(qubits_fid) | set(qubits_train)

def neighborhood(qubits, edges, radius=1):
    """Espande il set di qubit includendo i vicini fino a 'radius' hop."""
    current = set(qubits)
    for _ in range(radius):
        adj = set()
        for a, b in edges:
            if a in current: adj.add(b)
            if b in current: adj.add(a)
        current |= adj
    return current

visible = neighborhood(all_used, coupling_edges, radius=1)
visible = {q for q in visible if q >= 90}   # filtra qubit molto distanti

G = nx.DiGraph()
G.add_nodes_from(visible)
for a, b in coupling_edges:
    if a in visible and b in visible:
        G.add_edge(a, b)

G_undirected = G.to_undirected()

# ── Layout posizioni ──────────────────────────────────────────────────────────
pos = nx.kamada_kawai_layout(G_undirected, weight=None)

# ── Palette ──────────────────────────────────────────────────────────────────
C_FID    = "#2E7D32"   # verde
C_TR     = "#E65100"   # arancio
C_SHARED = "#7B1FA2"   # viola (qubit in entrambi i layout)
C_UNUSED = "#BDBDBD"   # grigio chiaro
C_EDGE_ACTIVE = "#424242"
C_EDGE_INACTIVE = "#E0E0E0"

def node_color(q, focus_set):
    if q in shared_qubits and q in focus_set:
        return C_SHARED
    if q in focus_set:
        return C_FID if focus_set is set(qubits_fid) else C_TR
    return C_UNUSED

def node_size(q, focus_set):
    return 220 if q in focus_set else 60

def edge_color(a, b, focus_set):
    if a in focus_set and b in focus_set:
        return C_EDGE_ACTIVE
    return C_EDGE_INACTIVE

def edge_width(a, b, focus_set):
    return 1.8 if a in focus_set and b in focus_set else 0.5

# ── Figura con due pannelli ──────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))

panels = [
    (axes[0], set(qubits_fid),   C_FID, "D",
     f"Layout {SEL_FID} — selezionato per fidelità hardware\n"
     f"$P_{{holdout}}={stats['P_holdout_selected_by_fidelity']:.3f}$"),
    (axes[1], set(qubits_train), C_TR,  "s",
     f"Layout {SEL_TRAIN} — selezionato per score sul train\n"
     f"$P_{{holdout}}={stats['P_holdout_selected_on_train']:.3f}$"),
]

for ax, focus, c_focus, marker, title in panels:
    node_colors = [
        C_SHARED if (q in shared_qubits and q in focus)
        else (c_focus if q in focus else C_UNUSED)
        for q in G_undirected.nodes()
    ]
    node_sizes = [200 if q in focus else 55 for q in G_undirected.nodes()]
    edge_colors = [
        C_EDGE_ACTIVE if (u in focus and v in focus) else C_EDGE_INACTIVE
        for u, v in G_undirected.edges()
    ]
    edge_widths = [
        1.8 if (u in focus and v in focus) else 0.45
        for u, v in G_undirected.edges()
    ]

    nx.draw_networkx_nodes(
        G_undirected, pos, ax=ax,
        node_color=node_colors, node_size=node_sizes,
        linewidths=0.4, edgecolors="#424242",
    )
    nx.draw_networkx_edges(
        G_undirected, pos, ax=ax,
        edge_color=edge_colors, width=edge_widths,
        arrows=False, alpha=0.85,
    )
    # Etichette solo per qubit usati
    labels = {q: str(q) for q in focus}
    nx.draw_networkx_labels(
        G_undirected, pos, labels=labels, ax=ax,
        font_size=5.5, font_color="white", font_weight="bold",
    )

    ax.set_title(title, fontsize=9.0, pad=6)
    ax.axis("off")

# Legenda globale
legend_handles = [
    mpatches.Patch(color=C_FID,    label="qubit layout 35 (fidelità)"),
    mpatches.Patch(color=C_TR,     label="qubit layout 48 (train score)"),
    mpatches.Patch(color=C_SHARED, label="qubit condivisi"),
    mpatches.Patch(color=C_UNUSED, label="qubit non usati"),
]
fig.legend(handles=legend_handles, loc="lower center", ncol=4,
           fontsize=8.0, framealpha=0.9, bbox_to_anchor=(0.5, -0.03))
fig.suptitle(
    r"M11 — Mapping circuito Shor ($N=15$, 12 qubit logici) su FakeSherbrooke 127Q",
    fontsize=10.5, y=1.01,
)

fig.tight_layout()
os.makedirs(OUT_DIR, exist_ok=True)
base = os.path.join(OUT_DIR, "gen_m11_hardware_map")
fig.savefig(base + ".pdf", bbox_inches="tight")
os.makedirs(PNG_DIR, exist_ok=True)
fig.savefig(os.path.join(PNG_DIR, os.path.basename(base) + ".png"),
            dpi=180, bbox_inches="tight")
print(f"Salvato: {base}.pdf")
print(f"Anteprima: {os.path.join(PNG_DIR, os.path.basename(base))}.png")
