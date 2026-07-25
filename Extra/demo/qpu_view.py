"""Vista 3D della QPU: il segnale entra, i 12 qubit "girano" mentre i gate li toccano, il
risultato esce. Stessa idea di narrazione a stadi della dashboard di un collega (QSDN adapter,
progetto diverso) ma con un linguaggio visivo distinto: QPU scura tipo chip fisico invece di una
mappa 2D, Plotly 3D nativo (già una dipendenza della demo, nessuna CDN esterna — la demo deve
restare riproducibile offline in Docker/Render).

I 6 stadi vengono letti da quantum_backend.base_circuit_layers() — Qiskit-core puro, nessun Aer:
sono ESATTAMENTE gli stessi layer già usati da circuit_view.render_circuit_svg per il diagramma
2D, non una ricostruzione parallela. Il "sfarfallio" del vettore sopra ogni qubit è una metafora
didattica (un solo qubit entangled non ha un vettore di Bloch pulito — stesso avvertimento già
in bloch_view.py), non uno stato calcolato esattamente: le posizioni, il numero di stadi, quali
qubit vengono toccati e quando restano invece fedeli al circuito reale.
"""
import numpy as np
import plotly.graph_objects as go

from circuit_view import ENTANGLE_COLORS, _entanglement_groups

IDEAL_BLUE = "#2E86AB"      # registro count, stato base — stesso blu "ideale" del resto della demo
WORK_VIOLET = "#9B5DE5"     # registro work — dalla stessa palette di circuit_view.ENTANGLE_COLORS
ACTIVE_RED = "#E76F51"      # gate attivo in questo stadio — stesso rosso "rumore/attivo" ovunque
SETTLED_TEAL = "#2A9D8F"    # qubit misurato/collassato — stesso verde "confermato" ovunque
IDLE_GOLD = "#E9C46A"       # qubit non ancora toccato — stesso oro "indeterminato" di bloch_view
CHIP_BG = "#0B1220"
GRID_COLOR = "#1E2A3A"

N_COUNT, N_WORK = 8, 4
INPUT_POINT = (-2.4, 0.0, 0.7)
OUTPUT_POINT = (11.6, 0.0, 0.7)

STAGE_LABELS = [
    "Init: superposizione (H×8) + |1⟩ sul registro work",
    "U(7¹) mod 15 — prima moltiplicazione modulare controllata",
    "U(7²) mod 15 — seconda (le altre 6 sono identità: periodo r=4)",
    "Checkpoint (barrier — nessun effetto fisico)",
    "QFT⁻¹ sul registro count — legge il periodo nascosto",
    "Misura: collasso del registro count",
]
STAGE_SUBFRAMES = [6, 6, 6, 2, 8, 4]


def _qubit_position(q):
    if q < N_COUNT:
        return (q * 1.3, 1.2, 0.0)
    w = q - N_COUNT
    return (2.6 + w * 1.3, -1.2, 0.0)


POSITIONS = {q: _qubit_position(q) for q in range(N_COUNT + N_WORK)}


def _short_label(q):
    return f"c{q}" if q < N_COUNT else f"w{q - N_COUNT}"


def _chip_plane():
    x = [-1.3, 10.5, 10.5, -1.3]
    y = [-2.3, -2.3, 2.3, 2.3]
    z = [-0.18] * 4
    plane = go.Mesh3d(
        x=x, y=y, z=z, i=[0], j=[1], k=[2], color=CHIP_BG, opacity=0.92,
        hoverinfo="skip", showlegend=False, flatshading=True,
    )
    xs, ys, zs = [], [], []
    for gx in np.arange(-1.3, 10.6, 1.3):
        xs += [gx, gx, None]
        ys += [-2.3, 2.3, None]
        zs += [-0.17, -0.17, None]
    for gy in (-1.2, 0.0, 1.2):
        xs += [-1.3, 10.5, None]
        ys += [gy, gy, None]
        zs += [-0.17, -0.17, None]
    grid = go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=GRID_COLOR, width=1),
                         hoverinfo="skip", showlegend=False)
    return [plane, grid]


def _qubit_markers(qubit_labels):
    xs, ys, zs, colors, texts = [], [], [], [], []
    for q in range(N_COUNT + N_WORK):
        x, y, z = POSITIONS[q]
        xs.append(x); ys.append(y); zs.append(z)
        colors.append(IDEAL_BLUE if q < N_COUNT else WORK_VIOLET)
        texts.append(_short_label(q))
    return go.Scatter3d(
        x=xs, y=ys, z=zs, mode="markers+text", text=texts, textposition="bottom center",
        textfont=dict(color="#cfd8dc", size=10),
        marker=dict(size=6, color=colors, line=dict(color="#000", width=0.5)),
        hovertext=qubit_labels, hoverinfo="text", showlegend=False,
    )


def _stage_of_frame(frame_idx):
    acc = 0
    for stage, n in enumerate(STAGE_SUBFRAMES):
        if frame_idx < acc + n:
            return stage, frame_idx - acc, n
        acc += n
    last = len(STAGE_SUBFRAMES) - 1
    return last, STAGE_SUBFRAMES[last] - 1, STAGE_SUBFRAMES[last]


def _active_qubits_and_links(layers, stage):
    layer = layers[stage] if stage < len(layers) else []
    active, links = set(), []
    for op in layer:
        if op["name"] == "barrier":
            continue
        qs = op["qubits"]
        active |= set(qs)
        if len(qs) > 1:
            control = qs[0]
            links.extend((control, t) for t in qs[1:])
    return active, links


def _spin_vector(pos, sub, n_sub, color_active, active):
    x, y, z = pos
    if not active:
        return x, y, z + 0.35, x, y, z  # ago fermo, corto, verticale
    angle = 2 * np.pi * sub / max(n_sub - 1, 1)
    R = 0.5
    tip = (x + R * np.sin(angle), y + 0.18 * np.sin(2 * angle), z + 0.35 + R * 0.4 * np.cos(angle))
    return tip[0], tip[1], tip[2], x, y, z


def render_qpu_figure(layers, qubit_labels, noisy_qubits=None, readout=None):
    """layers: quantum_backend.base_circuit_layers(). qubit_labels: QUBIT_LABELS.
    noisy_qubits: set di indici con rumore extra (stesso multiselect del circuito 2D).
    readout: dict con 'ideal_counts'/'noisy_counts' se già disponibile (st.session_state.sim_result),
    usato solo per colorare l'ultimo frame — l'istogramma vero va in render_readout_preview."""
    noisy_qubits = set(noisy_qubits or [])
    n_qubits = N_COUNT + N_WORK

    fig = go.Figure()
    for trace in _chip_plane():
        fig.add_trace(trace)
    fig.add_trace(_qubit_markers(qubit_labels))          # idx 2
    fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode="lines",
                                line=dict(width=4), hoverinfo="skip", showlegend=False))  # 3 link
    fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode="lines",
                                line=dict(color=ACTIVE_RED, width=6), hoverinfo="skip",
                                showlegend=False))  # 4 spin vectors
    fig.add_trace(go.Scatter3d(x=[INPUT_POINT[0]], y=[INPUT_POINT[1]], z=[INPUT_POINT[2]],
                                mode="markers", marker=dict(size=7, color="#00E5FF",
                                                             symbol="diamond"),
                                name="segnale", hoverinfo="skip", showlegend=False))  # 5 pulse
    ring_x, ring_y, ring_z = zip(*[POSITIONS[q] for q in noisy_qubits]) if noisy_qubits else ([], [], [])
    fig.add_trace(go.Scatter3d(x=list(ring_x), y=list(ring_y), z=[z + 0.02 for z in ring_z],
                                mode="markers", marker=dict(size=14, color=ACTIVE_RED, opacity=0.25),
                                hoverinfo="skip", showlegend=False))  # 6 noisy glow

    total_frames = sum(STAGE_SUBFRAMES)
    entangled_groups, _ = _entanglement_groups(layers, n_qubits)
    persistent_links = []  # (control, target, color) accumulati stadio per stadio
    link_color_i = 0

    frames = []
    for f in range(total_frames):
        stage, sub, n_sub = _stage_of_frame(f)
        active, new_links = _active_qubits_and_links(layers, stage)
        if sub == 0 and new_links:
            color = ENTANGLE_COLORS[link_color_i % len(ENTANGLE_COLORS)]
            link_color_i += 1
            persistent_links.extend((c, t, color) for c, t in new_links)

        lx, ly, lz, lc = [], [], [], []
        for c, t, color in persistent_links:
            (x0, y0, z0), (x1, y1, z1) = POSITIONS[c], POSITIONS[t]
            lx += [x0, x1, None]; ly += [y0, y1, None]; lz += [z0 + 0.02, z1 + 0.02, None]
        link_trace = go.Scatter3d(x=lx, y=ly, z=lz, mode="lines",
                                   line=dict(color=persistent_links[-1][2] if persistent_links else "#333",
                                             width=4))

        vx, vy, vz = [], [], []
        collapsing = stage == 5
        for q in range(n_qubits):
            pos = POSITIONS[q]
            is_active = q in active and not collapsing
            if collapsing and q < N_COUNT:
                tip = (pos[0], pos[1], pos[2] + 0.12)
                vx += [tip[0], pos[0], None]; vy += [tip[1], pos[1], None]; vz += [tip[2], pos[2], None]
                continue
            tx, ty, tz, bx, by, bz = _spin_vector(pos, sub, n_sub, ACTIVE_RED, is_active)
            vx += [tx, bx, None]; vy += [ty, by, None]; vz += [tz, bz, None]
        vec_trace = go.Scatter3d(x=vx, y=vy, z=vz, mode="lines", line=dict(color=ACTIVE_RED, width=6))

        t = (stage + sub / max(n_sub - 1, 1)) / (len(STAGE_SUBFRAMES) - 1)
        t = min(max(t, 0.0), 1.0)
        px = INPUT_POINT[0] + t * (OUTPUT_POINT[0] - INPUT_POINT[0])
        pulse_trace = go.Scatter3d(x=[px], y=[0.0], z=[0.7], mode="markers",
                                    marker=dict(size=7, color="#00E5FF", symbol="diamond"))

        noisy_size = 14 + 4 * np.sin(f * 0.6)
        glow_trace = go.Scatter3d(x=list(ring_x), y=list(ring_y), z=[z + 0.02 for z in ring_z],
                                   mode="markers", marker=dict(size=noisy_size, color=ACTIVE_RED, opacity=0.3))

        frames.append(go.Frame(
            data=[link_trace, vec_trace, pulse_trace, glow_trace],
            traces=[3, 4, 5, 6], name=f"f{f}",
            layout=go.Layout(annotations=[dict(
                text=STAGE_LABELS[stage], x=0.02, y=0.96, xref="paper", yref="paper",
                showarrow=False, font=dict(color="#cfd8dc", size=12), xanchor="left",
            )]),
        ))
    fig.frames = frames

    axis = dict(showticklabels=False, showbackground=False, zeroline=False, showgrid=False,
                title="", range=[-3, 12] if False else None)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHIP_BG,
        scene=dict(
            xaxis=dict(showticklabels=False, showbackground=False, zeroline=False, showgrid=False, title=""),
            yaxis=dict(showticklabels=False, showbackground=False, zeroline=False, showgrid=False, title=""),
            zaxis=dict(showticklabels=False, showbackground=False, zeroline=False, showgrid=False, title="",
                       range=[-0.5, 2.2]),
            aspectmode="manual", aspectratio=dict(x=2.6, y=1, z=0.55),
            camera=dict(eye=dict(x=0.9, y=-1.9, z=0.9)),
            bgcolor=CHIP_BG,
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=460,
        showlegend=False,
        annotations=[dict(text=STAGE_LABELS[0], x=0.02, y=0.96, xref="paper", yref="paper",
                           showarrow=False, font=dict(color="#cfd8dc", size=12), xanchor="left")],
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.98, y=0.02, xanchor="right", yanchor="bottom",
            bgcolor="#132033", font=dict(color="#cfd8dc"),
            buttons=[
                dict(label="▶ Anima la QPU", method="animate",
                     args=[None, {"frame": {"duration": 70, "redraw": True},
                                  "fromcurrent": True, "transition": {"duration": 0}}]),
                dict(label="⟲ Reset", method="animate",
                     args=[["f0"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]),
            ],
        )],
    )
    return fig


def render_readout_preview(readout):
    """readout: st.session_state.sim_result (dict con ideal_counts/noisy_counts) o None.
    Ritorna una go.Figure compatta con i TOP-6 esiti misurati, o None se non c'è ancora
    un'esecuzione live (in quel caso app.py mostra un invito a premere 'Esegui simulazione')."""
    if not readout:
        return None
    ideal_counts, noisy_counts = readout["ideal_counts"], readout["noisy_counts"]
    xs = sorted(set(ideal_counts) | set(noisy_counts),
                key=lambda k: noisy_counts.get(k, 0), reverse=True)[:6]
    fig = go.Figure()
    fig.add_bar(x=xs, y=[ideal_counts.get(x, 0) for x in xs], name="Ideale", marker_color=IDEAL_BLUE,
                opacity=0.85)
    fig.add_bar(x=xs, y=[noisy_counts.get(x, 0) for x in xs], name="Rumoroso", marker_color=ACTIVE_RED,
                opacity=0.65)
    fig.update_layout(
        barmode="overlay", height=220, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.15), xaxis_title="Esito (bin)", yaxis_title="Conteggio",
    )
    return fig
