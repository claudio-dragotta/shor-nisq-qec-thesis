"""Vista "Simulatore": due percorsi separati e nettamente distinti, scelti con un unico
selettore in cima (st.pills, non due controlli diversi):

- **Senza rumore**: solo la meccanica del circuito — avanzamento a click ("Avanti ▶", uno
  stadio alla volta) o play automatico, una sfera di Bloch per qubit del registro count
  (grigia = non toccata, blu orizzontale = dopo Hadamard, oro = toccata da un gate
  controllato/QFT, verde/rossa = collassata alla misura, corretta o no). Nessun controllo di
  rumore in questo percorso: è la vista "come funziona l'algoritmo".
- **Con rumore**: configuri il rumore (di base + regole mirate qubit-per-qubit), poi scegli
  quante iterazioni far girare per vedere quanto è affidabile il risultato — è la vista
  "quanto regge nel mondo reale".

Input N libero (via shor_general.py), sempre. Usa SEMPRE shor_general (mai quantum_backend.py,
che è cablato solo su N=15): per N in {15,21,35} shor_general richiama comunque
shor_core.shor_circuit, quindi il circuito resta identico a quello già validato — cambia solo
il modulo che lo invoca.
"""
import subprocess
import time

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

import circuit_view
import shor_general as sg
from bloch_view import _axis_lines, _scene_axes, _sphere_surface

IDLE_GREY = "#555f6b"
H_BLUE = "#2E86AB"
FLIGHT_GOLD = "#E9C46A"
OK_GREEN = "#2A9D8F"
BAD_RED = "#E76F51"

NOISE_PRESETS = {
    "UC1 — NISQ realistico": dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02),
    "UC2 — NISQ degradato": dict(eps_1q=5e-3, eps_2q=5e-2, t1_ns=50_000, t2_ns=30_000, p_ro=0.05),
}


# ---------------------------------------------------------------------------
# Disegno: una sfera di Bloch per qubit del registro count
# ---------------------------------------------------------------------------
def _qubit_visual_state(i, stage, layers):
    """(vec, color) per il qubit count `i` a uno stadio PRIMA della misura. La misura è gestita
    a parte in render_step_figure (serve lo shot campionato)."""
    if stage == 0:
        return (0.0, 0.0, 0.12), IDLE_GREY
    touched_by_gate = any(
        i in op["qubits"] and op["name"] not in ("h", "barrier")
        for layer in layers[1:stage] for op in layer
    )
    return (1.0, 0.0, 0.0), (FLIGHT_GOLD if touched_by_gate else H_BLUE)


def render_step_figure(layers, n_count, stage, measure_stage, shot, ok):
    """shot: bitstring campionata (stringa) o None se non ancora misurato. ok: bool se `shot`
    porta a fattori corretti (None se shot è None)."""
    fig = make_subplots(
        rows=1, cols=n_count, specs=[[{"type": "scene"}] * n_count],
        subplot_titles=[f"c{i}" for i in range(n_count)], horizontal_spacing=0.008,
    )
    collapsed = stage >= measure_stage and shot is not None
    for i in range(n_count):
        fig.add_trace(_sphere_surface(), row=1, col=i + 1)
        fig.add_trace(_axis_lines(), row=1, col=i + 1)
        if collapsed:
            bit = shot[i] if i < len(shot) else "0"
            vec = (0.0, 0.0, 1.0 if bit == "0" else -1.0)
            color = OK_GREEN if ok else BAD_RED
        else:
            vec, color = _qubit_visual_state(i, stage, layers)
        x, y, z = vec
        fig.add_trace(go.Scatter3d(
            x=[0, x], y=[0, y], z=[0, z], mode="lines+markers",
            line=dict(color=color, width=8), marker=dict(size=[0, 6], color=color),
            hoverinfo="skip", showlegend=False,
        ), row=1, col=i + 1)
        key = "scene" if i == 0 else f"scene{i + 1}"
        fig.update_layout(**{key: _scene_axes("")})
    fig.update_layout(height=230, margin=dict(l=0, r=0, t=22, b=0), showlegend=False)
    return fig


def _work_register_badges(layers, n_count, num_qubits, stage):
    touched = set()
    for layer in layers[:stage]:
        for op in layer:
            touched |= {q for q in op["qubits"] if q >= n_count}
    n_work = num_qubits - n_count
    if n_work <= 0:
        return
    chips = []
    for i in range(n_work):
        q = n_count + i
        color = FLIGHT_GOLD if q in touched else IDLE_GREY
        chips.append(
            f'<span style="background:{color};color:#111;border-radius:8px;padding:2px 9px;'
            f'margin-right:4px;font-size:12px;">w{i}</span>'
        )
    st.caption("Registro di lavoro (ancilla, mai misurato):")
    st.markdown(" ".join(chips), unsafe_allow_html=True)


def _stage_labels(layers):
    labels = ["Prima di iniziare: tutti i qubit count a |0⟩"]
    for layer in layers:
        names = {op["name"] for op in layer}
        if "barrier" in names:
            labels.append("Checkpoint (nessun effetto fisico, solo un separatore)")
        elif "measure" in names:
            labels.append("Misura: il registro count collassa")
        elif "QFT⁻¹" in names:
            labels.append("QFT⁻¹: legge il periodo nascosto nelle fasi")
        elif "h" in names:
            labels.append("Inizializzazione: H sul registro count, |1⟩ sul registro di lavoro")
        else:
            labels.append(f"Moltiplicazione modulare controllata: {next(iter(names))}")
    return labels


NOISE_KIND_LABELS = {
    "Depolarizzante extra": "depolarizing",
    "Decoerenza (T1/T2 basso)": "decoherence",
    "Errore di lettura (readout)": "readout",
}


def _noise_rule_text(spec):
    if spec["kind"] == "decoherence":
        t1, t2 = spec["value"]
        val_txt = f"T1={t1:,} ns, T2={t2:,} ns"
    else:
        val_txt = f"{spec['value']:.2f}"
    return f"`{spec['qubit_label']}` — {spec['kind_label']} ({val_txt})"


def _targeted_noise_controls(qubit_labels):
    """UI per il rumore MIRATO, qubit per qubit: ogni qubit può avere una regola indipendente
    (tipo + intensità propri), non un unico tipo condiviso da un gruppo — si aggiungono una alla
    volta a una lista, sopra il rumore di base già scelto. Ritorna (target_qubit_indices, extra_noise).
    """
    if "noise_specs" not in st.session_state:
        st.session_state.noise_specs = []  # lista di {'qubit_label','qubit_idx','kind','kind_label','value'}
    # se cambia il circuito (N/a diversi) i vecchi indici qubit non hanno più senso
    if st.session_state.get("noise_specs_for") != tuple(qubit_labels):
        st.session_state.noise_specs = []
        st.session_state.noise_specs_for = tuple(qubit_labels)

    with st.expander("🎯 Rumore mirato, qubit per qubit (facoltativo)",
                      expanded=bool(st.session_state.noise_specs)):
        st.caption(
            "Aggiungi una regola alla volta: ogni qubit può avere un tipo e un'intensità di "
            "rumore diversi. Si sommano al rumore di base scelto sopra, non lo sostituiscono."
        )
        ac1, ac2 = st.columns([1, 1.3])
        with ac1:
            add_qubit = st.selectbox("Qubit", qubit_labels, key="add_noise_qubit")
        with ac2:
            add_kind_label = st.selectbox("Tipo di rumore", list(NOISE_KIND_LABELS.keys()), key="add_noise_kind")
        kind = NOISE_KIND_LABELS[add_kind_label]

        if kind == "depolarizing":
            value = st.slider("Probabilità extra di depolarizzazione", 0.0, 0.9, 0.3, step=0.05,
                               key="add_noise_depol")
        elif kind == "decoherence":
            dc1, dc2 = st.columns(2)
            with dc1:
                t1 = st.select_slider("T1 (ns)", options=[500, 1_000, 5_000, 20_000, 50_000], value=1_000,
                                       key="add_noise_t1")
            with dc2:
                t2 = st.select_slider("T2 (ns)", options=[500, 1_000, 5_000, 20_000, 50_000], value=1_000,
                                       key="add_noise_t2")
            value = [t1, t2]
        else:
            value = st.slider("Probabilità di errore in lettura", 0.0, 0.5, 0.2, step=0.05,
                               key="add_noise_ro")

        if st.button("➕ Aggiungi regola su questo qubit"):
            others = [s for s in st.session_state.noise_specs if s["qubit_label"] != add_qubit]
            others.append({"qubit_label": add_qubit, "qubit_idx": qubit_labels.index(add_qubit),
                            "kind": kind, "kind_label": add_kind_label, "value": value})
            st.session_state.noise_specs = others
            st.rerun()

        if st.session_state.noise_specs:
            st.write("**Regole attive** (una per qubit — aggiungerne una nuova sullo stesso qubit sostituisce la precedente):")
            for i, spec in enumerate(st.session_state.noise_specs):
                rc1, rc2 = st.columns([5, 1])
                with rc1:
                    st.markdown("- " + _noise_rule_text(spec))
                with rc2:
                    if st.button("🗑️ rimuovi", key=f"del_noise_{i}"):
                        st.session_state.noise_specs.pop(i)
                        st.rerun()

    specs = st.session_state.noise_specs
    if not specs:
        return [], None
    target_indices = sorted({s["qubit_idx"] for s in specs})
    extra_noise = [{"qubits": [s["qubit_idx"]], "kind": s["kind"], "value": s["value"]} for s in specs]
    return target_indices, extra_noise


def _sample_one_shot(N, a, n_count, noise_cfg, extra_noise=None):
    seed = int(time.time() * 1000) % 100_000
    counts = sg.run_shots_isolated(N, a, n_count, noise_cfg, shots=1, seed=seed, extra_noise=extra_noise)
    return next(iter(counts))


def _circuit_success_probability(N, a, n_count, shots=200):
    """Probabilità di successo di QUESTO circuito, senza rumore — calcolata una volta per
    (N, a) e tenuta in cache. Anche senza rumore Shor non ha successo al 100% (periodi
    degeneri, cfr. N=15 r=4): l'utente deve poter vedere quel numero accanto al singolo shot
    che ha appena ottenuto, non solo "corretto/sbagliato" senza contesto."""
    key = (N, a)
    cached = st.session_state.get("ideal_prob_cache")
    if cached and cached["key"] == key:
        return cached["pct"], cached["shots"]
    counts = sg.run_shots_isolated(N, a, n_count, None, shots=shots, seed=99)
    total = sum(counts.values())
    ok = sum(
        n for b, n in counts.items()
        if (lambda pq: pq[0] is not None and pq[0] * pq[1] == N)(sg.extract_factors(int(b, 2), n_count, N, a))
    )
    pct = 100 * ok / total if total else 0
    st.session_state.ideal_prob_cache = {"key": key, "pct": pct, "shots": shots}
    return pct, shots


def _result_panel(shot, N, a, n_count, ok):
    p, q = sg.extract_factors(int(shot, 2), n_count, N, a)
    if ok:
        st.success(f"Shot misurato: `{shot}` → fattori **{p} × {q} = {N}** ✅")
        st.caption(f"Shor trova un solo fattore ({p}); l'altro è per divisione classica: {N} / {p} = {q}.")
    else:
        st.error(f"Shot misurato: `{shot}` → nessun fattore valido da questo shot ❌")

    st.markdown("**Shor è probabilistico: un solo tentativo non basta sempre.** Prova più iterazioni:")
    rc1, rc2 = st.columns([1, 2.5])
    with rc1:
        retry_clicked = st.button("🔁 Prova 10 iterazioni", key="retry10_btn", use_container_width=True)
    if retry_clicked:
        with st.spinner("Eseguo 10 tentativi..."):
            seed = int(time.time() * 1000) % 100_000
            counts = sg.run_shots_isolated(N, a, n_count, None, shots=10, seed=seed)
        n_ok = sum(
            n for b, n in counts.items()
            if (lambda pq: pq[0] is not None and pq[0] * pq[1] == N)(sg.extract_factors(int(b, 2), n_count, N, a))
        )
        st.session_state.retry10_result = (counts, n_ok)

    result = st.session_state.get("retry10_result")
    if result:
        counts, n_ok = result
        with rc2:
            st.metric("Su 10 iterazioni, quante trovano i fattori", f"{n_ok}/10")
        icons = []
        for b, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            p2, q2 = sg.extract_factors(int(b, 2), n_count, N, a)
            succ = p2 is not None and p2 * q2 == N
            icons += (["✅"] if succ else ["❌"]) * n
        st.write(" ".join(icons))

    with st.spinner("Stimo la probabilità di successo di questo circuito..."):
        prob_pct, prob_shots = _circuit_success_probability(N, a, n_count)
    st.caption(f"Su {prob_shots} esecuzioni ideali la probabilità di successo è **{prob_pct:.0f}%** — "
               "per questo conviene sempre ripetere più volte, non fidarsi di un solo tentativo.")


# ---------------------------------------------------------------------------
# Modalità passo-passo
# ---------------------------------------------------------------------------
def _render_stage_controls(measure_stage):
    """Righe di comando (Reset/Avanti/Play automatico/progresso). Va chiamata da DENTRO lo
    stesso `with st.container(border=True):` del blocco "N da fattorizzare" in render(), non in
    un container riaperto più tardi: due `with` separati sullo stesso container producono due
    riquadri visivi distinti invece di uno solo (verificato). Ritorna True se l'autoplay deve
    avanzare di uno stadio a fine pagina."""
    if "step_autoplay" not in st.session_state:
        st.session_state.step_autoplay = False
    stage = st.session_state.step_stage
    autoplay_on = st.session_state.step_autoplay and stage < measure_stage

    b1, b2, b3, b4 = st.columns([1, 1, 1.3, 1.6])
    with b1:
        if st.button("↺ Reset"):
            st.session_state.step_stage = 0
            st.session_state.step_shot = None
            st.session_state.step_autoplay = False
            st.session_state.pop("retry10_result", None)
            st.rerun()
    with b2:
        if st.button("Avanti", disabled=(stage >= measure_stage or autoplay_on),
                     type="primary" if stage < measure_stage else "secondary"):
            st.session_state.step_stage = min(stage + 1, measure_stage)
            st.rerun()
    with b3:
        if autoplay_on:
            if st.button("⏸ Ferma"):
                st.session_state.step_autoplay = False
                st.rerun()
        else:
            if st.button("▶ Play automatico", disabled=(stage >= measure_stage)):
                st.session_state.step_autoplay = True
                st.rerun()
    with b4:
        st.progress(stage / measure_stage if measure_stage else 0,
                    text=f"Stadio {stage} / {measure_stage}")
    return autoplay_on


def _render_step_details(N, a, n_count, layers, measure_stage, noise_cfg, extra_noise=None,
                          target_qubits=None, autoplay_on=False):
    """Circuito, sfere di Bloch e pannello risultato per lo stadio corrente — va chiamata FUORI
    dal riquadro dei comandi, in flusso normale."""
    stage = st.session_state.step_stage
    stage_names = _stage_labels(layers)

    # Il puntino/colonna evidenziata nel circuito, la sfera di Bloch e ogni altro elemento
    # vengono disegnati UNA volta per stadio da questa stessa funzione, sia che ci si arrivi
    # con un click su "Avanti" sia con l'autoplay (vedi sotto): stesso identico percorso di
    # rendering, quindi restano garantiti in sincrono per costruzione, non per coincidenza.
    if stage == measure_stage and st.session_state.step_shot is None:
        with st.spinner("Misuro (Qiskit Aer, sottoprocesso isolato)..."):
            st.session_state.step_shot = _sample_one_shot(N, a, n_count, noise_cfg, extra_noise)
    shot = st.session_state.step_shot if stage >= measure_stage else None
    ok = None
    if shot is not None:
        p, q = sg.extract_factors(int(shot, 2), n_count, N, a)
        ok = p is not None and p * q == N

    st.markdown(f"##### Stadio {stage} — {stage_names[min(stage, len(stage_names) - 1)]}")
    svg = circuit_view.render_circuit_svg(
        layers, st.session_state.step_qubit_labels, active_layer_index=(stage - 1 if stage > 0 else -1),
        noisy_qubits=target_qubits,
    )
    components.html(svg, height=circuit_view.TOP_MARGIN + st.session_state.step_num_qubits
                     * circuit_view.ROW_H + 20)
    fig = render_step_figure(layers, n_count, stage, measure_stage, shot, ok)
    st.plotly_chart(fig, use_container_width=True)
    _work_register_badges(layers, n_count, st.session_state.step_num_qubits, stage)
    if shot is not None:
        _result_panel(shot, N, a, n_count, ok)

    if autoplay_on:
        # avanza di UN solo stadio e forza un rerun completo e pulito — stesso percorso di
        # rendering del click manuale, garantendo che "sei qui" si sposti in sincrono
        time.sleep(1.1)
        st.session_state.step_stage = min(stage + 1, measure_stage)
        st.rerun()


# ---------------------------------------------------------------------------
# Modalità multi-run statistico
# ---------------------------------------------------------------------------
def _render_multi_run(N, a, n_count, noise_cfg, extra_noise=None, target_qubits=None):
    st.caption(
        "Nel mondo reale il rumore impone di ripetere l'esecuzione molte volte: lo stesso "
        "circuito gira N volte con lo stesso rumore, e vediamo quanto diventa credibile il "
        "risultato più frequente man mano che aumentano le iterazioni."
    )
    with st.container(border=True):
        # per N non validati (circuito generico Beauregard) il rumore rallenta molto la
        # simulazione (misurato: ~2-3s/shot contro ~0.05-0.2s/shot per N=15/21/35): 1000/5000
        # shot diventerebbero minuti di attesa in una demo dal vivo, quindi non li propongo.
        shot_options = [10, 100, 1000, 5000] if N in sg.VALIDATED_N else [10, 25, 50, 100]
        default_shots = 100 if N in sg.VALIDATED_N else 10
        shots = st.select_slider("Numero di iterazioni", options=shot_options, value=default_shots,
                                  key="multirun_shots")
        warn = sg.speed_warning(N, shots, noise_cfg, extra_noise)
        if warn:
            st.warning(warn)
        run_clicked = st.button("▶ Esegui", type="primary", use_container_width=True)

    if run_clicked:
        with st.spinner(f"Eseguo {shots} iterazioni..."):
            try:
                st.session_state.multirun_counts = sg.run_shots_isolated(
                    N, a, n_count, noise_cfg, shots=shots, seed=42, extra_noise=extra_noise,
                )
                st.session_state.multirun_key = (N, a, shots, str(noise_cfg), str(extra_noise))
            except subprocess.TimeoutExpired:
                st.session_state.multirun_counts = None
                st.error("Troppo lento: il circuito non ha finito in tempo utile. Prova con meno "
                          "iterazioni o un N più piccolo.")

    counts = st.session_state.get("multirun_counts")
    if not counts:
        return
    xs = sorted(counts, key=lambda k: -counts[k])[:8]
    fig = go.Figure()
    fig.add_bar(x=xs, y=[counts[x] for x in xs], marker_color=H_BLUE)
    fig.update_layout(xaxis_title="Esito (bin)", yaxis_title="Conteggio", height=340,
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    n_ok, total = 0, sum(counts.values())
    for b, n in counts.items():
        p, q = sg.extract_factors(int(b, 2), n_count, N, a)
        if p and p * q == N:
            n_ok += n
    pct = 100 * n_ok / total if total else 0
    st.metric("Probabilità di successo", f"{pct:.0f}%", help=f"{n_ok} su {total} iterazioni")

    top_b = max(counts, key=counts.get)
    p, q = sg.extract_factors(int(top_b, 2), n_count, N, a)
    top_ok = p is not None and p * q == N
    if top_ok:
        st.success(f"L'esito più frequente (`{top_b}`, {counts[top_b]} iterazioni) dà i fattori "
                   f"corretti: {p} × {q} = {N}.")
    else:
        st.info("L'esito più frequente da solo non basta qui: guarda gli altri picchi, o aumenta le iterazioni.")

    st.markdown("##### Il circuito e i qubit per l'esito più frequente")
    layers = st.session_state.step_layers
    measure_stage = len(layers)
    svg = circuit_view.render_circuit_svg(
        layers, st.session_state.step_qubit_labels, active_layer_index=measure_stage - 1,
        noisy_qubits=target_qubits,
    )
    components.html(svg, height=circuit_view.TOP_MARGIN + st.session_state.step_num_qubits
                     * circuit_view.ROW_H + 20)
    fig = render_step_figure(layers, n_count, measure_stage, measure_stage, top_b, top_ok)
    st.plotly_chart(fig, use_container_width=True)
    _work_register_badges(layers, n_count, st.session_state.step_num_qubits, measure_stage)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def render():
    st.subheader("🧮 Fattorizza un numero con Shor")
    st.caption(
        "Due percorsi separati: **senza rumore** per capire passo dopo passo come funziona il "
        "circuito, **con rumore** per configurare gli errori e vedere su quante iterazioni il "
        "risultato resta affidabile."
    )

    with_noise = st.pills(
        "Percorso", ["Senza rumore (passo-passo)", "Con rumore (statistico)"],
        default="Senza rumore (passo-passo)", key="top_path",
    ) == "Con rumore (statistico)"

    # Tutto (N, eventuali messaggi, e — nel percorso senza rumore — i comandi di stadio) sta in
    # UN SOLO with contiguo: due `with` separati sullo stesso container producono due riquadri
    # visivi distinti invece di uno, quindi qui dentro non deve mai chiudersi e riaprirsi.
    box = st.container(border=True)
    with box:
        c1, c2 = st.columns([3, 1])
        with c1:
            n_input = st.number_input(
                "N da fattorizzare", min_value=4, max_value=100_000,
                value=st.session_state.get("step_N_input", 15), step=1,
                help=f"Per N = 15, 21, 35 uso il circuito già validato in tesi; per qualsiasi "
                     f"altro N (fino a {sg.N_CAP}) costruisco un circuito reale equivalente "
                     "(Beauregard 2002), ma senza numeri di tesi con cui confrontarlo.",
            )
        with c2:
            st.write("")
            st.write("")
            go_clicked = st.button("🧮 Fattorizza", type="primary", use_container_width=True)

        if go_clicked or "step_preprocess" not in st.session_state:
            st.session_state.step_N_input = int(n_input)
            try:
                # seed derivato da N (non una costante fissa): con un seed unico globale, la
                # scelta casuale della base 'a' finiva quasi sempre "fortunata" per quasi ogni N
                # piccolo digitabile in demo, saltando il circuito quantistico quasi sempre.
                pp = sg.classical_preprocess(int(n_input), seed=int(n_input) * 7919 + 42)
                st.session_state.step_preprocess = pp
                st.session_state.step_N = int(n_input)
                st.session_state.step_error = None
            except ValueError as e:
                st.session_state.step_error = str(e)
                st.session_state.step_preprocess = None
            st.session_state.step_stage = 0
            st.session_state.step_shot = None
            st.session_state.pop("multirun_counts", None)
            st.session_state.pop("retry10_result", None)

        if st.session_state.get("step_error"):
            st.error(st.session_state.step_error)
            return

        pp = st.session_state.get("step_preprocess")
        if pp is None:
            return
        N = st.session_state.step_N

        if pp["done"]:
            msg = f"**{pp['reason']}.**"
            if pp["p"]:
                msg += f" Fattori: {pp['p']} × {pp['q']} = {N}."
            st.info("✅ " + msg + " Non serve il quantum computer per questo N.")
            return

        a = pp["a"]
        if not pp.get("validated", False):
            st.caption(f"ℹ️ Base scelta automaticamente (a={a}) — circuito reale, ma non "
                       "confrontabile con numeri di tesi.")

        n_count = sg.n_count_for(N)
        cache_key = (N, a)
        if st.session_state.get("step_layers_key") != cache_key:
            layers, num_qubits = sg.circuit_layers(N, a, n_count)
            st.session_state.step_layers = layers
            st.session_state.step_num_qubits = num_qubits
            st.session_state.step_qubit_labels = (
                [f"count[{i}]" for i in range(n_count)] + [f"work[{i}]" for i in range(num_qubits - n_count)]
            )
            st.session_state.step_layers_key = cache_key
            st.session_state.step_stage = 0
            st.session_state.step_shot = None
            st.session_state.pop("retry10_result", None)

        layers = st.session_state.step_layers
        measure_stage = len(layers)

        autoplay_on = False
        if not with_noise:
            # Percorso 1: SENZA rumore — i comandi restano nello stesso riquadro di N.
            autoplay_on = _render_stage_controls(measure_stage)

    if not with_noise:
        _render_step_details(N, a, n_count, layers, measure_stage, None, None, None, autoplay_on)
        return

    # Percorso 2: CON rumore — configuri il rumore, poi scegli quante iterazioni.
    st.markdown("##### 1. Configura il rumore")
    noise_label = st.pills("Rumore di base", ["UC1 — NISQ realistico", "UC2 — NISQ degradato"],
                            default="UC1 — NISQ realistico", key="step_noise")
    noise_cfg = NOISE_PRESETS[noise_label]

    target_qubits, extra_noise = _targeted_noise_controls(st.session_state.step_qubit_labels)

    st.markdown("##### 2. Quante iterazioni")
    _render_multi_run(N, a, n_count, noise_cfg, extra_noise, target_qubits)
