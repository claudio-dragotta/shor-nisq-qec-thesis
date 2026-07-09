# Campagne classiche M1–M4 — Shor rumoroso, Metodo 1/2, TOP-4, parametrica, ZNE

Prima campagna sperimentale della tesi (milestone **M1–M4**): esecuzione di Shor su simulatore
rumoroso e verifica dell'ipotesi ML. **Esito**: l'ablazione dimostra che il guadagno è della
strategia **TOP-4**, non del classificatore ML (risultato negativo consapevole → capitolo ponte).

> **Perché una cartella unica.** Questi script sono **interdipendenti** (`shor_core` importa
> `beauregard`; le campagne importano `shor_core`). Sono tenuti insieme così gli import
> `from shor_core import ...` restano validi. Separarli per singola milestone romperebbe codice
> già funzionante e difficile da ri-testare. I nuovi blocchi QEC (M5, M6, …) sono invece
> autonomi e hanno una cartella ciascuno.

## Libreria condivisa (usata da tutti gli script)

| File | Cos'è |
|---|---|
| `shor_core.py` | **Cuore**: circuito di Shor (QPE), QFT⁻¹, noise model parametrizzato, Metodo 1 (TOP-1), Metodo 2 (classificatore + TOP-K), post-processing dei fattori |
| `beauregard.py` | Decomposizione efficiente della moltiplicazione modulare (O(n³) CX) per N=21/35, evita l'esplosione di `UnitaryGate` |

## Script per milestone

| File | Blocco | Cosa fa |
|---|---|---|
| `run_experiments.py` | M1/M2 | Orchestrazione delle campagne sui 4 use case (Metodo 1 e Metodo 2) |
| `run_top4_baseline.py` | ablazione | Baseline M_TOP4 (TOP-4 **senza** classificatore) — isola il contributo del ML |
| `train_classifier.py` | M2 | Addestramento e selezione del classificatore (RF/SVM/MLP) sugli istogrammi |
| `run_parameter_analysis.py` | M4 | 7 sweep parametrici (K, ε₂q, shots, K×ε₂q, T₁/T₂, ε₁q, p_ro) → Appendice A |
| `run_zne_comparison.py` | M4 | Confronto con Zero-Noise Extrapolation |
| `mwu_analysis.py` | trasversale | Test statistici non parametrici (Mann-Whitney a una coda) |
| `pilot_calibration.py` | pilota | Calibrazione preliminare dei parametri del noise model |
| `pilot_uc3_uc4.py` | pilota | Prova di scalabilità su UC3/UC4 (N=21, 35) |
| `test_beauregard_cx.py` | test | Verifica del conteggio di porte CX della decomposizione Beauregard |
| `generate_figures.py` | figure | Genera le figure della prima campagna (istogrammi QPE, ROC, iterazioni) dai JSON |
| `extract_latex.py` | utility | Estrae righe/tabelle LaTeX dai risultati |

## Dati e modelli

| File | Cos'è |
|---|---|
| `clf_UC1.joblib`, `clf_UC2.joblib` | Classificatori addestrati (Metodo 2) per UC1 e UC2 |
| `train_log.txt` | Log dell'addestramento |
| `results_parameter_analysis_*.json` | Output degli 7 sweep parametrici (M4) |
| `results_zne_comparison_*.json` | Output del confronto ZNE |
| `GUIDA_ESPERIMENTI_PARAMETRI.md` | Guida dettagliata agli sweep parametrici e alle previsioni attese |

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python run_experiments.py            # campagne M1/M2 sui use case
python run_parameter_analysis.py --sweep k   # uno sweep alla volta (vedi GUIDA)
```
Gli script scrivono i risultati JSON in questa cartella. Dettagli, previsioni attese e ordine
consigliato: `GUIDA_ESPERIMENTI_PARAMETRI.md`.

## Risultato chiave (già in tesi)

- **Metodo 1** (TOP-1): M̄₁ = 6.43 iterazioni (UC1).
- **M_TOP4** (TOP-4 senza ML): M̄ = 1.00 — statisticamente equivalente a M2 (UC1, p=0.849).
- **Conclusione**: il classificatore ML a valle **non serve**; il guadagno è della ricerca
  multi-candidato TOP-4. Motiva il pivot alla QEC (blocchi M5→M8).
