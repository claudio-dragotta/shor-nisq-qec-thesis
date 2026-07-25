"""Disegno del circuito di Shor come SVG generato da codice (non un'immagine statica): stessa
struttura logica del circuito reale (via quantum_backend.base_circuit_layers, Qiskit-core puro,
nessun Aer), ma compatto, con animazioni CSS/SVG e tooltip in linguaggio semplice — pensato per
un pubblico che non conosce il calcolo quantistico.

I gate multi-qubit sono disegnati per CLUSTER di qubit contigui uniti da un sottile connettore,
non da un unico box pieno che coprirebbe anche i qubit di mezzo non coinvolti (fuorviante: un
box pieno da q0 a q11 farebbe credere che il gate tocchi tutti i 12 qubit, quando in realtà ne
tocca solo alcuni). Un'unione-find sull'intero circuito individua i gruppi di qubit che restano
entangled fino alla fine, mostrati con parentesi colorate sul margine sinistro.
"""
import re

ROW_H = 26
COL_W = 76
LABEL_W = 58
TOP_MARGIN = 34  # spazio extra sopra per la traccia del tempo animata

GATE_COLORS = {
    "h": "#2E86AB",
    "x": "#264653",
    "measure": "#6c757d",
}
DEFAULT_GATE_COLOR = "#8E1F4B"
ENTANGLE_COLORS = ["#E9C46A", "#2A9D8F", "#F4A261", "#9B5DE5", "#00BBF9"]

GATE_EXPLANATIONS = {
    "h": "Hadamard: mette il qubit in sovrapposizione (0 e 1 allo stesso tempo)",
    "x": "NOT quantistico: inverte il qubit",
    "measure": "Misura: legge il risultato, il qubit collassa in 0 o 1",
    "barrier": "Separatore: solo visivo, non è un'operazione fisica",
}


def _short_label(name):
    m = re.match(r"c_(\d+)\^(\d+) mod (\d+)", name)
    if m:
        a, k, _n = m.groups()
        return f"U({a}^{k})"
    if name == "measure":
        return "M"
    if name.startswith("QFT"):
        return "QFT⁻¹"
    return name.upper()


def _explanation(name):
    if name in GATE_EXPLANATIONS:
        return GATE_EXPLANATIONS[name]
    if name.startswith("c_") or name.startswith("QFT"):
        if name.startswith("QFT"):
            return "Trasformata di Fourier inversa: legge il periodo nascosto nei qubit"
        return "Moltiplicazione modulare controllata: il cuore dell'algoritmo di Shor"
    return name


def _clusters(qubits):
    """Raggruppa qubit ordinati in blocchi contigui (q, q+1, q+2, ...)."""
    qs = sorted(qubits)
    clusters, cur = [], [qs[0]]
    for q in qs[1:]:
        if q == cur[-1] + 1:
            cur.append(q)
        else:
            clusters.append(cur)
            cur = [q]
    clusters.append(cur)
    return clusters


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, a):
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _entanglement_groups(layers, n_qubits):
    """Unione-find sui gate multi-qubit (esclusi barrier/measure) su tutto il circuito:
    ritorna {qubit_index: group_id} solo per i gruppi con >1 qubit."""
    uf = _UnionFind(n_qubits)
    for layer in layers:
        for op in layer:
            if op["name"] in ("barrier", "measure") or len(op["qubits"]) < 2:
                continue
            qs = op["qubits"]
            for q in qs[1:]:
                uf.union(qs[0], q)
    groups = {}
    for q in range(n_qubits):
        groups.setdefault(uf.find(q), []).append(q)
    return {q: gid for gid, members in groups.items() if len(members) > 1 for q in members}, groups


def _short_qubit_label(label):
    """'count[12]' -> 'c12', 'work[3]' -> 'w3' — robusto a indici multi-cifra (a differenza di
    un accesso diretto a un carattere fisso, che tronca al primo digit oltre il 9)."""
    prefix = "c" if label.startswith("count") else "w"
    idx = label[label.index("[") + 1: label.index("]")]
    return prefix + idx


def render_circuit_svg(layers, qubit_labels, noisy_qubits=None, noisy_gate_positions=None,
                        active_layer_index=None):
    """layers: da quantum_backend.base_circuit_layers() o shor_general.circuit_layers().
    qubit_labels: una etichetta 'count[i]'/'work[i]' per qubit — la lunghezza determina il
    numero di righe disegnate (non più fissa a 12, generalizzato per N libero).
    noisy_qubits: set/dict di indici qubit con rumore extra (righe animate in rosso).
    noisy_gate_positions: set di (layer_idx, tuple(qubits)) da evidenziare come gate toccati.
    active_layer_index: se dato (vista step-by-step a click), evidenzia quella colonna con un
    riquadro fisso invece del puntino animato in autoplay — coerente con l'avanzamento manuale.
    """
    noisy_qubits = set(noisy_qubits or [])
    noisy_gate_positions = noisy_gate_positions or set()
    n_qubits = len(qubit_labels)
    n_cols = max(len(layers), 1)
    width = LABEL_W + n_cols * COL_W + 20
    height = TOP_MARGIN + n_qubits * ROW_H + 10

    def y_of(q):
        return TOP_MARGIN + q * ROW_H + ROW_H / 2

    qubit_to_group, groups_by_id = _entanglement_groups(layers, n_qubits)
    group_color = {}
    for i, gid in enumerate(sorted({g for g in qubit_to_group.values()})):
        group_color[gid] = ENTANGLE_COLORS[i % len(ENTANGLE_COLORS)]

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Helvetica,Arial,sans-serif">',
        """<style>
        @keyframes pulse-row { 0%{opacity:0.10;} 50%{opacity:0.42;} 100%{opacity:0.10;} }
        @keyframes pulse-gate { 0%{stroke-opacity:0.35;} 50%{stroke-opacity:1;} 100%{stroke-opacity:0.35;} }
        @keyframes fade-in { 0%{opacity:0;} 100%{opacity:1;} }
        @keyframes pulse-link { 0%{stroke-opacity:0.4;} 50%{stroke-opacity:1;} 100%{stroke-opacity:0.4;} }
        .noisy-row { animation: pulse-row 1.6s ease-in-out infinite; }
        .noisy-gate { animation: pulse-gate 1.2s ease-in-out infinite; stroke:#E76F51; stroke-width:2.5; }
        .wire { stroke:#888; stroke-width:1.2; }
        .connector { stroke-width:2; }
        .qlabel { font-size:10px; fill:#aaa; }
        .gate-text { font-size:8.5px; fill:white; text-anchor:middle; dominant-baseline:middle; pointer-events:none; }
        .gate-box { cursor:help; }
        .gate-box:hover { filter:brightness(1.35); }
        .diagram-body { animation: fade-in 0.5s ease-out; }
        .time-track { stroke:#444; stroke-width:1; stroke-dasharray:2,3; }
        .entangle-bracket { animation: pulse-link 2s ease-in-out infinite; stroke-width:2.5; fill:none; }
        .active-col { fill:#00E5FF; opacity:0.12; }
        @keyframes pulse-ball { 0%{r:5;} 50%{r:6.5;} 100%{r:5;} }
        .active-ball { animation: pulse-ball 1s ease-in-out infinite; fill:#00E5FF; }
        </style>""",
        f'<g class="diagram-body">',
        f'<line class="time-track" x1="{LABEL_W - 6}" y1="{TOP_MARGIN - 14}" '
        f'x2="{width - 6}" y2="{TOP_MARGIN - 14}" />',
    ]
    if active_layer_index is None:
        # vecchia vista (autoplay): un punto che scorre da sinistra a destra in loop
        parts.append(
            f'<text x="{LABEL_W - 6}" y="{TOP_MARGIN - 20}" font-size="8" fill="#666">il tempo scorre →</text>'
            f'<circle r="4" fill="#2A9D8F">'
            f'<animate attributeName="cx" values="{LABEL_W - 6};{width - 6}" dur="3.5s" repeatCount="indefinite" />'
            f'<animate attributeName="cy" values="{TOP_MARGIN - 14};{TOP_MARGIN - 14}" dur="3.5s" repeatCount="indefinite" />'
            f'</circle>'
        )
    else:
        # vista step-by-step: la pallina sta ferma sullo stadio corrente, si sposta di scatto a
        # ogni click su "Avanti" (nessun loop automatico). active_layer_index=-1: non ancora
        # partiti, la pallina sta prima della prima colonna, nessuna colonna evidenziata.
        started = active_layer_index >= 0
        label = "sei qui →" if started else "pronto — premi Avanti →"
        if started:
            parts.append(
                f'<rect class="active-col" x="{LABEL_W + active_layer_index * COL_W:.1f}" y="0" '
                f'width="{COL_W:.1f}" height="{height}" />'
            )
            ax_center = LABEL_W + active_layer_index * COL_W + COL_W / 2
        else:
            ax_center = LABEL_W - 6
        parts.append(
            f'<text x="{LABEL_W - 6}" y="{TOP_MARGIN - 20}" font-size="8" fill="#666">{label}</text>'
            f'<circle class="active-ball" cx="{ax_center:.1f}" cy="{TOP_MARGIN - 14}" r="5" />'
        )

    # sfondo animato dietro le wire con rumore extra
    for q in noisy_qubits:
        y = y_of(q)
        parts.append(
            f'<rect class="noisy-row" x="0" y="{y - ROW_H/2:.1f}" width="{width}" '
            f'height="{ROW_H:.1f}" fill="#E76F51" />'
        )

    # parentesi di entanglement sul margine sinistro: qubit con la stessa parentesi/colore
    # restano intrecciati tra loro fino alla fine del circuito (unione-find sui gate multi-qubit)
    for gid, members in groups_by_id.items():
        if len(members) < 2:
            continue
        color = group_color[gid]
        y0, y1 = y_of(min(members)), y_of(max(members))
        bx = 13
        parts.append(
            f'<path class="entangle-bracket" stroke="{color}" '
            f'd="M {bx+5},{y0:.1f} Q {bx},{y0:.1f} {bx},{(y0+y1)/2:.1f} '
            f'Q {bx},{y1:.1f} {bx+5},{y1:.1f}" />'
        )

    # wire + etichette
    for q in range(n_qubits):
        y = y_of(q)
        parts.append(f'<line class="wire" x1="{LABEL_W - 6}" y1="{y:.1f}" x2="{width - 6}" y2="{y:.1f}" />')
        short = _short_qubit_label(qubit_labels[q])
        label_color = group_color.get(qubit_to_group.get(q), "#aaa")
        parts.append(f'<text class="qlabel" x="20" y="{y + 3:.1f}" fill="{label_color}">{short}</text>')

    # gate per layer
    for c, layer in enumerate(layers):
        x_center = LABEL_W + c * COL_W + COL_W / 2
        for op in layer:
            name, qubits = op["name"], op["qubits"]
            highlighted = (c, tuple(sorted(qubits))) in noisy_gate_positions
            extra_class = " noisy-gate" if highlighted else ""
            tooltip = f"<title>{_explanation(name)}</title>"

            if name == "barrier":
                y0, y1 = y_of(min(qubits)), y_of(max(qubits))
                parts.append(
                    f'<line x1="{x_center:.1f}" y1="{y0 - ROW_H/2:.1f}" x2="{x_center:.1f}" '
                    f'y2="{y1 + ROW_H/2:.1f}" stroke="#bbb" stroke-width="1.5" stroke-dasharray="4,3" />'
                )
                continue

            label = _short_label(name)
            color = GATE_COLORS.get(name, DEFAULT_GATE_COLOR)

            if len(qubits) == 1:
                y = y_of(qubits[0])
                parts.append(
                    f'<g class="gate-box{extra_class}">{tooltip}'
                    f'<rect x="{x_center - 24:.1f}" y="{y - 10:.1f}" '
                    f'width="48" height="20" rx="4" fill="{color}" />'
                    f'<text class="gate-text" x="{x_center:.1f}" y="{y + 1:.1f}">{label}</text></g>'
                )
                continue

            clusters = _clusters(qubits)
            if len(clusters) > 1:
                # connettore sottile tra i cluster (attraversa le wire non coinvolte SENZA
                # coprirle con un box pieno, cosi' resta chiaro quali qubit sono coinvolti)
                y_first = y_of(sum(clusters[0]) / len(clusters[0]))
                y_last = y_of(sum(clusters[-1]) / len(clusters[-1]))
                parts.append(
                    f'<line class="connector{extra_class}" x1="{x_center:.1f}" y1="{y_first:.1f}" '
                    f'x2="{x_center:.1f}" y2="{y_last:.1f}" stroke="{color}" />'
                )
            # etichetta sul cluster piu' grande (quello con piu' qubit coinvolti)
            label_cluster = max(clusters, key=len)
            for cluster in clusters:
                y0, y1 = y_of(cluster[0]), y_of(cluster[-1])
                is_label_cluster = cluster is label_cluster
                w = 60 if is_label_cluster else 22
                parts.append(
                    f'<g class="gate-box{extra_class}">{tooltip}'
                    f'<rect x="{x_center - w/2:.1f}" y="{y0 - 10:.1f}" '
                    f'width="{w}" height="{y1 - y0 + 20:.1f}" rx="5" fill="{color}" />'
                )
                if is_label_cluster:
                    parts.append(
                        f'<text class="gate-text" x="{x_center:.1f}" y="{(y0 + y1)/2 + 1:.1f}">{label}</text>'
                    )
                parts.append("</g>")

    parts.append("</g></svg>")
    return "".join(parts)
