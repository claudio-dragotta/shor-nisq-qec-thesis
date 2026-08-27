# Guida v2 agli esperimenti parametrici

La guida precedente conteneva valori attesi e righe LaTeX derivate dal circuito N=15
errato. È stata sostituita: nessun numero storico va precompilato o copiato nella tesi.

## Prerequisiti

- eseguire da WSL2 distro `Ubuntu` 24.04;
- usare `/home/claudio/quantum-env/bin/python`;
- installare le versioni in `Extra/experiments/requirements.txt`;
- completare prima i test scientifici e congelare il manifest del circuito;
- scrivere in una nuova directory sotto `artifacts/`, senza sovrascrivere i JSON storici.

Esempio:

```bash
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v2_20260819

$PY run_parameter_analysis.py --sweep all \
  --k-reps 30 --shots 1024 --max-iter 50 \
  --output-dir "$RUN/results"
```

Per un singolo sweep:

```bash
$PY run_parameter_analysis.py --sweep k       --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep eps     --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep shots   --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep joint   --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep t1t2    --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep eps1q   --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep pro     --output-dir "$RUN/results"
$PY run_parameter_analysis.py --sweep optlevel --output-dir "$RUN/results"
```

Sono quindi **otto** sweep, non sette.

## Disegno

| Sweep | Valori |
|---|---|
| `k` | TOP-K = 1, 2, 3, 4, 6, 8 |
| `eps` | λ₂q = 0,001; 0,005; 0,01; 0,02; 0,05; 0,10 |
| `shots` | 128, 256, 512, 1024, 2048 |
| `joint` | griglia TOP-K × λ₂q |
| `t1t2` | T1 = 20, 50, 100, 200, 500 µs con T2/T1 = 0,8 |
| `eps1q` | λ₁q da 1e-4 a 2e-2 |
| `pro` | readout simmetrico da 0% a 20% |
| `optlevel` | livelli di compilazione 0, 1, 2, 3 |

`eps_1q` e `eps_2q` sono i parametri λ del canale depolarizzante Aer,
`E(ρ)=(1-λ)ρ+λI/d`; non sono direttamente la probabilità di un Pauli non-identità.
Lo sweep ε₂q riporta per questo la proxy

```text
P(no Pauli 2Q non-identità) = (1 - 15 λ₂q / 16) ^ n_CX
```

La proxy non include rilassamento o readout e non va chiamata probabilità di successo del
circuito.

## Regole statistiche

- la baseline M1 viene ricalcolata sul contratto corrente all'avvio, non è hardcoded;
- i fallimenti sono rappresentati con `max_iter+1`; un successo a `max_iter` resta valido;
- le statistiche descrittive `M_bar` riguardano i successi, mentre i test sui tempi includono
  il sentinel dei run censurati;
- ogni punto usa gli stessi seed di replica; i confronti tra strategie usano quindi il test
  di Wilcoxon appaiato unilaterale, non Mann–Whitney per campioni indipendenti;
- non interpretare `p<0,05` da decine di test come conferma isolata senza discutere la
  molteplicità e le dimensioni dell'effetto.

## Output e LaTeX

Il JSON v2 contiene:

```text
schema_version, timestamp, config, manifest, baseline_m1, sweeps
```

Usare `extract_latex.py` indicando esplicitamente il percorso del JSON v2. Lo script rifiuta
per default gli schemi storici. Le tabelle della tesi vanno aggiornate soltanto dopo aver
verificato hash circuito, versioni, numero di repliche e completezza di tutti gli sweep.

Non esistono più “conclusioni attese” precompilate: il punto della nuova campagna è misurare
gli effetti del circuito corretto e dichiarare anche risultati nulli o contrari alle ipotesi.
