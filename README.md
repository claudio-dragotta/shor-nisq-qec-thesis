# Shor's Algorithm on NISQ Hardware & Quantum Error Correction

**Master's thesis — full documentation of the study conducted.**
**Author:** Claudio Dragotta · **Advisor:** Ing. Floriano Caprio · Università Campus Bio-Medico di Roma

This repository documents the entire study behind the thesis: LaTeX sources, the
experimental code and results (Qiskit / Stim / PyMatching), the reproducible noise-model
campaigns, and an interactive demo. It is meant to be **consultable** — every experimental
number reported in the thesis can be traced back to a script and a JSON result here.

The work answers one question in two phases:

> **On noisy (NISQ) hardware, how do you recover Shor's result — and how much error
> correction does Shor actually need?**

1. **Phase 1 — testing an ML hypothesis (bridge).** Does a machine-learning classifier
   applied to the noisy output reduce the number of Shor iterations? An **ablation analysis**
   shows the gain comes from the multi-candidate **TOP-4** search, *not* from the classifier.
   A negative result — the ML filter downstream of the output adds nothing — which motivates
   Phase 2.
2. **Phase 2 — quantum error correction (core).** Build and simulate correction codes
   (repetition → Steane `[[7,1,3]]` → surface code), measure the **logical error rate**
   `p_L`, and inject it into a **logical Shor** to quantify the correction Shor requires.

---

## Key results

| Result | Value |
|---|---|
| Shor physical success rate, *N*=15, NISQ-realistic | crashes to **~3.4%** |
| Baseline iterations M̄₁ (Method 1, TOP-1) | **6.43** (UC1), 2.42 (UC2) |
| TOP-4 multi-candidate search | **M̄ = 1.00** (ρ = 6.44 on UC1, *p* = 0.0002) |
| ML classifier contribution (ablation) | **statistically irrelevant** on UC1 (*p* = 0.849), harmful on UC2 |
| Repetition code | logical error `p_L = 3p² − 2p³` (verified) |
| Steane `[[7,1,3]]` | **quadratic** suppression, pseudo-threshold ≈ 0.08 |
| Surface code (Stim + PyMatching, *d* = 3,5,7) | threshold **≈ 0.7–0.9%** |
| Logical Shor `P_success` | physical ≈ 0.64 → Steane ≈ 0.72 → surface *d*=7 ≈ 0.74 (ideal ≈ 0.75) |

**Take-away:** an ML filter on the noisy output is unnecessary; structural error correction
is, and its benefit is quantifiable end-to-end.

---

## Repository structure

```
.
├── file_latex/          THESIS SOURCES (Overleaf-ready — this is what compiles the thesis)
│   ├── main.tex             master file: preamble, chapter order, bibliography
│   ├── TITLE.tex            title page
│   ├── Bibliografia.bib     bibliography (biblatex + biber)
│   ├── capitoli/            14 chapters + 6 appendices (.tex)
│   └── figure/              figures embedded in the thesis
├── figure_src/          Python scripts that GENERATE file_latex/figure/
├── Extra/
│   ├── demo/               interactive Streamlit demo (see Extra/demo/README.md)
│   └── experiments/        experimental code + JSON results, one folder per block M1–M8
├── tesi_compilata.pdf   compiled thesis (output snapshot)
├── piano_azione_qec.md  QEC action plan (milestones M0–M9)
├── INDICE_PROGETTO.md   detailed project index (Italian)
├── CLAUDE.md            project context/instructions
├── AVVIO_WSL.md         WSL + Qiskit environment setup guide
└── Proposta_nuovo_ML.md proposal for a new topology-aware decoding algorithm (see below)
```

---

## The experimental campaigns (M1–M8)

All experiments live in `Extra/experiments/`, one folder per block, each with its **own
README** explaining what it does, what to expect, and how to read the JSON results. Overview
in [`Extra/experiments/README.md`](Extra/experiments/README.md).

| Block | Folder | What it produces |
|---|---|---|
| M1–M4 | `campagne_classiche_M1-M4/` | Shor core (`shor_core.py`) + Beauregard decomposition, Method 1 / Method 2, TOP-4, the parametric campaign, ZNE comparison, ML classifiers |
| M5 | `M5_repetition_code/` | repetition code `p` vs `p_L` curves (bit-flip / phase-flip) |
| M6 | `M6_steane_code/` | Steane `[[7,1,3]]` syndrome verification + logical error curve |
| M7 | `M7_surface_code/` | surface code with Stim + PyMatching (MWPM), distances *d* = 3,5,7 |
| M8 | `M8_shor_logico/` | logical Shor: `p_L` → `P_success` |

Every JSON result records its **seed, shot count and parameters**, so each run is reproducible
and each number in the thesis is traceable.

---

## Reproducing the study

**Environment.** Reference setup is **WSL2 + Ubuntu 22.04 + Python 3.11**, Qiskit `2.5.0`,
Qiskit Aer `0.17.2` (see [`AVVIO_WSL.md`](AVVIO_WSL.md)). Surface-code work additionally uses
Stim + PyMatching.

```bash
# experiments (example)
cd Extra/experiments/M6_steane_code
python qec_steane.py                 # regenerates the JSON results

# figures (from the repo root, quantum-env active)
python figure_src/gen_qec_repetition.py    # writes into file_latex/figure/

# build the thesis
cd file_latex
latexmk -pdf main.tex                # pdflatex → biber → pdflatex ×2

# interactive demo
cd Extra/demo
pip install -r requirements.txt
streamlit run app.py                 # opens http://localhost:8501
```

The demo can also be run via Docker or deployed on Render — see
[`Extra/demo/README.md`](Extra/demo/README.md).

---

## Thesis structure

**14 body chapters** (theory in Ch. 3–6, experiments in Ch. 7–14) + **6 appendices (A–F)**.

| # | Chapter | | # | Chapter / Appendix |
|---|---|---|---|---|
| 1 | Introduzione | | 9 | Sviluppo e Implementazione |
| 2 | Obiettivi e Piano Sperimentale | | 10 | Verifica dell'Ipotesi: ML → TOP-K *(bridge)* |
| 3 | Fondamenti del Calcolo Quantistico | | 11 | Correzione d'Errore (repetition → Steane) |
| 4 | L'Algoritmo di Shor | | 12 | Il Surface Code e la Stima dell'Errore Logico |
| 5 | Rumore Quantistico nei Sistemi NISQ | | 13 | Integrazione: lo Shor Logico |
| 6 | Strategie per la Riduzione del Rumore | | 14 | Sviluppi Futuri |
| 7 | Strumenti e Ambiente di Simulazione | | A–F | Appendices (parametric campaign, extended theory, ML classifier detail) |
| 8 | Metodologia e Architettura | | | |

### Structure note (July 2026 restructuring)
To keep the **body** near the target length, introductory/background material was condensed:
a **short summary stays in the body** and the **full treatment moves to a dedicated
appendix**, precisely cross-referenced. Moved to appendices: *Fondamenti* (→ App. B),
*Strumenti* (→ App. C), the introduction background (→ App. D), the objectives detail
(→ App. E) and the ML-classifier detail (→ App. F). The core chapters — Shor, Noise, and all
experimental chapters — were kept intact. Body reduced from ~143 to ~119 pages.

---

## New research proposal

[`Proposta_nuovo_ML.md`](Proposta_nuovo_ML.md) drafts a **topology-aware, training-free
decoding algorithm** for Shor: instead of the hardware-blind TOP-4 or the post-hoc ML
classifier, it uses the QPU's published calibration (coupling map, per-edge CX error, readout
error, T₁/T₂) to (A) place the count register on the highest-fidelity qubits before execution
and (B) rank candidates by an analytically-derived per-bit confidence — deciding in a **single
run**, with no separate training or calibration pass. Proposed as future work.

---

## Scope of this public repository

This repository contains the study's **own** material (thesis sources, code, results, demo).
It intentionally **excludes** third-party and private items that were part of the private
working tree: downloaded third-party papers, other students' theses, meeting recordings and
private working notes. Their absence does not affect the reproducibility of any result: all
scripts, seeds and JSON outputs needed to regenerate the thesis figures and numbers are here.

---

## Academic use

This is academic work submitted as a master's thesis. If you reference the methods or results,
please cite the thesis. © Claudio Dragotta — all rights reserved unless otherwise noted.
