# Piano d'azione — Revisione post-riunione relatore (luglio 2026)

> Il piano ha DUE parti. La fusione dei capitoli è solo la prima (l'iceberg visibile).
>
> **PARTE A — Ristrutturazione**: fondere i 4 capitoli sperimentali in uno solo che racconti
> *cosa abbiamo testato e perché*, dimostrando che l'uso dell'IA (classificatore ML) in quel modo
> e con quello scopo **non serve**: il componente attivo è la strategia TOP-4.
> **⚠ Questo capitolo NON è la conclusione della tesi**: è il capitolo-cerniera che chiude la
> prima campagna sperimentale e **motiva il nuovo algoritmo** (Parte B).
>
> **PARTE B — Il nuovo algoritmo**: progettare e implementare l'algoritmo che diventa il
> contributo conclusivo della tesi (direzione da fissare col prof — vedi Fase 6/7).

---

## Il messaggio della tesi cambia (da tenere a mente in OGNI modifica)

**Prima**: "un classificatore ML riduce le iterazioni di Shor da decine a ~3" (ipotesi ρ≫1 grazie al ML).
**Adesso**: "abbiamo testato il classificatore ML e l'ablazione dimostra che il guadagno (ρ=6.43 su UC1,
ρ=2.42 su UC2) è **interamente della ricerca multi-candidato TOP-4**; il ML è neutro (UC1) o dannoso (UC2)".
È un **risultato negativo consapevole e ben documentato** — scientificamente valido, va presentato come tale.

---

## FASE 0 — Preparazione (5 min)

- [ ] Commit/backup dello stato attuale del repo tesi (branch `pre-fusione` o commit su main)
- [ ] Decidere il **titolo del nuovo capitolo unico**. Proposta:
      *"Risultati Sperimentali: dal Classificatore ML alla Strategia TOP-K"*
      (alternativa più sobria: *"Risultati Sperimentali e Analisi Critica dei Metodi"*)
- [ ] ~~Decidere se serve un capitolo "Conclusioni" generale~~ **RISOLTO dalla Parte B**: la tesi
      non si chiude col capitolo fuso — dopo verranno i capitoli del nuovo algoritmo e le
      conclusioni vere. Il capitolo fuso si chiude con un ponte esplicito: "questo risultato
      negativo motiva l'approccio del Capitolo successivo".

---

## FASE 1 — Creare il nuovo capitolo unico (il grosso del lavoro)

Nuovo file: `file_latex/capitoli/RisultatiSperimentali.tex`
Fonti: `RisultatiMetodo1.tex` (195 r.) + `ConclusioniMetodo1.tex` (66 r.) +
`RisultatiMetodo2.tex` (190 r.) + `ConclusioniMetodo2.tex` (501 r.) ≈ 950 righe → target ~450–500 righe.

### Struttura proposta del capitolo (mappa sorgente → destinazione)

| § | Sezione nuova | Da dove viene | Note |
|---|---|---|---|
| .1 | **Setup sperimentale comune** | RisM1 §Setup + RisM2 §Setup | Unificare: use case, parametri, seed, K=30 |
| .2 | **Analisi del circuito e barriera di scalabilità (UC3/UC4)** | RisM1 §Circuito + §UC3 + §UC4 + ConM2 §Scalabilità | ⚠ oggi la scalabilità è raccontata **4 volte** — qui diventa UNA sezione sola (UnitaryGate O(4^k), P_surv, Beauregard come sviluppo futuro) |
| .3 | **Baseline: Metodo 1 (TOP-1)** | RisM1 §UC1 + §UC2 + §Analisi + ConM1 (tutto) | ConM1 si riduce a: paragrafo "limiti" (spreco istogramma, alta varianza, costo shot) che motiva il passo successivo. Tagliare le ripetizioni delle stesse tabelle |
| .4 | **Cosa abbiamo testato e perché: il classificatore ML (Metodo 2)** | RisM2 §Architettura + §Dataset + §Selezione + §Valutazione | Sezione chiave per il prof: dichiarare ESPLICITAMENTE l'ipotesi (il ML filtra le iterazioni inutili) e il disegno sperimentale che la mette alla prova. F1/AUC restano: dimostrano che il classificatore "funziona" come classificatore, ma... |
| .5 | **Confronto e ablazione: il ML non serve** | RisM2 §Risultati UC + §Confronto + ConM2 §Risultati | ⚠ la tabella ablazione (tab:riepilogo_rho / tab:rho_concl) è **duplicata identica** — tenerne UNA. Qui il risultato negativo: UC1 p=0.849 (ML neutro), UC2 ML dannoso (ρ 0.73 vs 2.42) |
| .6 | **Campagna parametrica su M_TOP4** | ConM2 §Parametri (sweep K, ε2q, shots, T1/T2, ε1q, p_ro) | ⚠ ConM2 racconta ogni sweep DUE volte (sezione sweep + sezione "Previsioni/Scoperte"): fondere nel formato previsione→osservato→perché, una volta per parametro |
| .7 | **Confronto con ZNE** | ConM2 §ZNE | Quasi invariato, è già asciutto |
| .8 | **Discussione e posizionamento** | ConM2 §Validità + §M_TOP4 nel contesto mitigazione + RisM2 §Discussione | Sintesi del contributo (duplice: TOP-4 efficace + ablazione che smonta il ML), tabella posizionamento strategie, riproducibilità |

### Regole di fusione

- **Ogni dato numerico compare UNA volta** (oggi ρ=6.435 è ripetuto ~8 volte tra i 4 capitoli).
- Mantenere le label di sezione esistenti dove possibile (`sec:setup_m1`, `subsec:sweep_secondari`,
  ecc.) così i `\ref` interni non si rompono.
- Le figure restano tutte (fig_istogrammi_qpe, fig_roc_curve, fig_iterazioni_m1_m2, circuiti N21).
- Stile invariato: `onehalfspace`, tabelle `[H]`, aggancio esplicito al capitolo precedente in apertura.

---

## FASE 2 — Aggiornare main.tex

- [ ] Rimuovere i 4 `\chapter{...}` + `\input{...}` (righe 145–162 di `main.tex`)
- [ ] Aggiungere il nuovo capitolo dopo `Sviluppo`:
  ```latex
  \chapter{<titolo scelto>}
  \label{chap:risultati}
  \label{chap:risultati1}   % alias retro-compatibilità
  \label{chap:risultati2}
  \label{chap:conclusioni1}
  \label{chap:conclusioni2}
  \input{capitoli/RisultatiSperimentali}
  ```
  Gli alias-label (stesso trucco già usato per `chap:obiettivi`/`chap:specifiche`) fanno sì che
  TUTTI i riferimenti esterni continuino a compilare puntando al capitolo giusto — poi si
  ripuliscono in Fase 3.
- [ ] Se scelto: rinominare `\chapter{Sviluppi Futuri}` → `Conclusioni e Sviluppi Futuri`
- [ ] NON cancellare i 4 vecchi file .tex subito: commentarli/spostarli solo a compilazione verificata

## FASE 3 — Sistemare riferimenti e narrazione negli altri capitoli

Riferimenti da aggiornare (grep già fatto, file → cosa toccare):

- [ ] `Introduzione.tex` (righe ~205–240): sezione **Struttura della Tesi** (`% SYNC-STRUTTURA`):
      "quattordici capitoli" → **undici**; i 4 paragrafi dei capitoli fusi → 1 paragrafo
- [ ] `Introduzione.tex` (parte iniziale): verificare che l'annuncio del contributo rifletta il
      risultato negativo (ablazione), non "il ML riduce le iterazioni"
- [ ] `ObiettiviPianoSperimentale.tex` r.251: `\ref{chap:conclusioni2}` → nuovo capitolo; inoltre
      **rivedere la formulazione delle ipotesi** (M̄₂≈3, ρ≫1): vanno mantenute come ipotesi di
      partenza ma con nota che il piano sperimentale include l'ablazione per isolare il contributo ML
- [ ] `StrategieAntiRumore.tex` r.40, 111, 115: refs a `chap:conclusioni2` → nuovo capitolo
- [ ] `Metodologia.tex` r.84, 93, 145: refs; r.93 dice "dal 76.7% (Metodo 2)" — refuso da correggere in "M1"
- [ ] `Sviluppo.tex` r.3, 223: refs ai capitoli risultati
- [ ] `SviluppiFuturi.tex`: la sezione "evoluzione ML" va riorientata (il futuro non è "migliorare il
      classificatore" ma: capire *quando* un filtro appreso servirebbe, TOP-K adattivo, Beauregard/UC3-UC4)
- [ ] `RisultatiMetodo1.tex` r.3: il richiamo interno a `chap:risultati2` sparisce con la fusione (stesso capitolo)

## FASE 4 — Aggiornare documentazione di progetto (regola standing del CLAUDE.md tesi)

- [ ] `CLAUDE.md`: tabella "Struttura della tesi" 14 → 11 capitoli; sezione "Di cosa parla questa
      tesi" va riscritta (l'obiettivo dichiarato è ancora "dimostrare che un classificatore ML può
      ridurre le iterazioni" — ora è il contrario)
- [ ] `diario_relatore.md`: già aggiornato con la riunione 2026-07-02 ✅

## FASE 5 — Verifica

- [ ] Compilare: `pdflatex main && biber main && pdflatex main ×2` — zero warning "undefined reference"
- [ ] Controllare indice: niente capitoli fantasma, numerazione figure/tabelle coerente
- [ ] **Conta pagine**: il prof vuole 120–150 pagine di capitoli; la fusione ne toglie ~15–20.
      Se si scende sotto 120, segnalarlo: le "altre cose" del prof (Fase 6) potrebbero ricolmare
- [ ] Rileggere il nuovo capitolo da cima a fondo: il filo deve essere
      *baseline → ipotesi ML → test → ablazione → il ML non serve → cosa serve davvero (TOP-4) → quanto è robusto*

---

# PARTE B — Il nuovo algoritmo (il vero contributo conclusivo della tesi)

> Il capitolo fuso della Parte A dice "il ML usato come filtro a posteriori non serve".
> La tesi deve chiudersi con una proposta costruttiva: **il nuovo algoritmo**.
> La direzione esatta va fissata con il prof; le indicazioni del 2026-06-04 (diario) sono il
> punto di partenza più probabile.

## FASE 6 — Definire il problema e la direzione (BLOCCANTE: serve l'input del prof)

- [ ] **Annotare l'elenco esatto delle richieste del prof** (riportarlo nel diario + qui)
- [ ] Scegliere la direzione dell'algoritmo. Candidati coerenti con la riunione 2026-06-04:
  1. **Predizione dell'impatto degli errori** (il "Metodo 3"): ML che prevede — prima o durante
     l'esecuzione — se un errore sarà impattante sul risultato del circuito di Shor
     (feature: posizione del gate, profondità, qubit coinvolti). È l'uso *diverso* dell'IA:
     non filtro a posteriori sull'istogramma, ma predizione strutturale a priori.
     → si aggancia perfettamente al risultato negativo della Parte A.
  2. **Caratterizzazione dell'impatto**: metrica errore alto/basso impatto tramite fault-injection
     (inietti un errore in un punto preciso del circuito, misuri quanto degrada l'output).
     È il prerequisito sperimentale del punto 1 (genera il dataset di training).
  3. **TOP-K adattivo / criterio di stop intelligente**: evoluzione del componente che ha
     davvero funzionato (K scelto dinamicamente dalla forma dell'istogramma).
  4. **Scalabilità con Beauregard** (UC3/UC4 con HCP/IBM Quantum, credenziali promesse dal prof).
- [ ] Definire l'ipotesi quantitativa verificabile (equivalente del vecchio "ρ≫1") e i criteri
      di successo PRIMA di implementare — errore da non ripetere: stavolta l'ablazione va
      progettata dall'inizio, non aggiunta dopo.

## FASE 7 — Design e implementazione

- [ ] Design sperimentale: use case, dataset, baseline di confronto, test statistici (riusare
      l'infrastruttura di `experiments/`: shor_core, noise model, mwu_analysis)
- [ ] Implementazione in `experiments/` (WSL, come per M1/M2; eventualmente HCP)
- [ ] Esperimenti + raccolta risultati (JSON come le campagne precedenti)

## FASE 8 — Scrittura dei capitoli finali

- [ ] Nuovo capitolo metodologico/implementativo per l'algoritmo (o estensione di Metodologia/Sviluppo)
- [ ] Nuovo capitolo Risultati dell'algoritmo
- [ ] **Conclusioni generali della tesi** (che ora hanno un arco completo: baseline → ML bocciato
      dall'ablazione → nuovo algoritmo → risultati) + aggiornare Sviluppi Futuri
- [ ] Sync struttura: Introduzione (SYNC-STRUTTURA), CLAUDE.md, conta pagine 120–150

---

## Ordine di esecuzione consigliato

**Parte A** (si può fare subito, non dipende dal prof):
1. Fase 0 (backup + scelta titolo) → 2. Fase 1 (nuovo capitolo) → 3. Fase 2 (main.tex) →
4. compilazione di prova → 5. Fase 3 (refs + narrazione) → 6. Fase 4 (docs) → 7. Fase 5 (verifica).

**Parte B** (parte appena c'è la direzione del prof — la Fase 6 si può preparare in parallelo
alla Parte A raccogliendo le domande da fargli):
8. Fase 6 (problema+ipotesi) → 9. Fase 7 (implementazione+esperimenti) → 10. Fase 8 (capitoli finali).

Stima: nella Parte A, la Fase 1 è ~70% dell'effort (il resto è meccanico, grep alla mano:
`chap:risultati1|chap:risultati2|chap:conclusioni1|chap:conclusioni2`).
La Parte B è il lavoro grosso dei prossimi mesi: implementazione + esperimenti + 2-3 capitoli nuovi.
