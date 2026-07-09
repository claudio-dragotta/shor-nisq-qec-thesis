# Indice del progetto — Tesi Magistrale (Shor + QEC)

> Leggenda di **dove si trova cosa** e **a che serve**. Aggiornato il 2026-07-09 dopo il
> riordino della cartella. Regola: `file_latex/` contiene SOLO ciò che serve a Overleaf;
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
| `INDICE_PROGETTO.md` | Questo file | 🟢 attivo |
| `AVVIO_WSL.md` | Guida al setup dell'ambiente WSL + Qiskit | 🟢 riferimento |
| `tesi_compilata.pdf` | Ultimo PDF prodotto da `file_latex/main.tex` (164 pp.) | output |
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
| `capitoli/` | I 17 file `.tex` dei capitoli attivi (sotto) |
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

| File | Cos'è | Stato |
|---|---|---|
| `shor_core.py` | Funzioni core: circuito di Shor, QFT⁻¹, noise model, Metodo 1/2 | 🟢 core |
| `beauregard.py` | Decomposizione efficiente per N=21/35 | 🟢 core |
| `qec_repetition.py` | **M5**: repetition code bit-flip/phase-flip (verify + curva p_L) | 🟢 QEC |
| `run_experiments.py`, `run_top4_baseline.py` | Campagne Metodo 1/2 e TOP-4 | 🟢 riusabile |
| `run_parameter_analysis.py` | Sweep parametrici (→ Appendice A) | 🟢 riusabile |
| `run_zne_comparison.py` | Confronto ZNE | 🟢 riusabile |
| `train_classifier.py`, `mwu_analysis.py` | Training classificatore + test statistici | 🟢 riusabile |
| `pilot_calibration.py`, `pilot_uc3_uc4.py`, `test_beauregard_cx.py` | Script di calibrazione/pilota | riferimento |
| `generate_figures.py`, `extract_latex.py` | Utility figure/LaTeX (campagne M1/M2) | riferimento |
| `clf_UC1.joblib`, `clf_UC2.joblib` | Classificatori addestrati (Metodo 2) | dato |
| `results_*.json` | Output degli esperimenti (M5, campagne parametriche, ZNE) | dato |
| `requirements.txt` | Ambiente Python versionato (qiskit, aer, numpy, scipy, matplotlib) | 🟢 attivo |
| `GUIDA_ESPERIMENTI_PARAMETRI.md` | Guida agli sweep parametrici | riferimento |

> **Prossimi file QEC** (dal piano): `qec_steane.py` (M6), `qec_surface.py` (M7, +stim/pymatching),
> `shor_logico.py` (M8).

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
