# Interactive Thesis Demo — Shor on NISQ, the ML→TOP-K ablation, and QEC

A [Streamlit](https://streamlit.io) web app that makes the thesis tangible: it runs the
**real Shor circuit live** (Qiskit + Qiskit Aer), lets you factor a number **step by step**
with per-qubit Bloch spheres, shows the **ML→TOP-4 ablation** result, and walks the **QEC
ladder** (repetition → Steane → surface) up to the **logical Shor**.

Opens at **`http://localhost:8501`**.

> The Italian version of this document is kept in [`README.it.md`](README.it.md).

---

## What the demo shows

The app opens on the **live simulator** (default view). The **"Teoria →"** button (top
right) opens six theory sections; **"← Torna al simulatore"** goes back.

### Default view — Live simulator (`step_view.py`)
Factor any integer *N* with Shor, via two clearly separated paths (one `st.pills` selector):

- **Senza rumore (step by step):** advance the circuit one stage at a time ("Avanti ▶" or
  auto-play), watching one **Bloch sphere per count qubit** change colour — grey (untouched)
  → blue (after Hadamard) → gold (touched by a controlled/QFT gate) → **green/red** (collapsed
  at measurement, correct or not). Shor returns **one** prime factor; the other is obtained by
  classical division.
- **Con rumore (statistical):** configure the noise (base preset + per-qubit targeted rules),
  then run the circuit **10 / 100 / 1000 / 5000** times and see how reliable the most-frequent
  outcome becomes as the iterations grow.

Free *N* input: for *N* ∈ {15, 21, 35} it uses the exact circuit validated in the thesis
(via `shor_core.py`); for other *N* it builds an equivalent real circuit (Beauregard 2002).

### Theory sections (`app.py`)
1. **Il problema** — how NISQ noise broadens the QPE peak.
2. **TOP-K** — the multi-candidate strategy that reduces the iterations.
3. **Ablazione ML** — the ablation proving the gain comes from TOP-4, **not** the classifier.
4. **QEC** — the ladder repetition → **Steane `[[7,1,3]]`** → surface code, with a **live
   Steane error-injection** experiment (inject a Pauli error, watch the syndrome decode it).
5. **Shor logico** — the concluding figure: `P_success` vs logical error rate for the three
   regimes (physical → Steane → surface).
6. **Bilancio** — the end-to-end summary.
7. **Vecchia versione (autoplay)** — the earlier 3D-QPU view, kept for comparison.

Tabs 1 and 3–7 read **only** the pre-computed JSON results in `../experiments/` (M1–M8) and
the numbers already validated in the thesis — no Qiskit needed for those. The live simulator
(default view) and the Steane injection do run Qiskit Aer for real.

---

## Running the demo

### Local (no Docker)

```bash
cd Extra/demo
pip install -r requirements.txt
streamlit run app.py
```

Requirements: `streamlit`, `plotly`, `numpy`, `pandas`, `qiskit==2.5.0`, `qiskit-aer==0.17.2`.

### Docker (reproducible — same versions as the thesis)

The build context is the **repo root** (needed to include `Extra/experiments/`).

```bash
# from the repo root
docker build -f Extra/demo/Dockerfile -t tesi-demo .
docker run -p 8501:8501 tesi-demo
```

or with Docker Compose (from `Extra/demo/`, its context is already `../..`):

```bash
cd Extra/demo
docker compose up --build
```

### Deploy on Render (public URL)

Render supports Docker deploys directly:

1. Push the repo to GitHub/GitLab.
2. Render → **New → Web Service** → connect the repo.
3. **Runtime:** Docker. **Dockerfile path:** `Extra/demo/Dockerfile`. **Root Directory:**
   leave empty / `.` so the build context is the repo root.
4. Render injects `$PORT` automatically — the Dockerfile already uses it
   (`streamlit run app.py --server.port=$PORT …`), nothing to configure.
5. No database or persistent storage is needed: everything (M1–M8 JSON results, Shor scripts)
   is baked into the image. The first cold start may take 1–2 minutes.

---

## Folder layout

| File / folder | Role |
|---|---|
| `app.py` | Entry point: top navigation + the six theory sections; the default view delegates to `step_view.render()`. |
| `step_view.py` | The default **live simulator**: step-by-step (no-noise) and statistical multi-run (with noise). Free-*N* input. |
| `quantum_backend.py` | Runs the **real** Shor circuit (N=15, a=7) with Qiskit Aer and configurable noise (global / per-qubit / per-gate). |
| `shor_general.py` | Free-*N* generalization; reuses `shor_core.shor_circuit` for N ∈ {15,21,35}, Beauregard for others. |
| `data.py` | Loads the pre-computed experiment JSON results from `../experiments/` (M1–M8). No Qiskit dependency. |
| `circuit_view.py` | Renders the Shor circuit as **code-generated SVG** (pure Qiskit-core, no static image). |
| `bloch_view.py` | Interactive 3D **Bloch sphere** (Plotly): noise on a single qubit + the entanglement/Bell demo. |
| `qpu_view.py` | 3D **QPU** stage animation (signal in → qubits rotate → result out). |
| `steane_backend.py` | Live **Steane `[[7,1,3]]`** error-injection backend (inject a Pauli error, read syndrome + correction). |
| `steane_view.py` | SVG rendering of the Steane code (7 data qubits + 6 syndrome checks). |
| `Dockerfile` | Image build (context = repo root); copies the demo + `shor_core.py`/`beauregard.py` + the M5–M8 JSONs. |
| `docker-compose.yml` | Compose service (context `../..`). |
| `requirements.txt` | Pinned dependencies. |
| `.streamlit/config.toml` | Dark UI theme (does **not** change the scientific chart colours). |

---

## Technical notes

- **Why Qiskit runs in a subprocess.** Qiskit Aer segfaults when built and executed inside
  Streamlit's internal `ScriptRunner` thread. `quantum_backend.py` / `steane_backend.py`
  therefore run every Qiskit call in a **dedicated subprocess** (`*_isolated` functions),
  which sidesteps the crash. Keep this pattern if you move the simulation logic.
- **Data provenance.** The theory tabs are not re-simulated live: they read the JSON files
  produced by the official experiment campaigns in `../experiments/` (M1–M8, each with its
  seed / shots / parameters), and a few tabulated numbers taken verbatim from the thesis
  `.tex` sources. This keeps the demo fast and consistent with the printed thesis.
- **Coupling to `Extra/experiments/`.** The demo intentionally lives under `Extra/` next to
  the experiments because it imports `shor_core.py` and reads the sibling `../experiments/`
  JSONs; the Dockerfile copies exactly those pieces. Moving the folder would require updating
  those relative paths and the Dockerfile.
- **Adding new results (M9, refinements).** The loaders in `data.py` use glob patterns, so a
  new run with a different timestamp is picked up automatically. If a JSON *schema* changes
  (new keys), update the matching loader in `data.py`.
