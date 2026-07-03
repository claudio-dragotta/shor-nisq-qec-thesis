# CLAUDE.md — Tesi Magistrale: Algoritmo di Shor e QML/QEC
## Claudio Dragotta | Relatore: Ing. Floriano Caprio
## Università Campus Bio-Medico di Roma | A.A. 2024/2025

---

## ⚠ REGOLA PERMANENTE: aggiorna Struttura della Tesi dopo ogni modifica

**Ogni volta che modifichi, aggiungi o elimini un capitolo**, aggiorna obbligatoriamente:
1. La sezione `\section{Struttura della Tesi}` in `file_latex/capitoli/Introduzione.tex` (cerca il commento `% ⚠ SYNC-STRUTTURA`)
2. La tabella "Struttura della tesi" in questo `CLAUDE.md`

Questa è una regola standing: non aspettare che l'utente te lo chieda.

---

## Prima di fare qualsiasi cosa: leggi il diario

Il file `diario_relatore.md` nella root di questa directory contiene tutte le decisioni prese con il professore, in ordine cronologico. Leggilo prima di suggerire modifiche strutturali alla tesi.

---

## Di cosa parla questa tesi

L'algoritmo di Shor fattorizza interi in tempo polinomiale, ma su hardware NISQ il rumore degrada l'output rendendo necessarie molte iterazioni per ottenere il risultato corretto. L'ipotesi di partenza era che un classificatore ML, addestrato sugli output rumorosi del simulatore Qiskit, potesse ridurre drasticamente il numero di iterazioni (da decine a ~3).

**L'esito sperimentale (e il messaggio attuale della tesi)** è un **risultato negativo consapevole sul ML**: l'analisi di ablazione dimostra che il guadagno (ρ=6.44 su UC1, ρ=2.42 su UC2) è interamente attribuibile alla **strategia di ricerca multi-candidato TOP-4**, non al classificatore, che risulta neutro su UC1 (p=0.849) e dannoso su UC2 (ρ=0.73 < 1). Direttiva del relatore (2026-07): presentare esplicitamente "cosa abbiamo testato e perché", dimostrando che l'IA usata così (filtro a valle sull'output) non serve.

**Il contributo originale** è duplice:
1. La dimostrazione sperimentale che TOP-4 riduce M̄ da 6.43 a 1.00, con robustezza completa ai parametri di rumore (campagna parametrica) e superiorità netta su ZNE
2. L'isolamento via ablazione del contributo del classificatore ML (nullo/negativo) — confronto a tre: **M1** (TOP-1), **M_TOP4** (TOP-4 senza clf), **M2** (CLF+TOP-4)

**Prossima fase (Parte B, da definire col prof)**: nuovo algoritmo come contributo conclusivo — vedi `piano_azione_revisione.md`.

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

## Struttura della tesi (11 capitoli)

### Parte introduttiva e raccordo

| # | File | Titolo | Stato |
|---|---|---|---|
| 1 | `Introduzione.tex` | Introduzione | ✅ Completo |
| 2 | `ObiettiviPianoSperimentale.tex` | Obiettivi e Piano Sperimentale | ✅ Completo — include ex-Cap.8 (SpecificheFunzionali) |

### Parte teorica — COMPLETATA (approvata dal relatore)

| # | File | Titolo | Stato |
|---|---|---|---|
| 3 | `Fondamenti.tex` | Fondamenti del Calcolo Quantistico | ✅ Completo |
| 4 | `Shor.tex` | L'Algoritmo di Shor | ✅ Completo |
| 5 | `Rumore.tex` | Rumore Quantistico nei Sistemi NISQ | ✅ Completo |
| 6 | `StrategieAntiRumore.tex` | Strategie per la Riduzione del Rumore Quantistico | ✅ Completo |

### Parte sperimentale — IN CORSO

| # | File | Titolo | Stato |
|---|---|---|---|
| 7 | `Strumenti.tex` | Strumenti e Ambiente di Simulazione | ✅ Completo |
| 8 | `Metodologia.tex` | Metodologia e Architettura | ✅ Scritto |
| 9 | `Sviluppo.tex` | Sviluppo e Implementazione | ✅ Scritto — include tabella selezione classificatore (RF/SVM/MLP) con metriche reali |
| 10 | `RisultatiSperimentali.tex` | Risultati Sperimentali: dal Classificatore ML alla Strategia TOP-K | ✅ Scritto — FUSIONE (2026-07) dei 4 ex-capitoli Risultati/Conclusioni M1+M2; baseline, ablazione, campagna parametrica, ZNE, discussione |
| 11 | `SviluppiFuturi.tex` | Sviluppi Futuri | ✅ Scritto — include direzione "ML a monte" (predizione impatto errori) |

> `SpecificheFunzionali.tex` ELIMINATO il 2026-05-15 — contenuto integrato in Cap.2.
> `RisultatiMetodo1/2.tex` e `ConclusioniMetodo1/2.tex` FUSI il 2026-07-03 in `RisultatiSperimentali.tex` (indicazione relatore). I vecchi file restano nel repo ma NON sono più inclusi in `main.tex`. Il label del capitolo unico è `chap:risultati`; i vecchi label `chap:risultati1/2`, `chap:conclusioni1/2` sono alias sullo stesso capitolo.

I file skeleton contengono in italiano la descrizione precisa di cosa va inserito in ogni sezione — leggili prima di scrivere quei capitoli.

---

## I quattro use case (parametri derivati dalla letteratura — da validare sperimentalmente)

Servono 4 use case per la validazione accademica (requisito per eventuale pubblicazione).
**Attenzione**: i parametri sotto sono le ipotesi di partenza formalizzate in Cap.2 (tab:use_case_params), derivati da ibm_marrakesh e dalla letteratura. Non sono ancora stati validati sperimentalmente — i test WSL potrebbero portare ad aggiustamenti.

**Asse rumore**: UC1 vs UC2 — stesso circuito N=15, livello di rumore diverso (isola l'effetto del rumore)
**Asse scalabilità**: UC1, UC3, UC4 — N crescente (15→21→35), stesso rumore NISQ-realistico

| Parametro | UC 1 | UC 2 | UC 3 | UC 4 |
|---|---|---|---|---|
| N | 15 | 15 | 21 | 35 |
| a | 7 | 7 | 2 | 6 |
| periodo r atteso | 4 | 4 | 6 | 2 |
| n_count (qubit) | 8 | 8 | 10 | 12 |
| M_shots | 4096 | 4096 | 4096 | 4096 |
| Livello rumore | NISQ-realistico | NISQ-degradato | NISQ-realistico | NISQ-realistico |
| ε_1q | 1e-3 | 5e-3 | 1e-3 | 1e-3 |
| ε_2q | 1e-2 | 5e-2 | 1e-2 | 1e-2 |
| T1 (ns) | 100_000 | 50_000 | 100_000 | 100_000 |
| T2 (ns) | 80_000 | 30_000 | 80_000 | 80_000 |
| p_ro | 0.02 | 0.05 | 0.02 | 0.02 |

NISQ-degradato = tassi errore ×5, T1/T2 dimezzati rispetto al realistico.

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

BHT, BQP, CCNOT, CDR, CNF, CNOT, CPTP, DFT, DSA, ECDSA, GNFS, HTTPS, IBM, MIT, NIST, NISQ, NMR, PEC, PQC, QEC, QFT, QML, QMA, QPE, RSA, SAT, SSH, TLS, TSP, ZNE, AUC, GCD, GPU, MLP, SVM, WSL, SDK, API, CPU, **ML, LSTM** (ultimi 2 aggiunti il 2026-05-17)

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
