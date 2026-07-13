# Extra — Errore coerente vs errore di Pauli

**Analisi complementare** (Cap. 12, §"Oltre il Modello di Pauli"). Nasce dal paper su **Plaquette**
(QC Design, preprint arXiv luglio 2026) segnalato dal relatore: i simulatori Clifford-Pauli (come
**Stim**, usato in M7) sottostimano l'errore logico quando il rumore reale non è Pauli casuale —
in particolare per **errori coerenti** (sovrarotazioni di calibrazione) e **leakage**.

## Cosa dimostra

Il meccanismo di base, su scala trattabile (full-state, un qubit): a **parità** di probabilità di
errore per operazione p, l'errore **coerente** si accumula molto più di quello di **Pauli**.

| Modello | Come | Accumulo dopo N operazioni |
|---|---|---|
| Pauli | errore X con probabilità p | **lineare**: ~N·p |
| Coerente | sovrarotazione RX(θ), sin²(θ/2)=p | **quadratico**: sin²(Nθ/2) |

## File

| File | Cos'è |
|---|---|
| `qec_coherent.py` | Simula (Qiskit Aer) e confronta con la teoria; salva JSON |
| `results_coherent_vs_pauli_*.json` | Curve di accumulo (sim + teoria) per i due modelli |

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python qec_coherent.py                 # p=0.01, N=1..20, 20000 shot
# opzioni: --p --Nmax --shots --seed
```

Figura: `../../../figure_src/gen_coherent.py` → `file_latex/figure/qec_coherent.pdf`.

## Risultato

Simulazione = teoria (validato). A p=0.01: già a **N=8** l'errore coerente (~52%) è **~7×** quello
di Pauli (~7%). Il modello di Pauli è quindi **ottimistico**. Su un codice completo il divario si
amplifica (il paper riporta fino a 25-56× su surface code d=9). Conferma il limite del nostro
approccio Stim/Pauli in M7, presentato in tesi come baseline ottimistica.
