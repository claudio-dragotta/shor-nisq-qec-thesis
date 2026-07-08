# Problema computazionale — Use Case UC3 e UC4 (N=21)

## Contesto

La tesi implementa l'algoritmo di Shor con decomposizione di Beauregard (2002) per N=21.
Il circuito risultante ha **~2.800 porte CX su 20 qubit**.

Simularlo classicamente con modello di rumore richiede di calcolare
**256–1024 traiettorie indipendenti** su uno spazio di Hilbert di dimensione 2²⁰ ≈ 1.000.000
di ampiezze complesse. Su un laptop (16 GB RAM, CPU i7), ogni singola run richiede stimati
**3–5 ore**; 30 ripetizioni per uso case sarebbero ~4 giorni di calcolo continuo.

---

## Opzione A — Accesso IBM Quantum (raccomandata per pubblicazione)

**Cosa serve:** account IBM Quantum con quota di shot su un backend ≥ 20 qubit
(es. `ibm_kyiv`, `ibm_nazca`, `ibm_torino` — tutti ≥ 127 qubit).

**Come funziona:** il circuito viene inviato al cloud IBM e girato su hardware superconduttivo reale.
Una run da 1024 shot richiede ~30–60 secondi. Le 30×4 = 120 ripetizioni totali
richiederebbero poche ore di coda.

**Perché è la scelta migliore per un articolo:**
- Si testa l'algoritmo su hardware NISQ reale, non in simulazione
- I parametri di rumore (ε₂q, T1, T2) sono quelli reali della macchina
- Risultato più credibile e pubblicabile
- IBM Quantum è gratuito per accademici (piano Open o accesso tramite hub universitario)

**Cosa chiedere:** accesso all'hub IBM Quantum del dipartimento/ateneo,
oppure credenziali personali con piano Open (limite: 10 min/mese di QPU time — sufficiente).

---

## Opzione B — Cluster HPC universitario

**Cosa serve:** accesso a un nodo con ≥ 64 GB RAM e ≥ 16 core CPU.

**Come funziona:** si esegue lo stesso codice Python/Qiskit in simulazione classica,
ma su hardware più potente. Con 64 GB RAM e parallelizzazione, il tempo
per 30 ripetizioni × 4 use case scenderebbe a ~12–24 ore (run notturna).

**Codice:** nessuna modifica necessaria — lo stesso `run_top4_baseline.py` funziona su cluster.
Basta un job Slurm/PBS standard con `python run_top4_baseline.py`.

**Perché è un'alternativa valida:**
- Risultati identici a quelli su laptop, solo più veloci
- Nessuna dipendenza da servizi cloud esterni
- Utile anche per replicabilità (cluster universitario = riproducibile da altri)

**Cosa chiedere:** account sul cluster HPC del dipartimento (SCAFANDRO, ENEA, CINECA, ecc.)
e tempo di calcolo su una coda CPU standard.

---

## Opzione C — UC3/UC4 come analisi teorica (senza esperimenti)

**Cosa serve:** niente di aggiuntivo.

**Come funziona:** UC3 e UC4 rimangono nella tesi ma senza dati sperimentali.
Si riportano solo:
- Profondità circuito: depth=X, CX=2.806
- Probabilità di sopravvivenza stimata: P_surv = (1 − ε₂q)^{CX}
  - UC3 (ε₂q=0.001): P_surv ≈ 6%
  - UC4 (ε₂q=0.0005): P_surv ≈ 25%
- Confronto con N=15: mostra la scalabilità del metodo

**Perché è accettabile per una tesi:**
- Il limite computazionale è noto e documentato nella letteratura NISQ
- La tesi dimostra già M1 vs M_TOP4 vs M2 su UC1/UC2 (N=15)
- UC3/UC4 dimostrano la scalabilità teorica della decomposizione Beauregard

**Svantaggio per pubblicazione:** reviewer potrebbero chiedere dati sperimentali su N=21.

---

## Riepilogo

| | A — IBM Quantum | B — HPC | C — Solo teorica |
|---|---|---|---|
| Tempo | Pochi giorni (coda) | 12–24h notturna | Già disponibile |
| Forza per articolo | ★★★ | ★★ | ★ |
| Dipendenze | Account IBM | Account cluster | Nessuna |
| Modifica codice | Minima (backend reale) | Nessuna | Nessuna |

**Raccomandazione:** Opzione A per pubblicazione, Opzione C se la tesi rimane solo tesi.
