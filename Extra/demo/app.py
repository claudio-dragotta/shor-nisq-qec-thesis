"""Demo interattiva della tesi: Shor su NISQ, l'ablazione ML->TOP-K, e la QEC.

Avvio locale:
    pip install -r requirements.txt
    streamlit run app.py

Avvio in Docker: vedi README.md.

Vista di default: il simulatore live (esegue dal vivo, con Qiskit + Qiskit Aer, il VERO
circuito di Shor N=15, a=7 — import da
Extra/experiments/campagne_classiche_M1-M4/shor_core.py, richiede quindi qiskit/qiskit-aer,
vedi requirements.txt). Il pulsante "Teoria →" nell'angolo in alto a destra apre le altre 6
sezioni (il problema, TOP-K, ablazione ML, QEC, Shor logico, bilancio), che leggono solo i
JSON già calcolati in Extra/experiments/ e i numeri già validati in tesi — nessuna dipendenza
da Qiskit per quella parte. "← Torna al simulatore" riporta alla vista di default.
"""
import faulthandler
import sys

faulthandler.enable(file=sys.stderr)  # traccia C-level su segfault, per diagnosticare crash rari

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import bloch_view
import circuit_view
import qpu_view
import steane_backend
import steane_view
import step_view
import data
import quantum_backend as qb

st.set_page_config(page_title="Demo tesi — Shor, TOP-K, QEC", page_icon="⚛️", layout="wide")

# Font e "chrome" ispirati a atarashigoestosicily.com (Space Grotesk/Space Mono, accento lime
# su sfondo quasi nero) — SOLO l'interfaccia: non tocca i colori dei grafici (quelli restano
# fedeli alle figure statiche della tesi, vedi commento in .streamlit/config.toml). Il font
# viene caricato da Google Fonts lato browser (non a build-time): se il client è offline
# degrada semplicemente al sans-serif di sistema, non rompe nulla.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    code, .stCaption, div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        font-family: 'Space Mono', monospace;
    }

    .block-container { padding-top: 2.2rem; max-width: 1180px; }
    h1, h2, h3, h4, h5 {
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; letter-spacing: -0.01em;
    }

    div[data-testid="stMetric"] {
        background: #141414; border-radius: 10px; padding: 0.6rem 0.9rem;
        border: 1px solid #262620;
    }
    div[data-testid="stMetricValue"] { color: #C6F24E; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
    .stTabs [aria-selected="true"] { color: #C6F24E !important; }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: #C6F24E; color: #0a0a0a; border: none; font-weight: 700;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: #d8ff7a; box-shadow: 0 0 16px rgba(244,120,37,.35);
    }

    [data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #262620 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "view" not in st.session_state:
    st.session_state.view = "simulatore"

nav_l, nav_r = st.columns([6, 1])
with nav_l:
    st.title("⚛️ Dal rumore alla correzione")
    st.caption(
        "Shor su NISQ, l'ablazione del ML, la QEC — Claudio Dragotta · "
        "Relatore Ing. Floriano Caprio · Università Campus Bio-Medico di Roma"
    )
with nav_r:
    st.write("")
    if st.session_state.view == "simulatore":
        if st.button("Teoria →", use_container_width=True):
            st.session_state.view = "teoria"
            st.rerun()
    else:
        if st.button("← Torna al simulatore", use_container_width=True):
            st.session_state.view = "simulatore"
            st.rerun()
st.divider()

if st.session_state.view == "teoria":
    tab_problema, tab_topk, tab_ablazione, tab_qec, tab_logico, tab_bilancio, tab_vecchia = st.tabs(
        [
            "1. Il problema",
            "2. TOP-K",
            "3. Ablazione ML",
            "4. QEC: repetition → Steane → surface",
            "5. Shor logico",
            "6. Bilancio",
            "0. Vecchia versione (autoplay)",
        ]
    )

    # ---------------------------------------------------------------------------
    # TAB 1 — Il problema
    # ---------------------------------------------------------------------------
    with tab_problema:
        st.header("L'algoritmo di Shor su hardware rumoroso (NISQ)")
        st.markdown(
            """
Shor fattorizza interi in tempo polinomiale, ma la sua sotto-routine quantistica
(la stima di fase, **QPE**) produce una distribuzione di probabilità sull'output.
Su un simulatore/hardware **senza rumore** questa distribuzione ha pochi picchi
netti, da cui si ricava il periodo `r` e quindi i fattori. **Con il rumore**
NISQ (depolarizzazione + T1/T2 + errore di readout) la distribuzione si allarga:
serve ripetere l'esperimento più volte prima di ottenere un output che porti al
fattore corretto.
    """
        )

        st.subheader("I 4 use case sperimentali")
        st.markdown(
            "Stesso circuito (N=15) con rumore diverso (UC1 vs UC2) per isolare l'effetto "
            "del rumore, e N crescente (UC1→UC3→UC4) a parità di rumore per la scalabilità."
        )
        st.dataframe(
            {
                "Use case": [u[0] for u in data.USE_CASES],
                "N": [u[1] for u in data.USE_CASES],
                "a": [u[2] for u in data.USE_CASES],
                "periodo r atteso": [u[3] for u in data.USE_CASES],
                "n_count (qubit)": [u[4] for u in data.USE_CASES],
                "Rumore": [u[6] for u in data.USE_CASES],
                "ε_1q": [u[7] for u in data.USE_CASES],
                "ε_2q": [u[8] for u in data.USE_CASES],
                "T1 (ns)": [u[9] for u in data.USE_CASES],
                "T2 (ns)": [u[10] for u in data.USE_CASES],
                "p_ro": [u[11] for u in data.USE_CASES],
            },
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Schema illustrativo: come il rumore allarga il picco QPE")
        st.caption("Schema qualitativo per la spiegazione — non sono dati sperimentali reali.")
        rng = np.random.default_rng(0)
        n_bins = 64
        true_peak = 20
        ideal = np.zeros(n_bins)
        ideal[true_peak] = 1.0
        x = np.arange(n_bins)
        noisy = np.exp(-0.5 * ((x - true_peak) / 4.0) ** 2)
        noisy += rng.uniform(0, 0.05, size=n_bins)
        noisy /= noisy.sum()
        fig = go.Figure()
        fig.add_bar(x=x, y=ideal, name="QPE ideale (senza rumore)", marker_color="#2E86AB", opacity=0.85)
        fig.add_bar(x=x, y=noisy, name="QPE rumoroso (NISQ)", marker_color="#E76F51", opacity=0.65)
        fig.update_layout(
            barmode="overlay",
            xaxis_title="Esito misura (intero su n_count bit)",
            yaxis_title="Probabilità",
            legend=dict(orientation="h", y=1.15),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "Il rumore **allarga** la distribuzione ma **non ne distrugge la struttura**: "
            "il picco vero resta quasi sempre tra i pochi esiti più frequenti. È esattamente "
            "questa osservazione a motivare la strategia TOP-K del prossimo passo."
        )

    # ---------------------------------------------------------------------------
    # TAB 3 — TOP-K
    # ---------------------------------------------------------------------------
    with tab_topk:
        st.header("La strategia che funziona: cercare tra i TOP-4 candidati")
        st.markdown(
            """
**Metodo 1** prende solo l'esito più frequente (TOP-1) e ripete l'intero circuito
finché non è quello giusto: sotto rumore servono in media molte iterazioni.
**M_TOP4** prova invece i 4 esiti più frequenti di *una singola* esecuzione, senza
alcun classificatore: quasi sempre il fattore corretto si trova già tra questi 4.
    """
        )

        m1_bar = {r[0]: r for r in data.ABLATION_TABLE if r[1].startswith("M1")}
        top4_bar = {r[0]: r for r in data.ABLATION_TABLE if r[1].startswith("M_TOP4")}

        col1, col2 = st.columns(2)
        for col, uc in zip((col1, col2), ("UC1", "UC2")):
            with col:
                m1 = m1_bar[uc]
                top4 = top4_bar[uc]
                fig = go.Figure()
                fig.add_bar(
                    x=["M1 (TOP-1)", "M_TOP4 (no clf)"],
                    y=[m1[3], top4[3]],
                    marker_color=["#6c757d", "#2E86AB"],
                    text=[f"{m1[3]:.2f}", f"{top4[3]:.2f}"],
                    textposition="outside",
                )
                fig.update_layout(
                    title=f"{uc}: M̄ (iterazioni medie), ρ = {top4[4]}",
                    yaxis_title="M̄ (iterazioni medie)",
                    height=340,
                )
                st.plotly_chart(fig, use_container_width=True)

        st.info(
            "**Risultato**: TOP-4 riduce M̄ da 6.43 a 1.00 su UC1 (ρ = 6.435, p < 0.001) e da "
            "2.42 a 1.00 su UC2 (ρ = 2.417, p = 0.003) — **senza addestramento e senza "
            "classificatore**, robusto su tutto il range di rumore NISQ testato (campagna "
            "parametrica, Appendice A)."
        )

    # ---------------------------------------------------------------------------
    # TAB 4 — Ablazione ML
    # ---------------------------------------------------------------------------
    with tab_ablazione:
        st.header("L'ablazione: quanto ci mette davvero il classificatore ML?")
        st.markdown(
            "L'ipotesi di partenza della tesi era che un classificatore ML addestrato sugli "
            "istogrammi rumorosi (**M2** = CLF + TOP-4) riducesse le iterazioni. Il confronto "
            "a tre — **M1** (TOP-1), **M_TOP4** (TOP-4 senza classificatore), **M2** "
            "(CLF + TOP-4) — isola il contributo del solo classificatore."
        )

        df = pd.DataFrame(
            data.ABLATION_TABLE,
            columns=["Use case", "Variante", "P_succ (%)", "M̄", "ρ vs M1", "p-value vs M1"],
        )
        st.dataframe(df, hide_index=True, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.success(f"**UC1 — il classificatore è superfluo.**\n\n{data.ABLATION_NOTE_UC1}")
        with c2:
            st.error(f"**UC2 — il classificatore è dannoso.**\n\n{data.ABLATION_NOTE_UC2}")

        st.markdown(
            """
**Conclusione (capitolo ponte della tesi)**: il guadagno osservato è interamente
della ricerca multi-candidato TOP-4, non del classificatore ML. Il classificatore
è **neutro** su UC1 e **dannoso** su UC2 (troppo conservativo al rumore nominale,
scarta iterazioni con segnale QPE parziale che TOP-4 avrebbe risolto).

Un ML applicato **a valle** dell'esecuzione (come filtro sull'output) non serve.
Questo risultato negativo motiva il pivot della tesi verso la **QEC**: se
l'informazione distrutta dal rumore non è recuperabile a valle, l'errore va
corretto **durante** l'esecuzione, non dopo.
    """
        )

    # ---------------------------------------------------------------------------
    # TAB 5 — QEC ladder
    # ---------------------------------------------------------------------------
    with tab_qec:
        st.header("La correzione d'errore quantistico: dal repetition code al surface code")
        code_choice = st.radio(
            "Codice",
            ["Repetition code (M5)", "Codice di Steane [[7,1,3]] (M6)", "Surface code (M7)"],
            horizontal=True,
        )

        if code_choice.startswith("Repetition"):
            st.markdown(
                "Codice a 3 qubit (bit-flip in base Z, phase-flip in base X), sindrome con "
                "2 ancilla, correzione a lookup table. Curva teorica: "
                r"$p_L = 3p^2 - 2p^3$ (l'errore logico sopravvive solo se **2 o più** dei 3 "
                "qubit fisici sbagliano)."
            )
            fig = go.Figure()
            colors = {"Z": "#2E86AB", "X": "#E76F51"}
            for basis in ("Z", "X"):
                d5 = data.load_m5(basis)
                pts = d5["curve"]["points"]
                p = [pt["p"] for pt in pts if pt["p"] > 0]
                pl = [pt["p_L"] for pt in pts if pt["p"] > 0]
                pl_theory = [pt["p_L_theory"] for pt in pts if pt["p"] > 0]
                pl_se = [pt["p_L_se"] for pt in pts if pt["p"] > 0]
                fig.add_scatter(
                    x=p, y=pl, mode="markers", name=f"empirico (base {basis})",
                    marker=dict(color=colors[basis], size=9),
                    error_y=dict(type="data", array=pl_se, visible=True),
                )
                fig.add_scatter(
                    x=p, y=pl_theory, mode="lines", name=f"teoria 3p²-2p³ (base {basis})",
                    line=dict(color=colors[basis], dash="dash"),
                )
            fig.update_layout(
                xaxis_title="p (errore fisico per qubit)", yaxis_title="p_L (errore logico)",
                xaxis_type="log", yaxis_type="log", height=450,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig, use_container_width=True)
            d5z = data.load_m5("Z")
            st.caption(
                f"Verifica sindrome: 4/4 casi corretti per entrambe le basi (dualità X/Z "
                f"confermata) — {d5z['curve']['shots']:,} shot/punto, seed {d5z['seed']}."
            )

        elif code_choice.startswith("Codice di Steane"):
            st.markdown(
                "Il codice di Steane [[7,1,3]] è il **codice centrale** della tesi: corregge "
                "un errore arbitrario (X, Y o Z) su un qubit qualsiasi tra i 7, con sindrome "
                "a matrice di Hamming."
            )

            st.subheader("Inietta un errore e guarda la correzione — dal vivo")
            st.caption(
                "Esegue **davvero** (Qiskit Aer) l'encoding di |0_L⟩, inietta l'errore scelto, "
                "misura le 6 sindromi e decodifica la correzione — stesso circuito della "
                "campagna M6."
            )
            si1, si2, si3 = st.columns([1, 1.4, 1])
            with si1:
                steane_pauli = st.selectbox("Tipo di errore", ["Nessuno", "X", "Y", "Z"], key="steane_pauli")
            with si2:
                steane_qubit = st.select_slider(
                    "Su quale qubit (0-6)", options=list(range(7)), value=3, key="steane_qubit",
                    disabled=(steane_pauli == "Nessuno"),
                )
            with si3:
                st.write("")
                st.write("")
                run_steane = st.button("⚡ Inietta ed esegui", type="primary")

            if run_steane or "steane_result" not in st.session_state:
                pauli_arg = None if steane_pauli == "Nessuno" else steane_pauli
                with st.spinner("Eseguo il circuito Steane su AerSimulator..."):
                    st.session_state.steane_result = steane_backend.run_injection_isolated(
                        pauli_arg, int(steane_qubit),
                    )
            sres = st.session_state.steane_result

            components.html(steane_view.render_steane_svg(sres), height=210)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Sindrome Z (rileva X)", "".join(map(str, sres["sz"])))
            sc2.metric("Sindrome X (rileva Z)", "".join(map(str, sres["sx"])))
            sc3.metric("Errore identificato", sres["identified"])
            sc4.metric("Stato logico recuperato", "✅ sì" if sres["recovered"] else "❌ no")
            if sres["recovered"]:
                st.success(
                    f"Correzione applicata: **{sres['correction']}**. La sindrome ha "
                    f"identificato correttamente l'errore iniettato — il qubit logico è salvo. "
                    f"Prova un altro qubit o tipo di errore: la sindrome cambia ogni volta ma "
                    f"identifica sempre il qubit giusto (biiettività verificata su tutti e 7 × "
                    f"3 tipi in Cap. 11)."
                )
            st.divider()

            c6 = data.load_m6_curve()
            pts = c6["curve"]["points"]
            p = [pt["p"] for pt in pts]
            pl = [pt["p_L"] for pt in pts]
            pl_se = [pt["p_L_se"] for pt in pts]
            fig = go.Figure()
            fig.add_scatter(
                x=p, y=pl, mode="markers+lines", name="p_L empirico",
                marker=dict(color="#2E86AB", size=9),
                error_y=dict(type="data", array=pl_se, visible=True),
            )
            fig.add_scatter(x=p, y=p, mode="lines", name="break-even (p_L = p)", line=dict(dash="dot", color="gray"))
            fig.update_layout(
                xaxis_title="p (errore fisico per qubit)", yaxis_title="p_L (errore logico)",
                xaxis_type="log", yaxis_type="log", height=450,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig, use_container_width=True)
            ratios = [pt["ratio_p2"] for pt in pts]
            st.caption(
                f"Pendenza log-log ≈ 2 (soppressione **quadratica**: p_L/p² resta "
                f"~{min(ratios):.1f}–{max(ratios):.1f} su tutto il range) → pseudo-soglia ~0.08. "
                f"Encoding e sindrome verificati: {data.load_m6_verify()['verify']} · "
                f"{c6['curve']['shots']:,} shot/punto."
            )

        else:  # surface code
            st.markdown(
                "Surface code simulato con **Stim + PyMatching** (decodifica MWPM), "
                "distanze d = 3, 5, 7. La soglia è il punto in cui le curve per diverso "
                "d si incrociano: sotto soglia, più qubit fisici (d maggiore) = meno errore "
                "logico."
            )
            basis_choice = st.radio("Base", ["Z", "X"], horizontal=True, key="surface_basis")
            d7 = data.load_m7(basis_choice.lower())
            curve = d7["curve"]
            fig = go.Figure()
            colors = {"3": "#2E86AB", "5": "#E76F51", "7": "#2A9D8F"}
            for dist, pts in curve["table"].items():
                p = [pt["p"] for pt in pts]
                pl = [pt["p_L"] for pt in pts]
                pl_se = [pt["p_L_se"] for pt in pts]
                fig.add_scatter(
                    x=p, y=pl, mode="markers+lines", name=f"d = {dist}",
                    marker=dict(color=colors.get(dist, "#333"), size=8),
                    error_y=dict(type="data", array=pl_se, visible=True),
                )
            fig.add_vline(x=curve["threshold"], line_dash="dot", line_color="gray",
                           annotation_text=f"soglia ≈ {curve['threshold']:.1%}")
            fig.update_layout(
                xaxis_title="p (errore fisico per qubit/gate)", yaxis_title="p_L (errore logico)",
                xaxis_type="log", yaxis_type="log", height=450,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Base {basis_choice}: soglia p_th ≈ {curve['threshold']:.1%} · "
                f"sanity check (d↑ ⇒ p_L↓ sotto soglia): "
                f"{'✅ verificato' if curve['sanity_ok'] else '❌ fallito'} · "
                f"{curve['shots']:,} shot/punto."
            )

        st.info(
            "**Il percorso**: repetition code (sindrome, correzione — concetti base) → "
            "Steane [[7,1,3]] (corregge un errore arbitrario) → surface code (scala con la "
            "distanza, sotto soglia p_th ≈ 0.7–0.9%). Ogni gradino riduce l'errore logico "
            "residuo che verrà iniettato nello Shor logico."
        )

    # ---------------------------------------------------------------------------
    # TAB 6 — Shor logico
    # ---------------------------------------------------------------------------
    with tab_logico:
        st.header("Integrazione: lo Shor logico e la figura conclusiva della tesi")
        st.markdown(
            "Si inietta un canale depolarizzante di intensità `p_L` dopo **ogni gate** del "
            "circuito di Shor (N=15, a=7, periodo r=4) e si misura `P_success`: la probabilità "
            "che la misura porti ai fattori corretti (16 384 shot/punto)."
        )

        m8 = data.load_m8()
        pts = m8["curve"]["points"]
        p_l = [pt["p_L"] if pt["p_L"] > 0 else 1e-5 for pt in pts]
        p_succ = [pt["P_success"] for pt in pts]
        p_succ_se = [pt["P_success_se"] for pt in pts]

        fig = go.Figure()
        fig.add_scatter(
            x=p_l, y=p_succ, mode="markers+lines", name="P_success (misurato)",
            marker=dict(color="#2E86AB", size=9),
            error_y=dict(type="data", array=p_succ_se, visible=True),
        )
        fig.add_hline(y=m8["curve"]["P_ideal"], line_dash="dash", line_color="#2A9D8F",
                       annotation_text=f"P_ideal ≈ {m8['curve']['P_ideal']:.2f}")
        fig.add_hline(y=m8["curve"]["P_floor"], line_dash="dash", line_color="#E76F51",
                       annotation_text=f"P_floor (casuale) ≈ {m8['curve']['P_floor']:.2f}")
        for label, pl_regime, p_succ_regime in data.SHOR_LOGICO_REGIMES:
            fig.add_scatter(
                x=[pl_regime], y=[p_succ_regime], mode="markers+text",
                marker=dict(size=14, symbol="diamond", color="black"),
                text=[label], textposition="top center", showlegend=False,
            )
        fig.update_layout(
            xaxis_title="p_L (errore logico per gate)", yaxis_title="P_success",
            xaxis_type="log", height=480,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
**I tre regimi** (marcatori nel grafico), dall'errore logico residuo dei capitoli QEC:

| Regime | p_L | P_success |
|---|---|---|
| Shor fisico nudo (nessuna correzione) | ≈ 10⁻² | ≈ 0.64 |
| Codice di Steane [[7,1,3]] | ≈ 1.7×10⁻³ | ≈ 0.72 |
| Surface code d=7 (sotto soglia) | ≈ 10⁻⁴ | ≈ 0.74 (verso il limite ideale ≈ 0.75) |

Muovendosi verso sinistra (più capacità di correzione → meno errore logico),
`P_success` risale monotonicamente verso il limite ideale ≈ 0.75.
    """
        )

        st.subheader("La soglia dell'80% è cumulativa, non per singola misura")
        st.markdown(
            r"Shor è probabilistico: ripetendo l'esecuzione $k$ volte, "
            r"$P(k) = 1 - (1-P_s)^k$. Una $P_s$ sotto l'80% non impedisce di superare "
            r"quella soglia con poche ripetizioni."
        )
        k = np.arange(1, 9)
        fig2 = go.Figure()
        for ps, color in [(0.75, "#2E86AB"), (0.40, "#E76F51")]:
            pk = 1 - (1 - ps) ** k
            fig2.add_scatter(x=k, y=pk, mode="markers+lines", name=f"P_s = {ps}", line=dict(color=color))
            k_cross = next((int(kk) for kk, v in zip(k, pk) if v >= 0.80), None)
            if k_cross:
                fig2.add_scatter(
                    x=[k_cross], y=[1 - (1 - ps) ** k_cross], mode="markers",
                    marker=dict(size=16, color=color, symbol="circle-open", line=dict(width=3)),
                    showlegend=False,
                )
        fig2.add_hline(y=0.80, line_dash="dot", line_color="gray", annotation_text="soglia 80%")
        fig2.update_layout(
            xaxis_title="k (esecuzioni indipendenti)", yaxis_title="P(k) cumulativa",
            height=380, legend=dict(orientation="h", y=1.15),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Con P_s ≈ 0.75 bastano k=2 esecuzioni per il 94%; anche a P_s = 0.40 ne bastano 4.")

    # ---------------------------------------------------------------------------
    # TAB 7 — Bilancio
    # ---------------------------------------------------------------------------
    with tab_bilancio:
        st.header("Il bilancio dell'intero percorso")
        st.markdown(
            """
1. **Prima campagna** (Cap. 10): TOP-4 riduce M̄ da 6.43 a 1.00 (UC1), robusto a tutti
   i parametri di rumore testati. L'ablazione dimostra che il classificatore ML è
   **neutro** (UC1) o **dannoso** (UC2): il guadagno è tutto della ricerca multi-candidato,
   non dell'apprendimento automatico applicato a valle dell'output.
2. **Seconda campagna** (Cap. 11-13): se il rumore non è recuperabile *a valle*, va
   corretto *durante* l'esecuzione. Percorso a livelli: repetition code → Steane
   [[7,1,3]] → surface code (Stim+PyMatching, soglia ≈ 0.7-0.9%) → **Shor logico**.
3. **Figura conclusiva**: fisico (P≈0.64) → Steane (P≈0.72) → surface d=7 (P≈0.74,
   verso il limite ideale 0.75). Ogni salto di capacità correttiva si traduce in un
   guadagno misurabile e riproducibile.
4. **Limiti dichiarati**: modello logico a canale unico depolarizzante (non
   fault-tolerant completo), sindrome non fault-tolerant, N=15 didattico (N=21
   intrattabile: profondità ~9500 porte). Le stime di risorse per RSA-2048
   (Gidney-Ekerå, milioni di qubit fisici) restano un confronto qualitativo, non
   un'estrapolazione diretta da questi risultati.

**Messaggio unico della tesi**: un filtro ML sull'output rumoroso non serve;
la correzione d'errore strutturale sì, e il guadagno è quantificabile end-to-end.
    """
        )
        st.caption(
            "Fonti: Extra/experiments/ (M1-M8, JSON con seed/shot/parametri dichiarati) · "
            "file_latex/capitoli/RisultatiSperimentali.tex, CorrezioneErrori.tex, "
            "SurfaceCode.tex, ShorLogico.tex."
        )

    # ---------------------------------------------------------------------------
    # TAB 0 — Vecchia versione (autoplay): QPU 3D + circuito SVG + istogrammi.
    # Sostituita come vista di default dalla nuova "Simulatore" (step_view.py) su
    # richiesta del prof — tenuta qui per confronto, invariata.
    # ---------------------------------------------------------------------------
    with tab_vecchia:
        # -----------------------------------------------------------------------
        # Vista di default: simulatore live (esegue il VERO circuito con Qiskit Aer)
        # -----------------------------------------------------------------------
        st.header("Simulatore live: configura il rumore, esegui il vero circuito di Shor")
        st.markdown(
            "Esegue **dal vivo** (Qiskit + Qiskit Aer) il circuito di Shor N=15, a=7 della tesi — "
            "non dati precalcolati. Sopra il disegno, sotto i comandi: ogni volta che muovi un "
            "comando, il disegno si aggiorna **subito**, senza dover premere nulla."
        )

        if "sim_cfg" not in st.session_state:
            st.session_state.sim_cfg = dict(
                eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02, shots=1024, seed=42,
            )

        # I comandi che pilotano il disegno (qubit scelti + probabilità extra) vengono letti da
        # session_state PRIMA di disegnare, cosi' il grafico sta sopra e i comandi sotto ma
        # l'aggiornamento resta immediato ad ogni movimento (i widget Streamlit persistono il loro
        # valore anche se letti prima di essere dichiarati piu' in basso nello script).
        qubit_choice = st.session_state.get("qubit_choice_widget", [])
        extra_p = st.session_state.get("extra_p_widget", 0.0)
        qubit_indices = {qb.QUBIT_LABELS.index(q) for q in qubit_choice}

        cfg = st.session_state.sim_cfg
        eps_1q, eps_2q, t1_ns, t2_ns, p_ro = cfg["eps_1q"], cfg["eps_2q"], cfg["t1_ns"], cfg["t2_ns"], cfg["p_ro"]
        shots, seed = cfg["shots"], cfg["seed"]

        @st.cache_data
        def _cached_layers():
            return qb.base_circuit_layers()

        layers = _cached_layers()

        st.subheader("La QPU in 3D: il segnale entra, i qubit girano, il risultato esce")
        st.caption(
            "Stessi 6 stadi reali del circuito qui sotto (letti dagli stessi layer, nessuna "
            "ricostruzione parallela): init → le due moltiplicazioni modulari controllate non "
            "banali → checkpoint → QFT⁻¹ → misura. L'ago che ruota sopra ogni qubit è una "
            "**metafora didattica** dello stato che cambia — con l'entanglement un singolo qubit "
            "non ha un vettore di Bloch pulito (stesso avvertimento della sfera di Bloch più "
            "sotto), ma stadi, tempi e quali qubit vengono toccati sono quelli veri. "
            "Trascina per ruotare la QPU, premi ▶ per animare il passaggio del segnale."
        )
        st.plotly_chart(
            qpu_view.render_qpu_figure(layers, qb.QUBIT_LABELS, noisy_qubits=qubit_indices,
                                        readout=st.session_state.get("sim_result")),
            use_container_width=True,
        )
        readout_fig = qpu_view.render_readout_preview(st.session_state.get("sim_result"))
        if readout_fig is not None:
            st.caption("Cosa è uscito dalla QPU nell'ultima esecuzione (TOP-6 esiti, ideale vs rumoroso):")
            st.plotly_chart(readout_fig, use_container_width=True)
        else:
            st.caption(
                "Premi *Esegui simulazione* più sotto per vedere qui il risultato vero — per ora "
                "questa è solo l'animazione dei 6 stadi del circuito."
            )

        st.subheader("Il circuito")
        st.caption(
            "Grazie al periodo r=4 solo 2 delle 8 esponenziazioni modulari controllate sono "
            "non banali — per questo il circuito è così compatto. Wire e gate **rossi pulsanti** "
            "= rumore extra assegnato."
        )

        noisy_gate_positions = {
            (c, tuple(sorted(op["qubits"])))
            for c, layer in enumerate(layers)
            for op in layer
            if qubit_indices & set(op["qubits"]) and op["name"] != "barrier"
        }
        svg = circuit_view.render_circuit_svg(
            layers, qb.QUBIT_LABELS, noisy_qubits=qubit_indices, noisy_gate_positions=noisy_gate_positions,
        )
        components.html(svg, height=circuit_view.TOP_MARGIN + 12 * circuit_view.ROW_H + 20)
        st.caption(
            "Le **parentesi colorate** sul margine sinistro segnano i qubit che restano "
            "**entangled** tra loro fino alla fine del circuito (stesso colore = stesso gruppo). "
            "Il connettore sottile tra un gate e l'altro mostra quali qubit quel gate lega — non "
            "tutti quelli che il box sembra attraversare."
        )

        st.subheader("Cosa succede quando DUE qubit si intrecciano? (entanglement)")
        st.markdown(
            "Prendiamo 2 qubit A e B, isolati: H su A poi CNOT(A,B) — è **esattamente** ciò che "
            "fanno i gate `U(7^k)` nel circuito sopra, solo su scala più piccola. Il risultato è "
            "uno **stato di Bell**: A e B presi singolarmente non hanno più una direzione definita "
            "— il vettore sparisce **del tutto**, non per il rumore ma per l'entanglement stesso."
        )
        if "entangle_history" not in st.session_state:
            st.session_state.entangle_history = []
            st.session_state.entangle_outcome = None

        b1, b2, _ = st.columns([1.3, 1, 2])
        with b1:
            if st.button("🎲 Misura A e B insieme"):
                outcome = int(np.random.randint(0, 2))
                st.session_state.entangle_outcome = outcome
                st.session_state.entangle_history.append(outcome)
        with b2:
            if st.button("↺ Reset (torna indeterminato)"):
                st.session_state.entangle_outcome = None
                st.session_state.entangle_history = []

        st.plotly_chart(
            bloch_view.render_entanglement_figure(st.session_state.entangle_outcome),
            use_container_width=True,
        )
        if st.session_state.entangle_outcome is not None:
            o = st.session_state.entangle_outcome
            st.success(
                f"Hai misurato A → **{o}**. B, che **non hai mai toccato**, è risultato **{o}** "
                f"anche lui: sempre concorde, mai l'opposto. Non è che A abbia 'detto' qualcosa a "
                f"B a velocità superluminale — il risultato di entrambi era deciso **insieme** fin "
                f"dallo stato di Bell iniziale; semplicemente, finché nessuno guarda, per entrambi "
                f"è indeterminato. Premi di nuovo *Misura* (dopo *Reset*) per ripeterlo: uscirà "
                f"sempre 00 o 11, mai 01/10."
            )
            hist = st.session_state.entangle_history
            st.caption(
                f"Storico di questa sessione: {len(hist)} misure, "
                f"{hist.count(0)} volte 0, {hist.count(1)} volte 1 — **sempre concordi tra A e B, "
                f"0 volte discordi** su {len(hist)}."
            )
        st.markdown(
            "Il sistema **non è casuale a caso**: le probabilità esatte per lo stato di Bell "
            "confermano che i risultati concordi (00 o 11) coprono il 100% dei casi, quelli "
            "discordi (01/10) lo 0%:"
        )
        st.plotly_chart(bloch_view.render_entanglement_correlation(), use_container_width=True)
        st.caption(
            "Valori esatti per lo stato di Bell (non stimati). È lo stesso motivo per cui i 12 "
            "qubit di Shor sopra non si possono disegnare uno per uno con una freccia propria: "
            "l'informazione sul periodo `r` vive nelle correlazioni **tra** i qubit `count[i]` e "
            "`work[i]` create dai gate `U(7^k)`, non nello stato di un qubit preso da solo."
        )

        st.subheader("Cosa fa il rumore a UN qubit isolato? (sfera di Bloch 3D)")
        st.caption(
            "Qui invece un qubit **non** entangled, per isolare l'effetto del rumore da quello "
            "dell'entanglement. Stessa fisica del canale depolarizzante usata ovunque nella demo. "
            "**Trascina per ruotare**, premi ▶ per animare."
        )
        shrink = 1.0 - extra_p
        bloch_fig = bloch_view.render_bloch_figure(shrink)
        st.plotly_chart(bloch_fig, use_container_width=True)

        st.divider()
        st.subheader("Comandi")
        st.markdown("**Rumore mirato** — aggiorna subito i due disegni sopra:")
        c_q, c_p = st.columns([1.3, 1])
        with c_q:
            st.multiselect(
                "Rumore EXTRA su questi qubit", options=qb.QUBIT_LABELS, key="qubit_choice_widget",
            )
        with c_p:
            st.slider("Probabilità extra di depolarizzazione", 0.0, 0.5, 0.0, step=0.01,
                       key="extra_p_widget")
        st.caption(
            f"`count[i]` = 8 qubit di stima di fase, `work[i]` = 4 qubit di lavoro. Impostata al "
            f"{extra_p:.0%} — ingrandita apposta per essere visibile (il rumore reale per gate, ε_1q, "
            f"è tipicamente sotto l'1%, ma si accumula su centinaia di gate). Passa il mouse sui gate "
            f"nel disegno per una spiegazione."
        )

        st.markdown("**Rumore globale** — usato quando premi *Esegui simulazione* più sotto:")
        with st.form("noise_form"):
            preset = st.radio("Preset", ["UC1 (realistico)", "UC2 (degradato)", "Personalizzato"],
                               horizontal=True)
            if preset == "UC1 (realistico)":
                d_eps1, d_eps2, d_t1, d_t2, d_pro = 1e-3, 1e-2, 100_000, 80_000, 0.02
            elif preset == "UC2 (degradato)":
                d_eps1, d_eps2, d_t1, d_t2, d_pro = 5e-3, 5e-2, 50_000, 30_000, 0.05
            else:
                d_eps1, d_eps2, d_t1, d_t2, d_pro = 1e-3, 1e-2, 100_000, 80_000, 0.02

            fc1, fc2 = st.columns(2)
            with fc1:
                eps_1q_in = st.select_slider("ε_1q (errore gate a 1 qubit)",
                                              options=[1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2], value=d_eps1)
                eps_2q_in = st.select_slider("ε_2q (errore gate a 2 qubit)",
                                              options=[1e-3, 5e-3, 1e-2, 5e-2, 1e-1], value=d_eps2)
                t1_in = st.select_slider("T1 (ns)", options=[30_000, 50_000, 80_000, 100_000, 200_000], value=d_t1)
            with fc2:
                t2_in = st.select_slider("T2 (ns)", options=[20_000, 30_000, 60_000, 80_000, 150_000], value=d_t2)
                pro_in = st.select_slider("p_ro (errore di readout)", options=[0.01, 0.02, 0.05, 0.1], value=d_pro)
                shots_in = st.select_slider("Shot", options=[256, 512, 1024, 2048], value=1024)
            seed_in = st.number_input("Seed", value=42, step=1)

            applied = st.form_submit_button("✔ Applica rumore globale", type="primary", use_container_width=True)
            if applied:
                st.session_state.sim_cfg = dict(
                    eps_1q=eps_1q_in, eps_2q=eps_2q_in, t1_ns=t1_in, t2_ns=t2_in, p_ro=pro_in,
                    shots=shots_in, seed=int(seed_in),
                )
                st.session_state.sim_result = None
        st.caption(f"Impostazioni attive: ε_1q={eps_1q:g} · ε_2q={eps_2q:g} · T1={t1_ns:,} ns · "
                   f"T2={t2_ns:,} ns · p_ro={p_ro:g} · shot={shots} · seed={seed}")

        with st.expander("Avanzate: rumore extra su una singola istanza di gate (circuito trasposto)"):
            st.caption(
                "Per la simulazione il circuito sopra viene trasposto in porte elementari "
                "(H, X, CX, RZ, CP — molte di più delle 21 istruzioni di alto livello): seleziona "
                "righe specifiche per colpire una singola istanza di gate, non un qubit intero."
            )

            @st.cache_data(show_spinner="Costruisco il circuito trasposto...")
            def _cached_gate_rows(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, seed):
                return qb.list_gates_isolated(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, seed)

            gate_rows = _cached_gate_rows(eps_1q, eps_2q, t1_ns, t2_ns, p_ro, int(seed))
            gate_df = pd.DataFrame(gate_rows)
            selection = st.dataframe(
                gate_df, hide_index=True, use_container_width=True, height=260,
                on_select="rerun", selection_mode="multi-row", key="gate_table",
            )
            selected_gate_indices = set(
                gate_df.iloc[selection["selection"]["rows"]]["index"].tolist()
            ) if selection and selection["selection"]["rows"] else set()

        all_extra_indices = selected_gate_indices | qb.gates_touching_qubits(gate_rows, qubit_indices)

        st.subheader("3. Esegui e confronta")
        if st.button("▶ Esegui simulazione (ideale vs rumoroso)", type="primary"):
            with st.spinner("Eseguo il circuito su AerSimulator..."):
                gate_rows, ideal_counts, noisy_counts = qb.run_comparison_isolated(
                    eps_1q, eps_2q, t1_ns, t2_ns, p_ro,
                    all_extra_indices, extra_p, int(shots), int(seed),
                )
            st.session_state.sim_result = dict(ideal_counts=ideal_counts, noisy_counts=noisy_counts)

        result = st.session_state.get("sim_result")
        if result:
            ideal_counts, noisy_counts = result["ideal_counts"], result["noisy_counts"]
            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure()
                xs = sorted(set(ideal_counts) | set(noisy_counts))
                fig.add_bar(x=xs, y=[ideal_counts.get(x, 0) for x in xs], name="Ideale (no rumore)",
                            marker_color="#2E86AB")
                fig.update_layout(title="Istogramma IDEALE (misura QPE)", xaxis_title="Esito (bin)",
                                   yaxis_title="Conteggio", height=380, xaxis_tickangle=-60)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = go.Figure()
                fig2.add_bar(x=xs, y=[noisy_counts.get(x, 0) for x in xs], name="Rumoroso",
                             marker_color="#E76F51")
                fig2.update_layout(title="Istogramma RUMOROSO (con le tue impostazioni)",
                                    xaxis_title="Esito (bin)", yaxis_title="Conteggio", height=380,
                                    xaxis_tickangle=-60)
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Quali qubit misurati sono stati disturbati?")
            st.caption(
                "Per ciascuno degli 8 qubit di conteggio (q0-q7 nel diagramma sopra), differenza "
                "tra P(bit=1) ideale e P(bit=1) rumoroso, marginalizzando su tutti gli shot: dove "
                "la barra è alta, il rumore ha spostato di più la distribuzione di quel qubit."
            )
            ideal_marg = qb.bit_marginals(ideal_counts)
            noisy_marg = qb.bit_marginals(noisy_counts)
            delta = [abs(n - i) for i, n in zip(ideal_marg, noisy_marg)]
            fig3 = go.Figure()
            fig3.add_bar(x=[f"q{i}" for i in range(len(delta))], y=delta, marker_color="#E76F51")
            fig3.update_layout(xaxis_title="qubit di conteggio", yaxis_title="|ΔP(bit=1)|", height=300)
            st.plotly_chart(fig3, use_container_width=True)

            st.subheader("Chi trova i fattori corretti?")
            v1, v2 = st.columns(2)
            with v1:
                st.markdown("**Ideale**")
                st.dataframe(pd.DataFrame(qb.factor_verdict(ideal_counts)), hide_index=True, use_container_width=True)
            with v2:
                st.markdown("**Rumoroso**")
                st.dataframe(pd.DataFrame(qb.factor_verdict(noisy_counts)), hide_index=True, use_container_width=True)

            top1_ideal = qb.top1_success(ideal_counts)
            top1_noisy = qb.top1_success(noisy_counts)
            top4_noisy = qb.top4_success(noisy_counts)
            m1, m2, m3 = st.columns(3)
            m1.metric("M1 (TOP-1) su ideale", "✅ successo" if top1_ideal else "❌ fallito")
            m2.metric("M1 (TOP-1) su rumoroso", "✅ successo" if top1_noisy else "❌ fallito")
            m3.metric("M_TOP4 su rumoroso", "✅ successo" if top4_noisy else "❌ fallito")
            if not top1_ideal:
                st.info(
                    "TOP-1 può fallire **anche senza rumore**: con N=15 il periodo r=4 dà 4 esiti "
                    "QPE equiprobabili, e non tutti portano al fattore (esito 0 fallisce sempre). "
                    "È la degenerazione r=4 discussa nel Cap. 13, non un artefatto del rumore."
                )
            if (not top1_noisy) and top4_noisy:
                st.success(
                    "Con questo rumore il TOP-1 fallisce ma il **TOP-4 recupera il risultato** — "
                    "esattamente il meccanismo del Cap. 10."
                )

            st.subheader("E se questo rumore fosse corretto dalla QEC? (proiezione)")
            st.caption(
                "Proiezione per interpolazione sulle curve già validate (M6 Steane, M7 surface "
                "d=7, M8 Shor logico) usando ε_2q come tasso d'errore fisico rappresentativo — "
                "non una nuova simulazione fault-tolerant esplicita (intrattabile, cfr. Cap. 13)."
            )
            proj = data.project_qec_outcome(eps_2q)
            proj_df = pd.DataFrame([
                {"Regime": "Fisico nudo (nessuna correzione)", "p_L": proj["fisico"]["p_L"],
                 "P_success proiettata": proj["fisico"]["P_success"]},
                {"Regime": "Codice di Steane [[7,1,3]]", "p_L": proj["steane"]["p_L"],
                 "P_success proiettata": proj["steane"]["P_success"]},
                {"Regime": "Surface code d=7", "p_L": proj["surface_d7"]["p_L"],
                 "P_success proiettata": proj["surface_d7"]["P_success"]},
            ])
            st.dataframe(proj_df, hide_index=True, use_container_width=True)
            if proj["surface_d7"]["p_L"] > eps_2q:
                st.warning(
                    f"A ε_2q = {eps_2q:g} sei **sopra la soglia** del surface code (≈0.7–0.9%): "
                    "la correzione peggiora l'errore invece di ridurlo (d maggiore fa danno sopra "
                    "soglia — cfr. Cap. 12). Prova un ε_2q più basso per vedere la soppressione."
                )




else:
    step_view.render()
