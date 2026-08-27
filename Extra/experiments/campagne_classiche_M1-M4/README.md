# Campagne classiche M1–M4 — contratto sperimentale v2

Questa directory contiene la pipeline riproducibile per Shor rumoroso su `N=15`, il
confronto TOP-1/TOP-K, l'ablazione del classificatore, gli sweep parametrici e il confronto
con l'estrapolazione a rumore zero.

> **Erratum del 19 agosto 2026.** Gli artefatti nella radice della directory (JSON, log e
> modelli `.joblib` datati prima della v2) sono conservati come storico ma non sono una fonte
> scientifica corrente. Il vecchio `c_amod15(7,1)` aveva ordine 4, ma implementava l'orbita
> `1→2→11→7→1` invece di `1→7→4→13→1`. I picchi ideali non rivelavano l'errore; i risultati
> rumorosi, i classifier e i gate count sono invece dipendenti dal circuito e vanno
> rigenerati.

## Contratto congelato

- istanza primaria: `N=15`, `a=7`, otto qubit di conteggio;
- base compilata: `rz/sx/x/cx`, `optimization_level=2`, seed transpiler `20260819`;
- `rz` virtuale; rumore 1Q su `sx/x`, rumore 2Q su `cx`;
- durata illustrativa: 50 ns per 1Q, 300 ns per CX;
- readout simmetrico nelle campagne storicamente comparabili;
- seed Aer: `rep*1_000_000 + iterazione*10_000`;
- pareggi nel ranking risolti con priorita' SHA-256 dipendente dallo stesso seed, mai con
  l'ordine interno del dizionario; la revisione e' salvata nel manifest;
- fallimento codificato con il sentinel `max_iter+1`, distinto dal successo all'ultima
  iterazione;
- ogni JSON/modello v2 contiene schema, revisione, hash circuito e versioni software.

Il modello è **uniforme e illustrativo**: UC1 è il preset uniforme di riferimento, UC2 il
preset uniforme degradato/stress. Non è una replica di una calibrazione QPU per-qubit.

Nel target Qiskit 2.5 il circuito v2 a livello 2 ha depth 412 e 224 CX (il manifest resta la
fonte autoritativa per ogni esecuzione).

## Classificatore: due domande distinte

Gli stessi istogrammi vengono etichettati in due modi:

- `TOP-1`: dataset destinato all'ablazione operativa M2;
- `TOP-16`: audit della regola documentata in precedenza; se produce una classe unica lo
  script registra l'esito e non inventa un classificatore.

La selezione RF/SVM/MLP usa split 60/20/20: selezione sul validation set, valutazione finale
una sola volta sul test set.

## Entry point v2

Usare, in quest'ordine:

```bash
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY -m pytest -q test_shor_core_n15.py test_beauregard_campaign_correctness.py
$PY train_classifier.py --n-samples 2000 --shots 1024 --seed 42 \
  --label-top-k 1 16 --noise-factor 0.5 --output-dir "$RUN/training"
$PY rerun_baseline_corretto.py --k 30 --shots 1024 --max-iter 50 \
  --model-dir "$RUN/training/top1" --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep all --k-reps 30 --shots 1024 \
  --max-iter 50 --output-dir "$RUN/results"
$PY run_zne_comparison.py --k-reps 30 --shots 1024 --max-iter 50 \
  --output-dir "$RUN/results"
```

Infine generare le figure indicando esplicitamente il solo JSON baseline v2:

```bash
$PY generate_figures.py --output-dir "$RUN/figures" \
  --model-dir "$RUN/training/top1" --baseline-json "$BASELINE_JSON"
```

`run_experiments.py` e il `main` storico di `run_top4_baseline.py` sono disabilitati per
impedire di mescolare N=15 e N=21 o modelli pre-v2. La baseline condivide ogni istogramma
simulato fra M1, TOP-4 e M2: il confronto e' realmente appaiato e non triplica Aer.

## Diagnostici di Fase 1

I diagnostici della moda e della frazione efficace non leggono risultati storici e non
eseguono codice all'import. Entrambi usano `compile_shor_circuit`, il tie-break
`rank_measurements` e salvano configurazione, schedule dei seed, manifest e misure in JSON
schema 2. I percorsi di output sono sempre espliciti:

```bash
$PY analisi_moda_uc1.py --seed 7 --shots 1024 --reps 60 \
  --output-dir "$RUN/diagnostics"
$PY frazione_coerente_efficace.py --seed 11 --shots 1024 --reps 20 \
  --output-dir "$RUN/diagnostics"
```

Nel secondo artefatto `(1-15*lambda_2q/16)^n_cx` è denominato esclusivamente
`p_no_nonidentity_2q_proxy`: rappresenta il proxy indipendente di nessun evento Pauli 2Q
non-identità, non la probabilità di successo, la fedeltà o il rendimento di Shor.

Le tre figure di audit si generano senza Aer e senza fallback a file `latest`, joblib storici
o numeri incorporati. Servono i due JSON precedenti e il manifest prodotto dal training v2:

```bash
$PY ../../../figure_src/gen_audit_classificatore.py \
  --mode-json "$RUN/diagnostics/diagnostic_mode_zero_uc1_v2.json" \
  --fraction-json "$RUN/diagnostics/diagnostic_effective_signal_fraction_v2.json" \
  --training-json "$RUN/training/training_manifest.json" \
  --output-dir "$RUN/figures/audit"
```

Il generatore rifiuta schema storici, manifest incompatibili e input mancanti. Lo script
`causa_bilanciamento_dataset.py` è invece uno stub storico intenzionalmente disabilitato: la
premessa sui vecchi gate count non è confrontabile con il circuito v2 e il bilanciamento delle
etichette è già registrato in `training_manifest.json` e negli audit delle classi uniche.

## File principali

| File | Ruolo |
|---|---|
| `shor_core.py` | circuito, compilazione deterministica, modello di rumore, manifest e post-processing |
| `beauregard.py` | aritmetica N=21/35 validata con truth table e QPE end-to-end |
| `train_classifier.py` | dataset condiviso TOP-1/TOP-16 e selezione train/validation/test |
| `analisi_moda_uc1.py` | diagnostico v2 della moda sterile `y=0`, con JSON e istogramma rappresentativo |
| `frazione_coerente_efficace.py` | massa sui picchi, estimatore di miscela e proxy no-evento-2Q |
| `causa_bilanciamento_dataset.py` | stub storico; rimanda al label audit del training v2 |
| `rerun_baseline_corretto.py` | baseline UC1/UC2 M1, TOP-4 e M2 |
| `run_parameter_analysis.py` | otto sweep: K, ε₂q, shot, K×ε₂q, T1/T2, ε₁q, readout e livello di ottimizzazione |
| `run_zne_comparison.py` | confronto M1/ZNE-2/ZNE-3/TOP-4; scaling digitale illustrativo, non gate folding hardware |
| `generate_figures.py` | figure generate da modelli e JSON v2 espliciti |
| `extract_latex.py` | estrazione delle tabelle da percorsi v2 forniti via CLI |
| `artifacts/v2_20260819/` | nuova campagna; gli artefatti precedenti restano immutati |

## Ambiente canonico

Ubuntu 24.04 su WSL2 (`wsl -d Ubuntu`), Python 3.12 e dipendenze esatte in
`Extra/experiments/requirements.txt`. La distro `Ubuntu-22.04` presente sulla stessa macchina
usa un ambiente diverso e non va impiegata per questa campagna.
