# Avvio WSL e pipeline sperimentale v2

Questa è la guida operativa corrente. I comandi storici e gli output collocati fuori dalle
directory v2 sono conservati solo per audit e non devono alimentare tabelle o figure nuove.

## 1. Ambiente canonico

Da PowerShell avviare esclusivamente la distro WSL denominata `Ubuntu`:

```powershell
wsl -d Ubuntu
```

La distro canonica è Ubuntu 24.04. Il Python canonico è sempre quello dell'ambiente già
versionato:

```bash
PY=/home/claudio/quantum-env/bin/python
$PY --version
lsb_release -ds
```

Non affidarsi al `python` risolto dal `PATH` e non creare un secondo virtual environment per
la stessa campagna. Dalla root del repository montato in WSL:

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum
$PY -m pip install -r Extra/experiments/requirements.txt
```

Prima di una campagna registrare almeno:

```bash
$PY -VV
$PY -m pip freeze
```

Ogni JSON accettabile deve inoltre contenere `schema_version: "2.0"`, hash/revisione del
circuito, modello di rumore, seed e versioni software.

## 2. Regole di provenienza

- Non sovrascrivere i JSON storici nelle directory dei singoli esperimenti.
- Scrivere i nuovi risultati in una directory `artifacts/v2_20260819/` del blocco pertinente.
- Non scegliere automaticamente il file più recente: passare sempre il percorso JSON
  esplicito agli script di analisi e alle figure.
- Non copiare numeri nella tesi prima di aver verificato schema, manifest e log.
- M1/TOP-K/M2 condividono gli stessi istogrammi e si confrontano con Wilcoxon appaiato.
- UC1 e UC2 sono preset uniformi illustrativi; non chiamarli calibrazioni hardware realistiche.
- L'aritmetica `N=21/35` è validata separatamente, ma non costituisce una campagna rumorosa.

## 3. Fase 1 — pipeline corretta N=15

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum/Extra/experiments/campagne_classiche_M1-M4
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819
mkdir -p "$RUN"/{training,results,diagnostics,figures,logs}
```

### 3.1 Guardrail scientifici

```bash
$PY -m pytest -q \
  test_shor_core_n15.py \
  test_campaign_stats_v2.py \
  test_beauregard_campaign_correctness.py \
  test_phase1_diagnostics_v2.py \
  test_extract_latex.py
```

I test ideali verificano l'orbita `1→7→4→13→1`, i quattro picchi QPE e il
post-processing. I test Beauregard verificano l'aritmetica N=21/35, non autorizzano run
rumorosi su quelle istanze.

### 3.2 Training e label audit

```bash
$PY train_classifier.py \
  --n-samples 2000 \
  --shots 1024 \
  --seed 42 \
  --label-top-k 1 16 \
  --noise-factor 0.5 \
  --output-dir "$RUN/training" \
  > "$RUN/logs/training_full.stdout.log" \
  2> "$RUN/logs/training_full.stderr.log"
```

Attendere il completamento e verificare `training_manifest.json` prima di avviare la
baseline. TOP-1 è la regola operativa dell'ablazione; TOP-16 è un audit separato. Se una
regola produce una classe unica, il risultato corretto è un label audit non addestrabile,
non un classificatore artificiosamente bilanciato.

Il training salva un checkpoint atomico ogni 200 campioni in `training/checkpoints` e lo
riprende automaticamente se il contratto (circuito, rumore, seed, shot e label) coincide.
Usare `--no-resume` soltanto quando si vuole rigenerare esplicitamente il dataset da zero.

### 3.3 Baseline appaiata

```bash
$PY rerun_baseline_corretto.py \
  --k 30 \
  --shots 1024 \
  --max-iter 50 \
  --model-dir "$RUN/training/top1" \
  --output-dir "$RUN/results" \
  > "$RUN/logs/baseline.stdout.log" \
  2> "$RUN/logs/baseline.stderr.log"
```

La baseline usa lo stesso istogramma di ciascuna coppia replica/iterazione per M1, TOP-4 e
M2. Un fallimento è salvato con il sentinel `max_iter+1`; non coincide con un successo
all'ultima iterazione.

### 3.4 Sweep parametrici

```bash
$PY run_parameter_analysis.py \
  --sweep all \
  --k-reps 30 \
  --shots 1024 \
  --max-iter 50 \
  --output-dir "$RUN/results" \
  > "$RUN/logs/parameter.stdout.log" \
  2> "$RUN/logs/parameter.stderr.log"
```

Per uno smoke usare una singola voce di `--sweep` e parametri minimi; non confondere uno
smoke con un risultato scientifico.

Con `--sweep all` ogni famiglia completata viene salvata atomicamente nel checkpoint v4
della directory risultati. Un rilancio con gli stessi manifest e parametri salta le famiglie
già concluse; `--no-resume` forza invece una nuova campagna.

### 3.5 Confronto ZNE

```bash
$PY run_zne_comparison.py \
  --k-reps 30 \
  --shots 1024 \
  --max-iter 50 \
  --output-dir "$RUN/results" \
  > "$RUN/logs/zne.stdout.log" \
  2> "$RUN/logs/zne.stderr.log"
```

Lo scaling digitale del rumore è illustrativo e non equivale a gate folding su hardware.
Il confronto salva una replica alla volta in `zne_checkpoint_v3.json` e riprende
automaticamente con lo stesso contratto; `--no-resume` forza un nuovo campionamento.

### 3.6 Diagnostici v2 espliciti

```bash
$PY analisi_moda_uc1.py \
  --seed 7 --shots 1024 --reps 60 \
  --output-dir "$RUN/diagnostics"

$PY frazione_coerente_efficace.py \
  --seed 11 --shots 1024 --reps 20 \
  --output-dir "$RUN/diagnostics"
```

Il secondo diagnostico salva `p_no_nonidentity_2q_proxy` usando
`(1-15*lambda_2q/16)^n_cx`. È soltanto un proxy indipendente di nessun evento Pauli 2Q
non-identità: non è probabilità di successo, fedeltà o frazione fisica di coerenza.

### 3.7 Figure ed estrazione LaTeX

Dalla root del repository:

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum
PHASE1=Extra/experiments/campagne_classiche_M1-M4/artifacts/v2_20260819

$PY figure_src/gen_audit_classificatore.py \
  --mode-json "$PHASE1/diagnostics/diagnostic_mode_zero_uc1_v2.json" \
  --fraction-json "$PHASE1/diagnostics/diagnostic_effective_signal_fraction_v2.json" \
  --training-json "$PHASE1/training/training_manifest.json" \
  --output-dir "$PHASE1/figures/audit"
```

Per le altre figure della Fase 1, selezionare il JSON baseline esplicito:

```bash
cd Extra/experiments/campagne_classiche_M1-M4
RUN=artifacts/v2_20260819
$PY generate_figures.py \
  --output-dir "$RUN/figures" \
  --model-dir "$RUN/training/top1" \
  --baseline-json <explicit-results_baseline_v2.json>
```

Gli snippet LaTeX richiedono anch'essi percorsi espliciti:

```bash
$PY extract_latex.py \
  --parameter-json <explicit-results_parameter_v2.json> \
  --baseline-json <explicit-results_baseline_v2.json> \
  --zne-json <explicit-results_zne_v2.json> \
  > <explicit-snippet.tex>
```

## 4. M8 e M13 — run canonico completato

Le curve archiviate prima della correzione del circuito sono solo audit. La nuova esecuzione
usa il circuito corretto e incorpora il manifest:

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum/Extra/experiments/M8_shor_logico
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY -m pytest -q test_m8_m13_v2.py

$PY shor_logico.py \
  --N 15 --a 7 --n-count 8 \
  --shots 4096 --replicates 20 --seed 42 \
  --output-dir "$RUN"

$PY topk_logico.py \
  --K 4 --shots 1024 --replicates 200 --seed 42 \
  --confidence 0.95 --equivalence-margin 0.10 \
  --output-dir "$RUN"
```

Il `p_L` di M8/M13 è un parametro fenomenologico per-gate del canale logico iniettato. Non è
equivalente al `p_L` per ciclo/circuito misurato in M6 o M7 e non rappresenta uno Shor
fault-tolerant completo.

## 5. M11 e M11b — run canonico completato

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum/Extra/experiments/M11_layout
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY -m pytest -q test_m11_layout_v2.py

$PY pilota_layout.py \
  --layouts 60 --shots 8192 --batches 8 \
  --holdout-fraction 0.5 --bootstrap 2000 --seed 42 \
  --output-dir "$RUN"

$PY test_ruoli.py \
  --sottografi 12 --shots 8192 --batches 8 \
  --holdout-fraction 0.5 --bootstrap 2000 --seed 42 --casuali 2 \
  --output-dir "$RUN"

$PY analisi_ruoli.py \
  --input-json <explicit-results_M11b_ruoli_v2.json> \
  --output-dir "$RUN" --bootstrap 2000 --seed 42
```

M11 usa train/holdout per valutare la selezione. M11b è un'analisi osservazionale
within-subgraph del readout effettivo dopo routing; le etichette dell'initial layout non sono
trattamenti e non autorizzano inferenze causali.

Gli artefatti canonici sono
`results_M11_pilota_v2_20260826_222137.json`,
`results_M11b_ruoli_v2_20260827_115109.json` e
`analysis_M11b_v2_20260827_115119.json`. Il checkpoint M11b permette la ripresa atomica e non
deve essere cancellato se si vuole verificare la riproducibilità senza ripetere le simulazioni.

## 6. Blocchi QEC già validi

M5, M6, M7 e il nucleo di M10 non dipendono dal moltiplicatore Shor corretto. I loro output
versionati restano le fonti correnti. Non rigenerarli solo per uniformare una data: una nuova
esecuzione richiede una motivazione scientifica e una nuova directory di artefatti.

## 7. Compilazione della tesi

```bash
cd /mnt/c/Users/ludov/Desktop/tesi_magistrale_quantum/file_latex
latexmk -pdf main.tex
```

Il backend bibliografico è Biber. Se `latexmk` non è disponibile, usare
`pdflatex → biber → pdflatex → pdflatex`.

## 8. Checklist prima di dichiarare concluso un run

- processo terminato con exit code zero;
- stderr controllato;
- JSON `schema_version: "2.0"` leggibile;
- manifest e hash coerenti fra training, baseline, sweep e figure;
- seed, shot, repliche e failure sentinel presenti;
- nessun risultato storico copiato nella nuova directory;
- output classificato come smoke, audit o risultato scientifico;
- percorso esatto dell'artefatto registrato nelle note di lavoro.
