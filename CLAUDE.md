# CLAUDE.md — Tesi Magistrale: Algoritmo di Shor e QML/QEC
## Claudio Dragotta | Relatore: Ing. Floriano Caprio
## Università Campus Bio-Medico di Roma | A.A. 2024/2025

---

## Prima di fare qualsiasi cosa: leggi il diario

Il file `diario_relatore.md` nella root di questa directory contiene tutte le decisioni prese con il professore, in ordine cronologico. Leggilo prima di suggerire modifiche strutturali alla tesi.

---

## Di cosa parla questa tesi

L'algoritmo di Shor fattorizza interi in tempo polinomiale, ma su hardware NISQ il rumore degrada l'output rendendo necessarie molte iterazioni per ottenere il risultato corretto. L'obiettivo della tesi è dimostrare che un classificatore ML, addestrato sugli output rumorosi del simulatore Qiskit, può ridurre drasticamente il numero di iterazioni necessarie (da decine a ~3).

**Il contributo originale** è il confronto sperimentale tra:
- **Metodo 1**: approccio classico — raccolta distribuzione output → analisi gaussiana → picco = valore più probabile
- **Metodo 2**: classificatore ML — dato l'output di una singola esecuzione, decide se è corretto o no

---

## Stack tecnologico

| Componente | Scelta | Motivazione |
|---|---|---|
| Framework quantistico | **Qiskit + Qiskit Aer** | Standard IBM, tutorial ufficiale disponibile, noise model realistico |
| Simulatore rumoroso | **AerSimulator** | Depolarizing noise + T1/T2 + readout error configurabili |
| Accelerazione | **qiskit-aer-gpu** (CUDA, RTX 4070) | Riduce i tempi di simulazione di 10--20x |
| Libreria ML | **scikit-learn** | Interfaccia unificata per RF, SVM, MLP |
| Ambiente | **WSL Ubuntu 22.04** su Windows 11 | Compatibilità Linux, accesso GPU via CUDA |
| LaTeX | **Overleaf** (biber + biblatex) | Template Campus Bio-Medico |
| Repo Shor | https://github.com/Graychii/Shor-Algorithm-Implementation | Implementazione ideale senza rumore |

**Virtual environment Python**: `source ~/quantum-env/bin/activate`

---

## Struttura della tesi (14 capitoli)

### Parte teorica — COMPLETATA (approvata dal relatore)

| # | File | Titolo | Stato |
|---|---|---|---|
| 1 | `Introduzione.tex` | Introduzione | ✅ Completo |
| 2 | `Obiettivi.tex` | Obiettivi | ✅ Completo |
| 3 | `Fondamenti.tex` | Fondamenti del Calcolo Quantistico | ✅ Completo |
| 4 | `Shor.tex` | L'Algoritmo di Shor | ✅ Completo |
| 5 | `Rumore.tex` | Rumore Quantistico e Correzione degli Errori | ✅ Completo |
| 6 | `StrategieAntiRumore.tex` | Strategie per la Riduzione del Rumore Quantistico | ✅ Completo |

### Parte sperimentale — IN CORSO

| # | File | Titolo | Stato |
|---|---|---|---|
| 7 | `Metodologia.tex` | Metodologia e Architettura | ✅ Scritto |
| 8 | `SpecificheFunzionali.tex` | Specifiche Funzionali del Software | ✅ Scritto |
| 9 | `Sviluppo.tex` | Sviluppo e Implementazione | ✅ Scritto (manca: scelta ML finale dopo test) |
| 10 | `RisultatiMetodo1.tex` | Risultati — Metodo 1 | 🔲 Skeleton dettagliato — aspetta test |
| 11 | `RisultatiMetodo2.tex` | Risultati — Metodo 2 | 🔲 Skeleton dettagliato — aspetta test |
| 12 | `ConclusioniMetodo1.tex` | Conclusioni — Metodo 1 | 🔲 Skeleton dettagliato — aspetta test |
| 13 | `ConclusioniMetodo2.tex` | Conclusioni — Metodo 2 | 🔲 Skeleton dettagliato — aspetta test |
| 14 | `SviluppiFuturi.tex` | Sviluppi Futuri | ✅ Scritto |

I file skeleton contengono in italiano la descrizione precisa di cosa va inserito in ogni sezione — leggili prima di scrivere quei capitoli.

---

## I quattro use case (da fissare con i test)

Servono 4 use case per la validazione accademica (requisito per eventuale pubblicazione).

**Criterio di selezione:**
- Use Case 1 e 2: stesso N, livello di rumore diverso (basso vs alto)
- Use Case 3 e 4: N crescente, stesso livello di rumore

**Punto di partenza**: N=15, a=7, n_count=8 (dal tutorial IBM)

I valori esatti vengono fissati durante la fase esplorativa iniziale.

---

## Parametri del noise model

```python
from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error, ReadoutError

def build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns, gate_time_ns=50, p_ro=0.02):
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(eps_1q, 1), ['h', 'x', 'rz', 'cp'])
    nm.add_all_qubit_quantum_error(depolarizing_error(eps_2q, 2), ['cx', 'swap'])
    nm.add_all_qubit_quantum_error(thermal_relaxation_error(t1_ns, t2_ns, gate_time_ns), ['h', 'x'])
    nm.add_all_qubit_readout_error(ReadoutError([[1-p_ro, p_ro], [p_ro, 1-p_ro]]))
    return nm
```

Valori di riferimento (ibm_marrakesh):
- `eps_1q` = 1e-3, `eps_2q` = 1e-2
- `T1` = 100_000 ns, `T2` = 80_000 ns
- `p_ro` = 0.02

---

## Metriche chiave del confronto

| Metrica | Descrizione |
|---|---|
| `M̄₁` | Iterazioni medie per risultato corretto (Metodo 1) |
| `M̄₂` | Iterazioni medie per risultato corretto (Metodo 2) |
| `ρ = M̄₁/M̄₂` | **Fattore di riduzione** — il risultato principale della tesi |
| F1, AUC | Prestazioni del classificatore sul test set |

Ipotesi da verificare: `M̄₂ ≈ 3`, `ρ ≫ 1`

---

## Come compilare il LaTeX

La tesi è su Overleaf. Per compilare localmente (se necessario):
```bash
cd file_latex/
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```
Il backend è **biber** (non bibtex). Usa sempre `pdflatex + biber + pdflatex x2`.

---

## Decisioni architetturali già chiuse (non riaprire)

1. **Framework**: Qiskit — chiuso il 2026-03-18 con il relatore
2. **Approccio**: QML + classificatore binario — chiuso il 2026-03-14
3. **QEC come sottocategoria di QML** — indicazione esplicita del relatore (2026-03-13)
4. **Focus su problemi fisici del rumore**, non matematici — indicazione del 2026-03-26
5. **4 use case** per la validazione — requisito del relatore (2026-04-10)

---

## File importanti nella root

| File | Contenuto |
|---|---|
| `diario_relatore.md` | Registro di tutte le riunioni con il prof — aggiorna dopo ogni incontro |
| `piano_azione_setup.md` | Guida step-by-step per setup WSL + Qiskit + GPU |
| `CLAUDE.md` | Questo file |
| `shors-algorithm.ipynb` | Notebook Qiskit di riferimento per i test iniziali |
| `file_latex/` | Tutti i file LaTeX della tesi |
| `file_latex/Bibliografia.bib` | ~36 citazioni — aggiorna quando aggiungi riferimenti |
| `file_latex/capitoli/Acronimi.tex` | Definizioni acronimi — aggiungi qui nuovi acronimi |

---

## Acronimi già definiti

BHT, BQP, CCNOT, CDR, CNF, CNOT, CPTP, DFT, DSA, ECDSA, GNFS, HTTPS, IBM, MIT, NIST, NISQ, NMR, PEC, PQC, QEC, QFT, QML, QMA, QPE, RSA, SAT, SSH, TLS, TSP, ZNE, **AUC, GCD, GPU, MLP, SVM, WSL** (ultimi 6 aggiunti il 2026-04-10)

---

## Stile di scrittura (da mantenere coerente)

- Lingua: **italiano accademico formale**
- Termini tecnici in inglese alla prima occorrenza: `\textbf{termine} (\textit{english term})`
- Acronimi: usa sempre `\ac{SIGLA}` (prima occorrenza espande, successive abbreviano)
- Equazioni numerate con `\label{eq:...}` e referenziate con `\eqref{}`
- Ogni capitolo inizia con un paragrafo che si aggancia esplicitamente alla fine del capitolo precedente
- Footnote per info storiche o supplementari non essenziali al filo del testo
- Ogni capitolo usa `\begin{onehalfspace} ... \end{onehalfspace}`
- Figure e tabelle: sempre `[H]`, caption descrittiva sotto, label con `fig:` o `tab:`
- Codice Python: ambiente `lstlisting` con caption
