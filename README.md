# Shor's Algorithm on NISQ Hardware & Quantum Error Correction

**Master's thesis — full documentation of the study conducted.**
**Author:** Claudio Dragotta · **Advisor:** Ing. Floriano Caprio · Università Campus Bio-Medico di Roma

This repository documents the entire study behind the thesis: LaTeX sources, the
experimental code and results (Qiskit / Stim / PyMatching / scikit-learn), the reproducible
noise-model campaigns, and an interactive demo. It is meant to be **consultable** — every
experimental number reported in the thesis can be traced back to a script and a JSON result
here, including the numbers that turned out to be wrong and were corrected.

The work answers one question in two phases:

> **On noisy (NISQ) hardware, how do you recover Shor's result — and how much error
> correction does Shor actually need?**

1. **Phase 1 — testing an ML hypothesis (bridge).** Does a machine-learning classifier
   applied to the noisy output reduce the number of Shor iterations? An **ablation analysis**
   shows the gain comes from the multi-candidate **TOP-4** search, *not* from the classifier.
   A negative result which motivates Phase 2.
2. **Phase 2 — quantum error correction (core).** Build and simulate correction codes
   (repetition → Steane `[[7,1,3]]` → surface code), measure the **logical error rate**
   `p_L`, and inject it into a **logical Shor** to quantify the correction Shor requires.
   Machine learning returns here, applied to the *syndrome* rather than the output.

---

## Key results

| Result | Value |
|---|---|
| Shor physical success rate, *N*=15, NISQ-realistic | crashes to **~3.4%** (analytic estimate) |
| Baseline iterations M̄₁ (Method 1, TOP-1) | **1.97** (UC1), 1.60 (UC2) |
| TOP-4 multi-candidate search | **M̄ = 1.00**, σ = 0 (ρ = 1.97 on UC1, *p* < 0.001) |
| ML classifier contribution (ablation) | **statistically irrelevant** on UC1 (*p* = 0.849), harmful on UC2 |
| Zero-Noise Extrapolation | **ineffective**: no significant gain, 2–3× the shot cost |
| Repetition code | logical error `p_L = 3p² − 2p³` (verified) |
| Steane `[[7,1,3]]` | **quadratic** suppression (slope 1.94), pseudo-threshold ≈ 0.08 |
| Surface code (Stim + PyMatching, *d* = 3,5,7,9) | threshold **≈ 0.86%** (Z), **0.81%** (X) |
| Surface code scaling law | `p_L = A(p/p_th)^((d+1)/2)`, A ≈ 0.035, RMS residual 0.08 in ln `p_L` |
| Resource estimate, logical Shor on *N*=15 | **~1 900 physical qubits** at *p* = 2×10⁻³; ~590 at *p* = 10⁻³ |
| Logical Shor `P_success` | physical ≈ 0.64 → Steane ≈ 0.72 → surface *d*=7 ≈ 0.74 (ideal ≈ 0.75) |
| Learned decoding (hybrid, *d* = 3) | **−21%** logical error under crosstalk (McNemar *p* < 10⁻³²⁰) |
| Learned decoding (hybrid, *d* = 7) | **no gain**: the network never flips a decision |

**Take-away:** an ML filter on the noisy output is unnecessary — indeed the classification
problem it addresses does not exist. Structural error correction is necessary, and its cost
is quantifiable end-to-end. Machine learning has a real but **narrow** niche: complementing
(never replacing) an analytic decoder, and only where that decoder is *structurally* unable
to represent the error class.

---

## The experiments: what we ran, and why

Every experiment below was run to answer a specific question, and several were run
**because a previous result was suspicious**. This section explains the reasoning, not just
the outcome. All results live in `Extra/experiments/`, one folder per block, each with its
own README and JSON outputs recording seed, shot count and parameters.

### Phase 1 — is the ML classifier doing anything? (M1–M4)

| Experiment | Question it answers | Outcome |
|---|---|---|
| **Baseline M1** | how many iterations does TOP-1 need? | M̄₁ = 1.97 (UC1), 1.60 (UC2), 100% success |
| **M_TOP4** | how much of the gain is the multi-candidate search alone? | M̄ = 1.00 with σ = 0 — *every* repetition converges first try |
| **M2** | does adding the ML classifier help? | UC1: no (*p* = 0.849). UC2: **harmful**, M̄ rises to 1.57 |
| **Parametric campaign** | is TOP-4 robust, or tuned to one noise level? | 6 of 7 parameters have no effect; only *K* matters, with threshold *K* = 2 |
| **ZNE comparison** | does a standard mitigation technique do better? | No significant gain, 2–3× the shots |

**Why the ablation mattered.** Method 2 combines two components — an ML gate and a TOP-4
search. Comparing it only against the TOP-1 baseline would have credited the classifier with
a gain produced by the search. The three-way comparison is what isolates the contribution,
and it is what turned a presumed positive result into a documented negative one.

### Why TOP-4 works: two follow-up measurements

The parametric campaign produced a result too strong to accept without explanation: TOP-4
kept converging on the first attempt even at ε₂q = 10⁻¹, where the probability that no
two-qubit gate fails is 2.5×10⁻⁸. Two experiments were added to explain it.

- **Mode distribution** (`analisi_moda_uc1.py`). Over 60 runs the histogram mode always
  falls on one of the four expected QPE peaks {0, 64, 128, 192}, and equals the sterile
  outcome *y* = 0 in 41.7% of cases. The mode leads to the factors 58.3% of the time
  (⇒ M̄₁ ≈ 1.7, measured 1.97); TOP-4 finds them in **60/60**. This explains σ = 0.
- **Effective coherent fraction** (`frazione_coerente_efficace.py`). Modelling the observed
  histogram as a mixture of the ideal distribution and the uniform one gives the surviving
  coherent fraction *f*. Result: **`P_surv` underestimates it by up to 23 orders of
  magnitude**, and the effective exponent is 14–20 rather than the 166 two-qubit gates in
  the circuit — **only about one gate in nine is critical** for phase readability.
  `(1−ε)^k` counts *errors*, not *damage*.

### The label audit: what the classifier actually learned

The coexistence of excellent classification metrics (F1 = 0.95, AUC = 0.96) with zero
operational gain was anomalous enough to warrant a direct check
(`audit_etichette_classificatore.py`). Because the trained models were archived together
with their test sets, the labels could be **recomputed** from the stored histograms.

- The labels match a **TOP-1** rule (99.8% agreement), not the **TOP-16** rule documented in
  the code (74.2% — which is merely the base rate of the positive class).
- Since the only sterile QPE peak is *y* = 0, the classifier was in effect trained to answer
  *"is the histogram's argmax cell 0?"*. All 103 negatives (UC1) and all 67 (UC2) have mode
  *y* = 0.
- Those "negative" histograms retain **75.8% of their mass on the four QPE peaks**, entropy
  3.66 bits out of 8 — the signal is entirely present. In 14 of 103 cases the two highest
  peaks are **exactly tied**, and the label was decided by a tie-break inside `max()`; in 29
  cases they differ by at most one count.
- **The TOP-16 rule cannot produce negatives at all.** 63 of the 256 outcomes lead to the
  correct factors (continued fractions with `limit_denominator(15)` map a whole band of
  phases onto *r* = 4), so for a signal-free histogram the chance that none of the top 16 is
  useful is `C(193,16)/C(256,16)` = **0.9%**. Regenerating the dataset with the documented
  rule yields **2000/2000 positives for both use cases**.

This is what turns the negative result from a finding into an explanation: the classifier's
metrics measured its ability to locate the maximum of 256 numbers, and TOP-4 covers exactly
that case by construction.

### Phase 2 — error correction (M5–M8)

| Block | Question | Outcome |
|---|---|---|
| **M5** repetition | does the syndrome extract information without collapsing the state? | `p_L = 3p² − 2p³`, exact match |
| **M6** Steane `[[7,1,3]]` | does a real CSS code suppress errors quadratically? | slope 1.94, pseudo-threshold ≈ 0.08 |
| **M7** surface code | is there a threshold, and where? | crossing at `p_th` ≈ 0.86% (Z), 0.81% (X) |
| **M8** logical Shor | what `p_L` does Shor need? | `p_L` ≈ 10⁻⁴ restores `P_success` to the instance maximum |

**Why d = 9 was added.** With three distances one can *observe* that redundancy suppresses
errors; with four one can *estimate the law*. Fitting `p_L = A(p/p_th)^((d+1)/2)` to the
sub-threshold points gives A ≈ 0.035 and `p_th` = 0.86%, with an RMS residual of 0.08 in
ln `p_L` across five orders of magnitude — and the threshold from the fit agrees with the one
read off the crossing, which is a non-trivial cross-check (the first uses sub-threshold
behaviour, the second the boundary). The suppression factors per distance step are 3.8×,
5.0×, 5.1×: the last two agreeing means the **asymptotic regime is reached**, which three
distances could not have established. Inverting the law yields the resource table in the
thesis — the concrete cost of correction, in physical qubits.

### Phase 2b — learned decoding (M10) and its limits

| Experiment | Question | Outcome |
|---|---|---|
| **E1** substitution | can a network replace MWPM? | **No** — 0 wins in 14 configurations |
| **E1b** data scaling | how much data would it take? | 10⁵–10⁶ samples merely to *tie* at *d* = 3 |
| **E2** crosstalk | and if the noise leaves the decoder's model? | network wins at *d* = 3 (1.14–1.19×) |
| **E3** validator | can it predict *when* MWPM is wrong? | AUC = 0.941 |
| **E4** hybrid decoder | complement instead of replace? | **−18/−21%** at *d* = 3, −1/−3% at *d* = 5, **0% at *d* = 7** |
| **E5** transferability | does it survive a different noise profile? | 12/12 transferred networks still beat MWPM |
| **E6** mis-calibration | does a *wrong* noise model open a margin? | **No** — 0/12; MWPM costs only 1–3% when mis-calibrated |
| **E7** better analytic decoder | does BP+OSD already capture the crosstalk margin? | **At *d* = 5 it does, and far better than the network** |

**Why E6 and E7 were added, and what they cost the thesis.** Both were run as adversarial
checks on the M10 result, and both qualified it.

- **E6** tested whether the network's advantage came from MWPM being fed an *exact* noise
  model — a luxury real hardware never offers. It does not: mis-calibrating the measurement
  error by a factor 5 low or 10 high changes `p_L` by 1–3%, and the network never wins.
  This **corrected the thesis's own criterion**: it is not enough for the analytic model to
  be *imprecise*; it must be *structurally unable* to represent the error class. A model with
  wrong parameters still describes the same error classes, and the geometry of the problem —
  which detection events are plausibly connected — does not change.
- **E7** compared against BP+OSD, a strictly more expressive analytic decoder. At *d* = 3 the
  network's advantage survives (BP+OSD actually *degrades* under crosstalk, because it trusts
  an incomplete model more thoroughly than MWPM does). At *d* = 5 it does not: BP+OSD gains
  17–27% where the learned hybrid gains 1–3%. **Choosing a better analytic decoder is worth
  five times more than training a network.**

The honest conclusion is that learned decoding has a real but **narrow** niche, and that the
first check before introducing a learned model is whether the best available analytic method
has already been chosen.

### Phase 2c — the third position: compilation (M11–M14)

| Block | Question | Outcome |
|---|---|---|
| **M11** layout | can ML pick a better qubit mapping than the transpiler? | margin exists (43.5 pp spread) but the fidelity criterion already captures all but **1.9 pp** |
| **M12** coherent errors | is the Stim/Pauli model hiding something? | coherent errors cost ≈ 12%; syndrome extraction partially twirls them |
| **M14** generalisation | does the decoder transfer across noise profiles? | 12/12, at +1.6% cost |

---

## Parameter changes, and why

Several parameters were changed mid-study. Each change is documented here because each was
forced by a defect found in the original choice — and in every case the *old* results were
superseded, not merely refined.

| Change | From → To | Why |
|---|---|---|
| **Iteration seeding** | `seed*10⁴ + iter` → `seed*10⁶ + iter*10⁴` | Aer derives each shot's RNG as `seed_simulator + shot_index`. With 1024 shots, consecutive iterations shared **1023 samples out of 1024** — they were not independent runs. M̄₁ fell from 6.43 to 1.97 and every strategy reached 100% success once fixed. |
| **`P_surv` exponent** | `#cx` → `#cx + #cp + #swap` | The noise model applies the two-qubit depolarising error to `['cx','swap','cp']`, and the inverse QFT's `cp` gates survive transpilation. For *N* = 15 that is 166 gates, not 114 — and for Beauregard circuits the `cp` gates *outnumber* the `cx` by more than three to one. |
| **Surface-code sampling** | fixed 200k shots → adaptive (~200 logical events) | At *d* = 9 and *p* = 2×10⁻³ the logical rate is ~10⁻⁵: 200k shots give **two events** (70% uncertainty). Adaptive sizing brings the same point to 3.5%, which is what makes the scaling-law fit possible at all. |
| **Sampling strategy** | single call → 500k-shot blocks | 40M shots × 720 detectors allocates 26.8 GiB in one array. Failure counts are additive, so blocks are equivalent. |
| **Mis-calibration design** | uniform rescaling → measurement error only | Uniform rescaling produced **no effect** (cost 1.000, 1.004, 1.000). MWPM minimises total matching weight and an edge weight is ≈ −log *p*: scaling every probability shifts all weights by a constant, leaving the minimum-weight matching unchanged. Only an *unbalanced* perturbation — the ratio of time-like to space-like edges — makes the matching err. |
| **Cost measurement** | 4 trajectories → increasing shot scale | Aer parallelises trajectories across cores, so per-shot cost falls with shot count (32.6 → 2.9 ms/shot on UC1 between 4 and 1024 shots). Estimates from 4 trajectories **overstate the cost by ~11×**; earlier reported figures for UC3/UC4 were withdrawn. |
| **BP+OSD shot count** | 800k → 200k | Both decoders under comparison are analytic, so no train/validation split is needed and all shots are usable as test. The comparison is also *paired* (same shots to both decoders), evaluated with McNemar, which is far more sensitive than comparing independent error rates. |

### Two use-case caveats worth knowing

- **UC4 (*N* = 35, *a* = 6) is a degenerate instance.** Since 6² ≡ 1 (mod 35), the period is
  *r* = 2 and eleven of the twelve controlled-U gates are the identity and get removed. Its
  circuit is *shorter* than UC1's despite the larger modulus. The choice was deliberate (Ch. 2
  states it: isolating register width from exponentiation depth), but it means UC4 does **not**
  belong on the "larger *N* ⇒ harder" axis that Secondary Hypothesis 2 assumes. Along
  *N* = 15 → 21 → 35 the periods are 4 → 6 → 2 and the depths 311 → 9 883 → 1 480.
- **UC3 (*N* = 21) is barred by a double barrier**, not by the decomposition alone.
  Beauregard cuts `cx` from 10 040 to 3 406 but introduces 11 436 `cp`, so the total number of
  noisy two-qubit gates *grows* to 14 842. On top of that, simulation costs 16.8 s per
  trajectory — 4.8 hours for a single 1024-shot iteration.

---

## Repository structure

```
.
├── file_latex/          THESIS SOURCES (Overleaf-ready — this is what compiles the thesis)
│   ├── main.tex             master file: preamble, chapter order, bibliography
│   ├── TITLE.tex            title page
│   ├── Bibliografia.bib     bibliography (biblatex + biber)
│   ├── capitoli/            15 chapters + 7 appendices (.tex)
│   └── figure/              figures embedded in the thesis
├── figure_src/          Python scripts that GENERATE file_latex/figure/
├── Extra/
│   ├── demo/               → interactive demo moved to its own repo + live site (see below)
│   └── experiments/        experimental code + JSON results, one folder per block
├── tesi_compilata.pdf   compiled thesis (output snapshot)
├── piano_azione_qec.md  QEC action plan (milestones M0–M9)
├── INDICE_PROGETTO.md   detailed project index (Italian)
├── CLAUDE.md            project context/instructions
└── AVVIO_WSL.md         WSL + Qiskit environment setup guide
```

| Block | Folder | What it produces |
|---|---|---|
| M1–M4 | `campagne_classiche_M1-M4/` | Shor core (`shor_core.py`) + Beauregard, Method 1 / Method 2, TOP-4, parametric campaign, ZNE, ML classifiers, label audit |
| M5 | `M5_repetition_code/` | repetition code `p` vs `p_L` curves (bit-flip / phase-flip) |
| M6 | `M6_steane_code/` | Steane `[[7,1,3]]` syndrome verification + logical error curve |
| M7 | `M7_surface_code/` | surface code with Stim + PyMatching, *d* = 3,5,7,9 + scaling law |
| M8 | `M8_shor_logico/` | logical Shor: `p_L` → `P_success` |
| M10 | `M10_neural_decoder/` | learned decoding: substitution, hybrid, validator, transfer, mis-calibration, BP+OSD |
| M11 | `M11_layout/` | layout selection on a real calibration snapshot (FakeSherbrooke) |
| M12 | `extra_rumore_coerente/` | coherent (non-Pauli) errors on the surface code |

---

## Reproducing the study

**Environment.** Reference setup is **WSL2 + Ubuntu 22.04 + Python 3.12**, Qiskit 2.x,
Qiskit Aer (see [`AVVIO_WSL.md`](AVVIO_WSL.md)). Surface-code work uses Stim + PyMatching;
the BP+OSD comparison additionally requires `ldpc`.

```bash
# experiments (example)
cd Extra/experiments/M7_surface_code
python qec_surface.py --basis z --adattivo --distances 3 5 7 9
python legge_di_scala.py                   # fits p_L(d,p) and prints the resource table

# figures (from the repo root, quantum-env active)
python figure_src/gen_qec_surface.py       # writes into file_latex/figure/
python figure_src/gen_audit_classificatore.py

# build the thesis
cd file_latex
latexmk -pdf main.tex                      # pdflatex → biber → pdflatex ×2
```

Every JSON result records its **seed, shot count and parameters**, so each run is reproducible
and each number in the thesis is traceable to a script.

---

## Interactive demo

A **live** interactive demo of Shor's algorithm — the circuit and a Bloch sphere per qubit,
stage by stage, with statistical execution over many iterations — runs at
**<https://shor-demo-6knp.onrender.com>**. Its source code lives in a dedicated repository:
**<https://github.com/claudio-dragotta/shor-demo>** (FastAPI + Qiskit, deployed on Render).

---

## Thesis structure

**15 body chapters** (theory in Ch. 3–6, experiments in Ch. 7–13, closing in Ch. 14–15) +
**7 appendices (A–G)**.

| # | Chapter | | # | Chapter / Appendix |
|---|---|---|---|---|
| 1 | Introduzione | | 10 | Verifica dell'Ipotesi: ML → TOP-K *(bridge)* |
| 2 | Obiettivi e Piano Sperimentale | | 11 | Correzione d'Errore (repetition → Steane) |
| 3 | Fondamenti del Calcolo Quantistico | | 12 | Il Surface Code e la Stima dell'Errore Logico |
| 4 | L'Algoritmo di Shor | | 13 | Integrazione: lo Shor Logico |
| 5 | Rumore Quantistico nei Sistemi NISQ | | 14 | Sviluppi Futuri |
| 6 | Strategie per la Riduzione del Rumore | | 15 | Conclusioni |
| 7 | Strumenti e Ambiente di Simulazione | | A–G | Appendices |
| 8 | Metodologia e Architettura | | | |
| 9 | Sviluppo e Implementazione | | | |

### Structure note (July 2026 restructuring)
To keep the **body** near the target length, introductory/background material was condensed:
a **short summary stays in the body** and the **full treatment moves to a dedicated
appendix**, precisely cross-referenced. Moved to appendices: *Fondamenti* (→ App. B),
*Strumenti* (→ App. C), the introduction background (→ App. D), the objectives detail
(→ App. E) and the ML-classifier detail (→ App. F). The core chapters — Shor, Noise, and all
experimental chapters — were kept intact.

---

## Scope of this public repository

This repository contains the study's **own** material (thesis sources, code, results, demo).
It intentionally **excludes** third-party and private items that were part of the private
working tree: downloaded third-party papers, other students' theses, meeting recordings,
presentation slides and private working notes. Their absence does not affect the
reproducibility of any result: all scripts, seeds and JSON outputs needed to regenerate the
thesis figures and numbers are here.

---

## Keeping the public mirror in sync

This public repository is a **scrubbed mirror** of a private working repository. Keeping it
up to date is automated: a git `post-commit` hook re-creates the scrubbed mirror (via
[`git filter-repo`](https://github.com/newren/git-filter-repo), stripping the excluded
material from the *entire* history) and force-pushes it whenever a commit touches files that
belong here.

- **Enable** (once, after cloning the private repo): `sh scripts/setup-hooks.sh`
- **Toggle**: `git config tesi.autopublish true|false`
- The hook [`.githooks/post-commit`](.githooks/post-commit) **skips** commits that only touch
  excluded/private files; the publish logic and the exclusion list live in
  [`scripts/publish-public.sh`](scripts/publish-public.sh).
- Requires `git-filter-repo` (`pip install git-filter-repo`).

---

## Academic use

This is academic work submitted as a master's thesis. If you reference the methods or results,
please cite the thesis. © Claudio Dragotta — all rights reserved unless otherwise noted.
