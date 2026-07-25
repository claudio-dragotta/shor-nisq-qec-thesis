# Indice del progetto — Tesi Magistrale (Shor + QEC)

> Leggenda di **dove si trova cosa** e **a che serve**. Aggiornato il 2026-07-25 dopo la ristrutturazione della tesi
> (sunti nel corpo + trattazioni estese in appendice, corpo ~119 pp). Regola: `file_latex/` contiene SOLO ciò che serve a Overleaf;
> tutto il resto (script, output, materiale superato) vive fuori.

---

## Mappa rapida delle cartelle

```
tesi_magistrale_quantum/
├── file_latex/          ← SORGENTI TESI (questo si carica su Overleaf, niente altro)
├── figure_src/          ← script Python che GENERANO le figure di file_latex/figure/
├── Extra/experiments/   ← codice sperimentale (Qiskit): Shor, noise, QEC, campagne
├── Extra/articoli|tesi_esterne|thesis_images/  ← materiale di riferimento
├── _archivio/           ← documenti e capitoli SUPERATI (storico, non cancellati)
├── *.md                 ← documenti di lavoro attivi (piano, diario, questo indice)
└── tesi_compilata.pdf   ← ultimo PDF compilato (output, non è un sorgente)
```

---

## ROOT — documenti di lavoro attivi

| File | Cos'è | Stato |
|---|---|---|
| `CLAUDE.md` | Istruzioni e contesto del progetto (letto da Claude Code) | 🟢 attivo |
| `diario_relatore.md` | Registro cronologico di tutte le riunioni col prof | 🟢 attivo |
| `piano_azione_qec.md` | **Piano corrente**: milestone M0–M9 QEC + semaforo di validazione (flag) | 🟢 attivo |
| `INDICE_PROGETTO.md` | Questo file (indice dettagliato, IT) | 🟢 attivo |
| `README.md` | Overview del progetto in **inglese** (struttura, build, cosa è stato fatto) | 🟢 attivo |
| `Proposta_nuovo_ML.md` | Proposta di un nuovo algoritmo di decodifica *topology-aware* per Shor | 🟢 attivo |
| `AVVIO_WSL.md` | Guida al setup dell'ambiente WSL + Qiskit | 🟢 riferimento |
| `tesi_compilata.pdf` | Ultimo PDF prodotto da `file_latex/main.tex` (184 pp.; corpo ~119) | output |
| `.gitignore` | Ignora artefatti build, `__pycache__`, PDF | 🟢 attivo |

---

## file_latex/ — SORGENTI DELLA TESI (Overleaf-ready)

> Contiene esclusivamente i file necessari alla compilazione. Per compilare (Overleaf o
> locale): `pdflatex → biber → pdflatex ×2`.

| File / cartella | Cos'è |
|---|---|
| `main.tex` | File master: preambolo, ordine dei capitoli, bibliografia |
| `TITLE.tex` | Frontespizio |
| `Bibliografia.bib` | Bibliografia (biblatex + biber) |
| `capitoli/` | I 22 file `.tex` di capitoli e appendici attivi (sotto) |
| `figure/` | Immagini incluse nella tesi (`.pdf`, `.png`, `.jpg`) — **generate da `figure_src/`** |

### file_latex/capitoli/ — i capitoli (ordine in `main.tex`)

| # | File | Titolo |
|---|---|---|
| — | `Acronimi.tex` | Definizioni acronimi (nel preambolo) |
| 1 | `Introduzione.tex` | Introduzione |
| 2 | `ObiettiviPianoSperimentale.tex` | Obiettivi e Piano Sperimentale |
| 3 | `Fondamenti.tex` | Fondamenti del Calcolo Quantistico |
| 4 | `Shor.tex` | L'Algoritmo di Shor |
| 5 | `Rumore.tex` | Rumore Quantistico nei Sistemi NISQ |
| 6 | `StrategieAntiRumore.tex` | Strategie per la Riduzione del Rumore |
| 7 | `Strumenti.tex` | Strumenti e Ambiente di Simulazione |
| 8 | `Metodologia.tex` | Metodologia e Architettura |
| 9 | `Sviluppo.tex` | Sviluppo e Implementazione |
| 10 | `RisultatiSperimentali.tex` | Verifica Sperimentale dell'Ipotesi Iniziale (capitolo PONTE) |
| 11 | `CorrezioneErrori.tex` | La Correzione d'Errore Quantistico (repetition → Steane) **[QEC]** |
| 12 | `SurfaceCode.tex` | Il Surface Code e la Stima dell'Errore Logico **[QEC]** |
| 13 | `ShorLogico.tex` | Integrazione: lo Shor Logico **[QEC]** |
| 14 | `SviluppiFuturi.tex` | Sviluppi Futuri |
| A | `AppendiceParametrica.tex` | Campagna Parametrica Dettagliata e Confronto ZNE |
| B | `AppendiceFondamenti.tex` | Fondamenti del Calcolo Quantistico — Trattazione Estesa |
| C | `AppendiceStrumenti.tex` | Strumenti e Ambiente di Simulazione — Trattazione Estesa |
| D | `AppendiceIntroduzione.tex` | Contesto Esteso dell'Introduzione |
| E | `AppendiceObiettivi.tex` | Dettaglio degli Obiettivi e del Piano Sperimentale |
| F | `AppendiceClassificatore.tex` | Il Classificatore ML: Architettura, Addestramento e Metriche |
| — | `Ringraziamenti.tex` | Ringraziamenti |

---

## figure_src/ — generatori delle figure

> Script Python che producono le immagini in `file_latex/figure/`. Stanno FUORI da `file_latex`
> perché a Overleaf non servono. Ogni script scrive automaticamente in `../file_latex/figure/`.
> Eseguire in WSL con `~/quantum-env` attivo, es. `python figure_src/gen_qec_repetition.py`.

| Script | Figure prodotte |
|---|---|
| `gen_bloch.py` | Sfera di Bloch |
| `gen_circuits.py` | Circuito di Bell, tavola delle porte |
| `gen_complexity.py` | Classi di complessità (P ⊆ BPP ⊆ BQP ⊆ PSPACE) |
| `gen_noise_figures.py` | Canali di rumore su Bloch, P_success vs n (Cap. 5) |
| `gen_qec_repetition.py` | Curva p vs p_L del codice a ripetizione (M5, Cap. 11) |

---

## Extra/experiments/ — codice sperimentale (Qiskit)

Organizzato **per blocco M**: ogni cartella ha codice + risultati (JSON) + un `README.md` che
spiega cosa fa, cosa aspettarsi e come leggere i risultati. Indice generale in
`Extra/experiments/README.md`.

| Cartella | Blocco | Contenuto | Stato |
|---|---|---|---|
| `campagne_classiche_M1-M4/` | M1–M4 | `shor_core.py`, `beauregard.py` + campagne (Metodo 1/2, TOP-4, parametrica, ZNE) + classificatori + JSON. **Tenuti insieme**: import interdipendenti | ✅ fatto |
| `M5_repetition_code/` | M5 | `qec_repetition.py` + JSON (bit-flip/phase-flip) | ✅ completo |
| `M6_steane_code/` | M6 | `qec_steane.py` + JSON (check/verify/curve) | ✅ completo |
| `M7_surface_code/` | M7 | `qec_surface.py` (Stim+PyMatching) | ⬜ da fare |
| `M8_shor_logico/` | M8 | `shor_logico.py` (p_L → P_success) | ⬜ da fare |
| `requirements.txt` | — | Ambiente versionato (qiskit 2.5, aer, numpy, scipy, matplotlib) | 🟢 |

> Gli script figura (`figure_src/gen_qec_*.py`) leggono i JSON dalle rispettive cartelle
> `M5_.../ M6_.../` e scrivono in `file_latex/figure/`.

---

## Extra/ — materiale di riferimento

| Cartella | Contenuto |
|---|---|
| `Extra/articoli/` | Articoli scientifici (PDF) |
| `Extra/tesi_esterne/` | Tesi di altri usate come riferimento |
| `Extra/thesis_images/` | Immagini varie di lavoro |

---

## _archivio/ — storico (superato, non cancellato)

> Documenti della fase **precedente al pivot QEC** (idea "gestione predittiva / anti-duplicazione",
> M_PRED) e i capitoli sostituiti. Tenuti come registro, non fanno parte della tesi corrente.

| File | Cos'era |
|---|---|
| `documento_algoritmo_predittivo.{tex,pdf}` | Proposta dettagliata M_PRED (superata) |
| `proposta_algoritmo_mitigazione_qpu.{md,pdf}` | Proposta originale dell'idea predittiva |
| `proposta_sistema_predittivo.{tex,pdf}` | Variante della proposta M_PRED |
| `mappa_fase_sperimentale.md` | Work packages del sistema predittivo (superati) |
| `piano_azione_revisione.md` | Piano Parte A (fusione capitoli, ✅ fatta) + Parte B M_PRED (superata) |
| `capitoli_storici/` | 5 capitoli `.tex` fusi/sostituiti: RisultatiMetodo1/2, ConclusioniMetodo1/2, NuovoApproccio |
