# Shor's Algorithm on NISQ Hardware & Quantum Error Correction

**Master's thesis — Claudio Dragotta · Advisor: Ing. Floriano Caprio · Università Campus
Bio-Medico di Roma**

This repository contains the thesis sources, experimental code, versioned JSON artifacts,
figure generators and the interactive Shor demo. Scientific outputs are considered current
only when their circuit/model revision and provenance are recorded in the artifact.

## Scientific status — 27 August 2026

The historical Phase-1 circuit for `N=15, a=7` had the correct order but implemented the
wrong modular permutation. Its ideal peak positions were unchanged, so the bug was invisible
in the ideal QPE histogram; noisy results, trained classifiers and downstream studies that
used that circuit are not transferable to the corrected implementation.

The following boundary is therefore mandatory:

| Block | Current status |
|---|---|
| M1–M4, Phase 1 | **Current v2.** Regenerated under `artifacts/v2_20260819/` with the corrected circuit manifest, paired analyses and explicit provenance. |
| M5 repetition code | **Current.** Independent of the corrected Shor multiplier. |
| M6 Steane code | **Current.** Independent of the corrected Shor multiplier. |
| M7 surface code | **Current.** Independent of the corrected Shor multiplier. |
| M8 logical Shor and M13 logical TOP-K | **Current v2 as phenomenological proxies.** Regenerated with schema-2 artifacts; they are not a fault-tolerant Shor implementation. |
| M10 learned decoding, including M14 transfer tests | **Current.** Decoder results do not use the faulty modular multiplier. |
| M11/M11b layout studies | **Current v2 as exploratory/observational studies.** Regenerated on an offline FakeSherbrooke snapshot; they are not hardware benchmarks and do not support causal claims. |
| M12 coherent-noise study | Current within its documented surface-code scope. |

Only the schema-2 Phase-1, M8, M13, M11 and M11b artifacts under
`artifacts/v2_20260819/` are current; older outputs remain historical audit material.
The ideal `N=15` invariants remain valid: period `r=4`, peaks `{0,64,128,192}`, factors
`3×5`, ideal single-shot factor yield `3/4`, and uniform random floor `63/256`.

The Beauregard arithmetic used for `N=21/35` is validated separately by truth tables, clean
ancillas and end-to-end QPE tests. That validation is not a noisy campaign. Those
instances remain outside the interactive and noisy Phase-1 pipeline because of classical
simulation cost. As a reproducible compilation diagnostic, the complete
`N=21, a=2, n_count=8` circuit has 21,036 CX and depth 23,081 in the `rz/sx/x/cx` basis;
if an Aer no-nonidentity-event proxy is reported, its form is
`(1-15*lambda_2q/16)^21036`. It is never a Shor success probability or circuit fidelity.

## Current results unaffected by the erratum

### M5–M7: quantum error correction

| Experiment | Valid result |
|---|---|
| Repetition code | `p_L = 3p² − 2p³`, verified against simulation. |
| Steane `[[7,1,3]]` | Quadratic suppression, fitted slope `1.94`, pseudo-threshold about `0.08`. |
| Surface code, distances 3/5/7/9 | Threshold about `0.86%` for Z memory and `0.81%` for X memory. |
| Surface-code scaling | `p_L = A(p/p_th)^((d+1)/2)`, with `A ≈ 0.035` and RMS residual `0.08` in `ln p_L`. |

These results establish the physical-to-logical suppression laws. They do not by themselves
provide a gate-by-gate equivalent noise channel for Shor.

### M10: learned decoding and its limits

| Experiment | Valid result |
|---|---|
| Neural substitution for MWPM | No wins in the tested 14 configurations. |
| Data scaling at distance 3 | Approximately `10^5–10^6` samples are required merely to tie the analytic decoder. |
| Hybrid decoder under crosstalk | Logical-error reduction of about `18–21%` at distance 3, about `1–3%` at distance 5, and no gain at distance 7. |
| Error validator | AUC `0.941`. |
| Transfer tests | All 12 tested transfers retain the documented advantage. |
| Measurement-error miscalibration | No learned-model win in the 12 tested settings; the analytic decoder changes by only about `1–3%`. |
| BP+OSD comparison | At distance 5 the stronger analytic decoder captures more of the available margin than the learned hybrid. |

The supported conclusion is deliberately narrow: learning can complement an analytic
decoder when its error model is structurally incomplete; it does not automatically replace
the best available analytic method.

## M8 is a phenomenological proxy, not an M6/M7 equivalence

`Extra/experiments/M8_shor_logico/shor_logico.py` injects an independently sampled logical
Pauli channel after compiled Shor gates. Its parameter `p_L` is a **phenomenological
per-gate proxy** used for a sensitivity curve. It is not a full fault-tolerant Shor
construction, and it is not mathematically equivalent to the logical error rates measured by
M6 or M7, whose circuits, cycles, correlations and decoder semantics differ. Mapping M6/M7
points onto an M8 curve is contextual only and must be labelled as such.

The current M8/M13 conclusions use the regenerated schema-2 outputs and their embedded
circuit manifest. Historical curves that predate the corrected multiplier remain superseded.

## Canonical environment

The only canonical execution environment is WSL2 distro `Ubuntu` (Ubuntu 24.04), with:

```text
/home/claudio/quantum-env/bin/python
```

From PowerShell:

```powershell
wsl -d Ubuntu
```

Inside WSL, from the repository root:

```bash
PY=/home/claudio/quantum-env/bin/python
$PY --version
$PY -m pip install -r Extra/experiments/requirements.txt
```

See [`AVVIO_WSL.md`](AVVIO_WSL.md) for the complete ordered workflow.

## Reproducible v2 pipeline

### Phase 1: corrected `N=15` campaign

```bash
cd Extra/experiments/campagne_classiche_M1-M4
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY -m pytest -q test_shor_core_n15.py test_campaign_stats_v2.py \
  test_beauregard_campaign_correctness.py test_phase1_diagnostics_v2.py

$PY train_classifier.py --n-samples 2000 --shots 1024 --seed 42 \
  --label-top-k 1 16 --noise-factor 0.5 --output-dir "$RUN/training"

$PY rerun_baseline_corretto.py --k 30 --shots 1024 --max-iter 50 \
  --model-dir "$RUN/training/top1" --output-dir "$RUN/results"

$PY run_parameter_analysis.py --sweep all --k-reps 30 --shots 1024 \
  --max-iter 50 --output-dir "$RUN/results"

$PY run_zne_comparison.py --k-reps 30 --shots 1024 --max-iter 50 \
  --output-dir "$RUN/results"

$PY analisi_moda_uc1.py --seed 7 --shots 1024 --reps 60 \
  --output-dir "$RUN/diagnostics"

$PY frazione_coerente_efficace.py --seed 11 --shots 1024 --reps 20 \
  --output-dir "$RUN/diagnostics"
```

M1, TOP-K and M2 reuse the same histogram for each replica/iteration. Their inferential
comparison is paired Wilcoxon. UC1 and UC2 are uniform illustrative noise presets, not a
calibration of a named QPU.

The classifier-audit figures accept only explicit schema-2 inputs:

```bash
cd ../../..
$PY figure_src/gen_audit_classificatore.py \
  --mode-json Extra/experiments/campagne_classiche_M1-M4/$RUN/diagnostics/diagnostic_mode_zero_uc1_v2.json \
  --fraction-json Extra/experiments/campagne_classiche_M1-M4/$RUN/diagnostics/diagnostic_effective_signal_fraction_v2.json \
  --training-json Extra/experiments/campagne_classiche_M1-M4/$RUN/training/training_manifest.json \
  --output-dir Extra/experiments/campagne_classiche_M1-M4/$RUN/figures/audit
```

### M8/M13: canonical logical-sensitivity run

```bash
cd Extra/experiments/M8_shor_logico
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY shor_logico.py --N 15 --a 7 --n-count 8 --shots 4096 \
  --replicates 20 --seed 42 --output-dir "$RUN"

$PY topk_logico.py --K 4 --shots 1024 --replicates 200 --seed 42 \
  --equivalence-margin 0.10 --output-dir "$RUN"
```

### M11/M11b: canonical layout run

```bash
cd Extra/experiments/M11_layout
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY -m pytest -q test_m11_layout_v2.py

$PY pilota_layout.py --layouts 60 --shots 8192 --batches 8 \
  --holdout-fraction 0.5 --bootstrap 2000 --seed 42 --output-dir "$RUN"

$PY test_ruoli.py --sottografi 12 --shots 8192 --batches 8 \
  --holdout-fraction 0.5 --bootstrap 2000 --seed 42 --casuali 2 \
  --output-dir "$RUN"

$PY analisi_ruoli.py --input-json <explicit-results_M11b_ruoli_v2.json> \
  --output-dir "$RUN" --bootstrap 2000 --seed 42
```

The final command intentionally requires a selected input filename; no “latest file” lookup
is part of the workflow. M11 is exploratory and M11b is observational; neither supports a
causal ML claim.

## Repository map

```text
file_latex/          thesis sources and included figures
figure_src/          deterministic figure generators
Extra/experiments/   code and versioned artifacts, grouped by milestone
Extra/shor-demo/     interactive demo, maintained as a separate nested repository
_archivio/           superseded material retained as an audit trail
```

| Block | Directory |
|---|---|
| M1–M4 | `Extra/experiments/campagne_classiche_M1-M4/` |
| M5 | `Extra/experiments/M5_repetition_code/` |
| M6 | `Extra/experiments/M6_steane_code/` |
| M7 | `Extra/experiments/M7_surface_code/` |
| M8/M13 | `Extra/experiments/M8_shor_logico/` |
| M10/M14 | `Extra/experiments/M10_neural_decoder/` |
| M11/M11b | `Extra/experiments/M11_layout/` |
| M12 | `Extra/experiments/M12_coerenti/` and `Extra/experiments/extra_rumore_coerente/` |

## Interactive demo

The live teaching demo is available at
**<https://shor-demo-6knp.onrender.com>**. It deliberately exposes only the tractable
`N=15, a=7` instance and separates the ideal mathematical simulation from an illustrative
noise laboratory.

## Building the thesis

The LaTeX sources use `biblatex` with Biber:

```bash
cd file_latex
latexmk -pdf main.tex
```

Se MiKTeX non dispone del motore Perl richiesto da `latexmk`, la sequenza equivalente usata
per la build finale è `pdflatex → biber → pdflatex` fino a stabilizzazione dei riferimenti.
Il glossario è configurato in modalità `noidx` e non richiede `makeglossaries`.

The thesis sources contain the reviewed v2 values. Before changing any reported number,
check `schema_version`, the circuit hash, model revision, seeds and software versions in its
JSON artifact.

## Academic use

This repository contains the study's original thesis material. If you reuse the methods or
results, please cite the thesis. Historical files are retained for transparency, not as
current evidence.
