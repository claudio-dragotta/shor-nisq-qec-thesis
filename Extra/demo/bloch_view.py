"""Sfera di Bloch 3D interattiva (Plotly) per mostrare cosa fa il rumore a UN qubit: non i 12
qubit entangled del circuito di Shor (lì un singolo qubit misurato da solo non ha un vettore di
Bloch pulito, perché è intrecciato con gli altri — mostrarlo confonderebbe un pubblico non
esperto), ma due esempi didattici isolati (H e X) con la STESSA fisica del canale depolarizzante
usato nel resto della demo: per depolarizing_error(p, 1), il vettore di Bloch si accorcia
esattamente di un fattore (1-p) — non è un'approssimazione. L'utente può ruotare la sfera col
mouse (3D nativo Plotly) e far partire un'animazione che mostra il vettore accorciarsi nel tempo.
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

N_FRAMES = 24
SPHERE_RES = 28
IDEAL_COLOR = "#2E86AB"
NOISY_COLOR = "#E76F51"

EXAMPLES = [
    ("Qubit dopo H (sovrapposizione)", (1.0, 0.0, 0.0)),
    ("Qubit dopo X (bit-flip)", (0.0, 0.0, -1.0)),
]

POLE_LABELS = [
    (0, 0, 1.3, "|0⟩"), (0, 0, -1.3, "|1⟩"),
    (1.3, 0, 0, "|+⟩"), (-1.3, 0, 0, "|−⟩"),
    (0, 1.3, 0, "|+i⟩"), (0, -1.3, 0, "|−i⟩"),
]


def _sphere_surface():
    u = np.linspace(0, 2 * np.pi, SPHERE_RES)
    v = np.linspace(0, np.pi, SPHERE_RES)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones_like(u), np.cos(v))
    return go.Surface(
        x=x, y=y, z=z, opacity=0.12, showscale=False, hoverinfo="skip",
        colorscale=[[0, "#8ecae6"], [1, "#8ecae6"]],
    )


def _axis_lines():
    L = 1.15
    xs, ys, zs = [], [], []
    for dx, dy, dz in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
        xs += [-L * dx, L * dx, None]
        ys += [-L * dy, L * dy, None]
        zs += [-L * dz, L * dz, None]
    return go.Scatter3d(
        x=xs, y=ys, z=zs, mode="lines", line=dict(color="#666", width=2),
        hoverinfo="skip", showlegend=False,
    )


def _pole_labels():
    xs, ys, zs, texts = zip(*POLE_LABELS)
    return go.Scatter3d(
        x=xs, y=ys, z=zs, mode="text", text=texts,
        textfont=dict(color="#999", size=11), hoverinfo="skip", showlegend=False,
    )


def _vector_trace(vec, color, name, width=9):
    x, y, z = vec
    return go.Scatter3d(
        x=[0, x], y=[0, y], z=[0, z], mode="lines+markers",
        line=dict(color=color, width=width),
        marker=dict(size=[0, 6], color=color),
        name=name, hoverinfo="name",
    )


def _scene_axes(title):
    ax = dict(range=[-1.35, 1.35], showticklabels=False, showbackground=False,
              zeroline=False, showgrid=False, title="")
    return dict(
        xaxis=ax, yaxis=ax, zaxis=ax, aspectmode="cube",
        camera=dict(eye=dict(x=1.4, y=1.4, z=0.9)),
    )


def render_bloch_figure(shrink):
    """shrink: fattore di accorciamento del vettore di Bloch (1 - probabilità extra), in [0,1].
    Ritorna una go.Figure con 2 scene 3D (esempio H, esempio X), ruotabili col mouse, con
    un'animazione (pulsante Play) che accorcia il vettore rumoroso da 1.0 a `shrink`."""
    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=[e[0] for e in EXAMPLES],
        horizontal_spacing=0.02,
    )

    noisy_trace_idx = []
    for col, (_, ideal_vec) in enumerate(EXAMPLES, start=1):
        fig.add_trace(_sphere_surface(), row=1, col=col)
        fig.add_trace(_axis_lines(), row=1, col=col)
        fig.add_trace(_pole_labels(), row=1, col=col)
        fig.add_trace(_vector_trace(ideal_vec, IDEAL_COLOR, "ideale"), row=1, col=col)
        fig.add_trace(_vector_trace(ideal_vec, NOISY_COLOR, "rumoroso"), row=1, col=col)
        noisy_trace_idx.append(len(fig.data) - 1)

    fig.update_layout(
        scene=_scene_axes(EXAMPLES[0][0]),
        scene2=_scene_axes(EXAMPLES[1][0]),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=420,
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.5, y=1.12, xanchor="center",
            buttons=[
                dict(label="▶ Anima il rumore", method="animate",
                     args=[None, {"frame": {"duration": 60, "redraw": True},
                                  "fromcurrent": True, "transition": {"duration": 0}}]),
                dict(label="⟲ Reset", method="animate",
                     args=[["frame0"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]),
            ],
        )],
    )

    frames = []
    for i in range(N_FRAMES + 1):
        t = i / N_FRAMES
        s = 1.0 - t * (1.0 - shrink)  # da 1.0 (ideale) a `shrink`
        frame_data = []
        frame_traces = []
        for idx, (_, ideal_vec) in zip(noisy_trace_idx, EXAMPLES):
            x, y, z = (ideal_vec[0] * s, ideal_vec[1] * s, ideal_vec[2] * s)
            frame_data.append(go.Scatter3d(
                x=[0, x], y=[0, y], z=[0, z], mode="lines+markers",
                line=dict(color=NOISY_COLOR, width=9),
                marker=dict(size=[0, 6], color=NOISY_COLOR),
            ))
            frame_traces.append(idx)
        frames.append(go.Frame(data=frame_data, traces=frame_traces, name=f"frame{i}"))
    frames[0].name = "frame0"
    fig.frames = frames

    return fig


def render_entanglement_figure(outcome=None):
    """Due qubit A, B dopo H(A) + CNOT(A,B) -> stato di Bell (|00>+|11>)/sqrt(2).

    outcome=None: nessuna misura ancora fatta — entrambi i vettori sono un punto nell'origine
    (stato indeterminato, non un'approssimazione: la traccia parziale è ESATTAMENTE I/2).
    outcome=0 o 1: A e B sono stati misurati insieme — entrambi i vettori COMPAIONO INSIEME,
    con un'animazione, allo stesso polo (|0> o |1>), perché nello stato di Bell il risultato è
    sempre concorde. Il pulsante ▶ anima la comparsa simultanea dei due vettori."""
    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=["Qubit A", "Qubit B (mai toccato)"],
        horizontal_spacing=0.02,
    )
    measured = outcome is not None
    final_z = 0.0 if not measured else (1.0 if outcome == 0 else -1.0)
    color = "#E9C46A" if not measured else ("#2E86AB" if outcome == 0 else "#E76F51")
    legend_name = "vettore = 0 (indeterminato)" if not measured else f"collassato su |{outcome}⟩"
    # stato iniziale del disegno: se misurato, parte dall'origine (l'animazione lo fa crescere);
    # se non misurato, e' gia' il punto finale (un punto fermo nell'origine, niente da animare).
    start_z = 0.0
    start_marker = 0 if measured else 7

    vec_trace_idx = []
    for col in (1, 2):
        fig.add_trace(_sphere_surface(), row=1, col=col)
        fig.add_trace(_axis_lines(), row=1, col=col)
        fig.add_trace(_pole_labels(), row=1, col=col)
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, start_z], mode="lines+markers",
            line=dict(color=color, width=9), marker=dict(size=[0, start_marker], color=color),
            name=legend_name, showlegend=(col == 1),
        ), row=1, col=col)
        vec_trace_idx.append(len(fig.data) - 1)

    fig.update_layout(
        scene=_scene_axes("A"), scene2=_scene_axes("B"),
        showlegend=True, legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
        margin=dict(l=0, r=0, t=30, b=0), height=380,
    )

    if measured:
        fig.update_layout(updatemenus=[dict(
            type="buttons", showactive=False, x=0.5, y=1.12, xanchor="center",
            buttons=[dict(
                label="▶ Misura A e B insieme", method="animate",
                args=[None, {"frame": {"duration": 40, "redraw": True},
                             "fromcurrent": True, "transition": {"duration": 0}}],
            )],
        )])
        n = 20
        frames = []
        for i in range(n + 1):
            t = i / n
            z = final_z * t
            frame_data = [
                go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, z], mode="lines+markers",
                             line=dict(color=color, width=9),
                             marker=dict(size=[0, 7 * t], color=color))
                for _ in vec_trace_idx
            ]
            frames.append(go.Frame(data=frame_data, traces=vec_trace_idx, name=f"f{i}"))
        fig.frames = frames

    return fig


def render_entanglement_correlation():
    """Probabilita' congiunte ESATTE per lo stato di Bell (|00>+|11>)/sqrt(2): 50% i due qubit
    concordano (00 o 11), 0% discordano — la correlazione perfetta che sostituisce il vettore
    individuale (sparito) come portatrice dell'informazione."""
    labels = ["00 (concordi)", "01 (discordi)", "10 (discordi)", "11 (concordi)"]
    probs = [0.5, 0.0, 0.0, 0.5]
    colors = ["#2A9D8F", "#E76F51", "#E76F51", "#2A9D8F"]
    fig = go.Figure()
    fig.add_bar(x=labels, y=probs, marker_color=colors, text=[f"{p:.0%}" for p in probs],
                textposition="outside")
    fig.update_layout(
        yaxis_title="Probabilità (esatta, stato di Bell)", yaxis_range=[0, 0.65],
        height=300, showlegend=False,
    )
    return fig
