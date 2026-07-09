# Piano d'azione — Riallineamento QEC (dal 2026-07-09)

> **Fonte vincolante**: `Documento_tesi_Shor_QEC.docx` (v1.0, 8 luglio 2026) — indicazione del
> prof: *attenersi in maniera super fedele*. Registro della riunione: `diario_relatore.md`
> (2026-07-08). Questo piano SOSTITUISCE la Parte B di `_archivio/piano_azione_revisione.md`
> (direzione M_PRED/anti-duplicazione, archiviata).
>
> **Decisioni di impianto (Claudio, 2026-07-09)**:
> 1. La STRUTTURA attuale della tesi resta (teoria approvata dal relatore); il documento
>    guida fedelmente contenuti, metriche e milestone della NUOVA parte sperimentale.
> 2. Il capitolo ponte (cap. 10, verifica ML/TOP-4) RESTA come capitolo.
>
> **Deadline: ottobre 2026.**

---

## Il messaggio della tesi (versione aggiornata)

Arco narrativo completo:
1. Shor su NISQ fallisce per il rumore (teoria, cap. 3–6).
2. Prima campagna: l'ML **a valle** dell'output non serve — vince TOP-4 (risultato negativo
   consapevole, cap. 10 ponte).
3. **Nucleo nuovo**: se filtrare l'output non basta, l'errore va **corretto alla radice**,
   codificando qubit logici — QEC con circuito ancillare: repetition → Steane [[7,1,3]] →
   surface code (cap. 11–12).
4. Integrazione: **Shor logico** — quale errore logico p_L serve perché Shor mantenga
   P_success ≥ 80% (cap. 13). Break-even: quando p_L < p il qubit logico conviene.
5. (Solo prospettiva, Sviluppi Futuri: rete neurale che conferma/nega la correzione
   ancillare — menzione del prof, fuori perimetro salvo tempo residuo.)

---

# PARTE T — Modifiche alla tesi

## T1 — Nuovi capitoli (creati 2026-07-09, con segnaposto [DA COMPLETARE])

| # | File | Titolo | Fonte nel documento prof |
|---|---|---|---|
| 11 | `CorrezioneErrori.tex` | La Correzione d'Errore Quantistico: dal Codice a Ripetizione al Codice di Steane | §7 (concetti: stabilizzatori, sindrome, decoder, Pauli frame, distanza), §8 (confronto codici), §9 (Steane + laboratorio) |
| 12 | `SurfaceCode.tex` | Il Surface Code e la Stima dell'Errore Logico | §10 (griglia, detection events, MWPM, Stim+PyMatching, curve p vs p_L per d=3,5,7) |
| 13 | `ShorLogico.tex` | Integrazione: lo Shor Logico e i Requisiti di Correzione | §11 (architettura a 4 livelli, limiti di Stim sui non-Clifford, modello logico p_L, resource estimates Gidney-Ekerå) |

Label: cap. 11 `chap:qec` (+ alias `chap:predizione` per retro-compatibilità dei \ref),
cap. 12 `chap:surface`, cap. 13 `chap:integrazione`.

`NuovoApproccio.tex` esce da `main.tex` ma resta nel repo (come i 4 capitoli fusi).
La sezione "duplicazione dei qubit" viene riciclata come motivazione d'apertura del cap. 11
(dalla ridondanza ingenua alla codifica vera).

## T2 — Ritocchi ai capitoli esistenti

- [x] `main.tex`: swap cap. 11, aggiunta cap. 12–13, SviluppiFuturi → cap. 14
- [x] `Introduzione.tex`: §Motivazione ("seconda fase" → QEC/Shor logico) + SYNC-STRUTTURA
      (14 capitoli, paragrafi nuovi capitoli)
- [x] `RisultatiSperimentali.tex` (ponte): apertura (r.3) e §Bilancio (r.237) — il ponte ora
      punta alla QEC, non alla gestione predittiva
- [x] `SviluppiFuturi.tex`: apertura + §evoluzione_ml — refs riorientati; aggiunta direzione
      "rete neurale a supporto della decodifica" (indicazione prof 2026-07-08)
- [x] `Rumore.tex` r.137: riferimento al cap. successore (alias ok, testo rivisto)
- [x] `Bibliografia.bib`: + gidney2021, gidney2025, stim2021, pymatching2021, roffe2019
- [x] `Acronimi.tex`: + MWPM, CSS
- [x] `CLAUDE.md`: tabella struttura (14 cap + app.), messaggio tesi
- [ ] `ObiettiviPianoSperimentale.tex`: **PASSO SUCCESSIVO** — integrare le 7 domande di
      ricerca del documento (§2.1) e le metriche QEC (P_order, TV distance, p_L, break-even)
      nel contratto sperimentale; oggi il capitolo parla solo di ρ e dei 4 use case
- [ ] `StrategieAntiRumore.tex` (cap. 6): verificare coerenza col nuovo cap. 11 (oggi la QEC
      è presentata come sottocategoria del QML; il cap. 11 la tratta da protagonista) —
      eventuale nota di raccordo
- [ ] `Metodologia.tex`: quando parte l'implementazione, aggiungere la metodologia QEC
      (livelli 3–4 del documento §11.1)

## T3 — Regole dal documento (valgono per TUTTI i risultati nuovi)

- Ogni risultato: versione codice, seed, shot, noise model, parametri, profondità, #CX,
  script che rigenera la figura. **Figure rigenerate da CSV, mai a mano.**
- Metriche obbligatorie: P_success, P_order, TV distance, depth, #2q, p_L, break-even,
  intervalli di confidenza.
- Distinguere sempre: detection / correction / decoding; rumore fisico / rumore logico.
- Non dichiarare "Shor fault-tolerant completo": l'integrazione è a livelli, via p_L.

---

# PARTE I — Implementazione (milestone M0–M9 del documento)

## Stato: cosa è già coperto dal lavoro esistente

| Milestone | Stato | Note |
|---|---|---|
| M0 setup | ✅ fatto (2026-07-09) | `~/quantum-env` RICREATO in WSL (era sparito): Python 3.12, qiskit 2.5.0, qiskit-aer 0.17.2, numpy 2.5.1, scipy 1.18.0 → `experiments/requirements.txt` versionato. DA FARE per M7: `pip install stim pymatching` |
| M1 order finding classico | ✅ | verifica classica già nelle pipeline M1/M2 — da formalizzare in notebook `01` |
| M2 QFT manuale | 🔶 | QFT⁻¹ già implementata (cap. Sviluppo); MANCA il confronto sistematico manuale vs libreria su stati noti (2–5 qubit) → notebook `02`, mezza giornata |
| M3 Shor ideale | ✅ | N=15 fatto; N=21 documentato con barriera UnitaryGate (il doc chiede "N=21 tentato o discusso con limiti chiari" — fatto) |
| M4 Shor rumoroso | ✅ ~90% | curve parametro→P_success = campagna parametrica (App. A). GAP piccoli: (a) esperimento "solo readout" isolato, (b) metriche P_order e TV distance da estrarre dai dati esistenti o con run mirati, (c) esperimento F (transpiled vs non) = sweep optimization_level già fatto |
| M5 repetition code | ✅ COMPLETO (2026-07-09) | `qec_repetition.py`: bit-flip (basis Z) + phase-flip (basis X), sindrome con 2 ancilla, lookup. VERIFICA: 4/4 sindromi corrette per entrambi i codici. CURVA p vs p_L (20k shot): segue 3p²-2p³ entro l'errore statistico; break-even a p=0.5. Figura `qec_repetition_curve.pdf` (script `gen_qec_repetition.py`) + sezione `subsec:risultati_repetition` RIEMPITA in tesi. Compila 164 pp, 0 undefined. TUTTI I FLAG VERDI (vedi Parte V) |
| M6 Steane [[7,1,3]] | ✅ sperimentale COMPLETO (2026-07-09) | `qec_steane.py`: TUTTI E 3 I FLAG VERDI — (1) encoding \|0_L⟩ nel code space (sindrome 000000/2000 shot); (2) syndrome table BIIETTIVA X/Z/Y (matrice di Hamming, Y accende entrambe); (3) curva p vs p_L (Monte Carlo Pauli-frame, 200k shot): pendenza log-log 1.94 ≈ 2, pseudo-soglia tra 0.05 e 0.10. MANCA solo: figura + sezione in tesi (Cap. 11). Nota: syndrome extraction non fault-tolerant (dichiararlo, no overclaiming) |
| M7 surface code | ✅ COMPLETO (2026-07-09) | `M7_surface_code/qec_surface.py` (Stim + PyMatching MWPM), d=3,5,7, rounds=d, 200k shot. FLAG VERDI: sanity (d↑⇒p_L↓ a p piccolo) + soglia (incrocio curve) p_th≈0.9% base Z, ≈0.7% base X. Sotto soglia soppressione ×4/distanza; sopra soglia inversione. Figura `qec_surface_curve` + sezione Cap. 12. Compila 168 pp, 0 undefined. Rounds=2d = estensione |
| M8 Shor logico | ❌ NUOVO | iniettare errore logico p_L dopo ogni gate/blocco logico nello Shor esistente; curva p_L vs P_success; trovare p_L per P_success ≥ 80%; FIGURA CONCLUSIVA: Shor fisico rumoroso vs Steane vs surface |
| M9 scrittura | 🔶 | capitoli 11–13 creati con segnaposto → riempire man mano |

## Ordine di lavoro e stima (deadline ottobre)

1. **Luglio (sett. 2–3)**: M0 residuo (stim/pymatching, requirements) + notebook 01–02
   (M1/M2 formali) + **M5 repetition code** (piccolo: 3+2 qubit bit-flip, poi phase-flip).
   → primo risultato QEC da mostrare al prof subito.
2. **Luglio (sett. 4) – Agosto (sett. 1–2)**: **M6 Steane**: preparazione stato logico,
   laboratorio iniezione errori (doc §9.4 passo-passo), lookup decoder, curve.
3. **Agosto (sett. 3–4)**: **M7 surface code** con Stim/PyMatching (codice quasi pronto nel
   doc §10.2); sweep d=3,5,7 — attenzione ai tempi di decoding (mitigazione doc: partire da d=3).
4. **Settembre (sett. 1–2)**: **M8 Shor logico** + figura conclusiva.
5. **Settembre (sett. 3–4)**: **M9**: riempire i [DA COMPLETARE] dei cap. 11–13,
   aggiornare Obiettivi/Metodologia, conta pagine, revisione completa.
6. **Inizio ottobre**: buffer + revisione col prof.

Checklist settimanale (doc, App. B): report ≤2 pagine, ogni risultato → commit + notebook
eseguibile, ogni figura rigenerabile da script.

## Setup ambiente (da fare in WSL alla prossima sessione sperimentale)

```bash
source ~/quantum-env/bin/activate
pip install stim pymatching
pip freeze > requirements.txt   # versionare nel repo esperimenti
```

## Rischi (dal doc §13.3, adattati)

- Steane non fault-tolerant nella syndrome extraction → dichiarare modello e assunzioni
  (mai overclaiming: "corregge 1 errore arbitrario SE al più 1 errore nel blocco").
- Decoding lento su d=7 → scalare solo se sostenibile.
- Confusione fisico/logico → i livelli 1–4 del doc §11.1 vanno rispettati anche nel testo.
- Shot insufficienti → intervalli di confidenza sempre (p_L piccoli richiedono ≥10⁴ shot).

---

# PARTE V — Semaforo di validazione (i FLAG per ogni milestone)

> A cosa serve: dopo ogni esperimento devi poter dire in 10 secondi "🟢 va bene, procedo"
> oppure "🔴 c'è un bug, mi fermo". Ogni milestone ha (a) UN flag decisivo — il numero/
> comportamento che da solo dice se ha funzionato — e (b) una tabella di controlli con il
> valore atteso (🟢) e il segnale d'allarme (🔴). I valori attesi vengono dal documento del
> prof (§6 metriche, §9–10 comportamenti) e dalla teoria dei codici.

## Cruscotto — il flag DECISIVO di ogni milestone

| Milestone | Flag decisivo (🟢 se…) | Valore atteso |
|---|---|---|
| M2 QFT manuale | fidelity(QFT manuale, QFT libreria) = 1 su stati noti | ≥ 0.9999 |
| M4 Shor rumoroso | P_success cala al crescere di ε₂q, monotòna | ε₂q dominante (già visto) |
| M5 repetition ✅ | curva p_L segue 3p²−2p³ | scarto < 2σ su ogni punto ✅ |
| M6 Steane | mappa sindrome→qubit **biiettiva** sui 7 qubit + p_L ∝ p² | pendenza log-log ≈ 2 |
| M7 surface | le curve d=3,5,7 **si incrociano** a una soglia p_th | p_th ≈ 0.5–1% |
| M8 Shor logico | esiste p_L* con P_success = 80% **raggiungibile** da M7 | p_L* coerente con (d,p) reale |

> Regola d'oro trasversale (doc §6.1): un risultato senza seed + shot + noise model + intervallo
> di confidenza **non è un flag verde**, è "una fotografia colorata". Vale per tutti.

---

## M2 — QFT manuale vs libreria

| Controllo | 🟢 va bene se | 🔴 allarme se |
|---|---|---|
| Correttezza QFT | fidelity con la QFT di libreria ≥ 0.9999 su 2–5 qubit | fidelity < 1 → errore di segno/ordine swap |
| Stati noti | QFT\|0…0⟩ = stato uniforme; QFT su base → fasi corrette | picchi nel posto sbagliato |
| Inversa | QFT⁻¹·QFT = identità (a meno di fase globale) | residuo ≠ identità |

## M4 — Shor rumoroso (chiudere i gap, dati per lo più già presenti)

| Controllo | 🟢 va bene se | 🔴 allarme se |
|---|---|---|
| Monotonìa | P_success decresce al crescere di ε₂q | non-monotòna → seed/shot insufficienti |
| Dominanza | ε₂q sposta P_success molto più di ε₁q, T₁/T₂, p_ro | un secondario domina → bug noise model |
| P_order vs P_success | P_order ≥ P_success (il post-processing può solo perdere) | P_order < P_success → bug post-processing |
| TV distance | cresce con il rumore, ∈ [0,1] | fuori range → normalizzazione errata |

## M6 — Steane [[7,1,3]] (il codice CENTRALE)

**Flag decisivo**: iniettando un errore su ciascuno dei 7 qubit, la sindrome deve dare
**7 valori distinti e non nulli** (biiezione qubit↔sindrome). Se due qubit danno la stessa
sindrome, il decoder non può distinguerli → encoding o stabilizzatori sbagliati.

| Controllo | 🟢 va bene se | 🔴 allarme se |
|---|---|---|
| Prep. \|0_L⟩ | i 3 stabilizzatori Z misurano +1 → sindrome 000 | sindrome ≠ 000 → stato logico non nel code space |
| Prep. \|+_L⟩ | i 3 stabilizzatori X misurano +1 → sindrome 000 | idem lato X |
| Errori X | X su qubit i → sindrome Z-type = i in binario, biiettiva sui 7 | due qubit stessa sindrome → **STOP** |
| Errori Z | Z su qubit i → sindrome X-type biiettiva (dualità CSS) | asimmetria X/Z → bug stabilizzatori |
| Errori Y | Y=iXZ su qubit i → **entrambe** le sindromi accese | solo una accesa → Y non gestito |
| Correzione | dopo lookup+correzione, \|ψ_L⟩ recuperato (1 errore) | non recupera con 1 solo errore |
| Scaling | p_L ∝ p² a p piccolo (pendenza log-log ≈ 2) | pendenza ≈ 1 → il codice non corregge, copia soltanto |
| Pseudo-soglia | ∃ p_th sotto cui p_L < p (Steane conviene) | p_L > p ovunque → sotto la soglia utile |
| Data vs ancilla | errore su ancilla in syndrome extraction può dare sindrome errata → **dichiararlo** (non FT) | spacciarlo per fault-tolerant → overclaiming |

> Nota anti-overclaiming (doc §9.4 + §13.3): Steane qui corregge 1 errore arbitrario **assumendo
> al più 1 guasto nel blocco**. La syndrome extraction non è fault-tolerant: va scritto nel testo.

## M7 — Surface code (Stim + PyMatching)

**Flag decisivo**: le curve p vs p_L per d=3,5,7 devono **incrociarsi** attorno a una soglia
p_th. È la firma del comportamento a soglia (doc §10.3, "threshold-like behaviour").

| Controllo | 🟢 va bene se | 🔴 allarme se |
|---|---|---|
| Sanity p=0 | p_L ≈ 0 per ogni d | p_L > 0 a rumore nullo → bug decoder |
| Sotto soglia (p<p_th) | d ↑ ⟹ p_L ↓ (soppressione esponenziale in d) | d ↑ ⟹ p_L ↑ → matching/DEM sbagliato |
| Sopra soglia (p>p_th) | d ↑ ⟹ p_L ↑ (la ridondanza peggiora) | comportamento invertito |
| Soglia | incrocio delle curve a p_th ≈ 0.5–1% (ordine atteso) | nessun incrocio → noise model o rounds errati |
| Simmetria X/Z | memory_X e memory_Z danno p_L confrontabili | forte asimmetria → bug su una base |
| Statistica | ≥10⁴ shot; barre d'errore che non coprono l'incrocio | p_L piccolo con pochi shot → CI enormi |
| Costo | d=7 decodifica in tempo sostenibile | esplode → fermarsi a d=5 (mitigazione doc) |

## M8 — Shor logico (la figura conclusiva)

**Flag decisivo**: il p_L* che porta P_success di Shor all'80% deve essere **raggiungibile** dal
surface code di M7 per qualche coppia (d, p) fisica. Se sì, l'arco si chiude: "servono qubit
logici a p_L*, ottenibili con surface code d=… a errore fisico p=…".

| Controllo | 🟢 va bene se | 🔴 allarme se |
|---|---|---|
| Sanity p_L=0 | P_success = valore ideale (≈100% per N=15) | < 100% a p_L=0 → bug iniezione logica |
| Monotonìa | P_success decresce al crescere di p_L | non-monotòna → seed/shot |
| Soglia 80% | ∃ p_L* con P_success(p_L*) = 0.80, ben definito | curva piatta → range p_L mal scelto |
| Chiusura arco | p_L* ≥ p_L(surface, d, p) per (d,p) sensati | p_L* irraggiungibile → dichiarare il gap onestamente |
| Figura finale | Shor fisico rumoroso vs Steane vs surface, coerente e leggibile | curve che si contraddicono → rivedere i livelli |

---

## Come usare i flag nel lavoro quotidiano

1. Esegui l'esperimento della milestone.
2. Controlla il **flag decisivo** del cruscotto: se 🔴, fermati — è inutile procedere.
3. Scorri la tabella di controlli: ogni 🔴 va risolto o **dichiarato** nel testo come limite.
4. Solo con flag decisivo 🟢 + statistica valida (seed/shot/CI) → riempi la sezione del capitolo
   e passa alla milestone successiva.
5. Report settimanale (doc App. B): elenca per ogni milestone toccata quali flag sono 🟢/🔴.
