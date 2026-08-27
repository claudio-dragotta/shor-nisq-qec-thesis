# M10 — Decodifica appresa vs MWPM sul surface code

Milestone aggiuntiva (2026-07-31), non prevista dal documento di indirizzo originario: chiude
il cerchio fra la prima fase sperimentale (il ML a valle **non** serve, Cap. 7) e la parte QEC,
verificando se lo stesso strumento applicato alla **sindrome** produca invece un guadagno.

È la gamba sperimentale del §9.6 della tesi e dell'Appendice E.1.

> **Erratum 2026-08-19.** `propagazione_su_shor.json` è solo storico: trattava il
> fallimento di memoria/decodifica di M10 come se fosse la probabilità indipendente di un
> Pauli non-identità dopo ogni gate del proxy M8. Senza un mapping validato queste metriche
> non sono intercambiabili; l'entry point ora blocca esplicitamente la propagazione.

La campagna è cresciuta in tre ondate. Le prime quattro prove (E1–E4) stabiliscono il
risultato; le tre successive (E5–E7) lo attaccano dall'esterno; le ultime cinque (E8–E12,
2026-08-10) attaccano le *conclusioni delle precedenti*, e ne smentiscono due.

## File

| File | Esperimenti |
|---|---|
| `qec_neural_decoder.py` | **E1** confronto leale, **E1b** scaling dati, **E2** rumore correlato, **E3** validatore |
| `qec_hybrid_decoder.py` | **E4** decoder ibrido MWPM + rete, forma residuale — importa dal precedente |
| `generalizzazione.py` | **E5** il decoder è trasferibile fra profili di rumore? |
| `decoder_miscalibrato.py` | **E6** e se il modello del decoder fosse solo mal calibrato? |
| `confronto_bposd.py` | **E7** e se si scegliesse un decoder analitico migliore (BP+OSD)? |
| `residuo_su_bposd.py` | **E8** il residuo appreso sopra BP+OSD: i due guadagni si sommano? |
| `dimensione_vs_distanza.py` | **E9** incrocio 2×2: il fallimento a d=7 è della distanza o dei detector? |
| `pavimento_comune.py` | **E10** sei decoder sugli stessi campioni: esiste un pavimento comune? |
| `controllo_pavimento.py` | **E11** quel pavimento è del problema o del modello? |
| `auc_per_dimensione.py` | **E12** a 336 detector la rete è cieca o solo indecisa? |
| `propaga_su_shor.py` | guardrail: blocca la vecchia propagazione M10→M8 finché non esiste un mapping di metrica validato |

Risultati in `results_M10_*.json`, log completi in `run_M10_*.log`, uno per campagna.
Figure da `figure_src/gen_qec_neural.py` e `figure_src/gen_confronto_decoder.py`.

## Come si esegue

```bash
source ~/quantum-env/bin/activate     # richiede scikit-learn e ldpc oltre a stim+pymatching
python qec_neural_decoder.py  --shots 400000 --shots-scaling 900000 --distances 3 5
python qec_hybrid_decoder.py  --shots 800000 --distances 3 5
python confronto_bposd.py     --shots 200000 --distances 3 5
python residuo_su_bposd.py    --shots 800000 --distances 3      # poi --distances 5
python dimensione_vs_distanza.py --shots 800000
python pavimento_comune.py    --shots 800000 --distances 3
python controllo_pavimento.py --shots 800000
python auc_per_dimensione.py  --shots 800000
```

Tempi sulla macchina di sviluppo (CPU, 22 core): E1–E4 ~34 e ~32 min; E8 56 min a d=3 e
66 min a d=5; E9 8.6 min; E10 13.4 min; E11 18.2 min; E12 5.4 min.

Il costo è quasi interamente nell'**addestramento della rete** — campionamento Stim e
decodifica MWPM sono centesimi di secondo. L'eccezione è BP+OSD, che decodifica shot per
shot (la libreria `ldpc` non espone un'API batch): a d=5 su 8·10⁵ campioni costerebbe ~7 h in
un solo processo, per cui `residuo_su_bposd.py` distribuisce il ciclo su un pool di processi.
Ogni shot è indipendente, quindi la parallelizzazione non introduce alcuna approssimazione.

## Il dataset non richiede infrastruttura

```python
#  X = det (detection events = sindrome)   y = obs (flip logico)
det, obs = circuito.compile_detector_sampler().sample(shots, separate_observables=True)
```

## Il modello di crosstalk

Accoppiamento residuo fra qubit **dati adiacenti**: viola la decomponibilità in archi che il
MWPM assume, ma non l'ipotesi di Pauli. È precisamente la cecità *strutturale* che
l'apprendimento sfrutta — vedi E7 e la sezione "Enunciato" più sotto.

## Risultati in sintesi

### Prima ondata — il risultato

| Esperimento | Esito |
|---|---|
| **E1** sostituzione, modello esatto | la rete **non** batte MWPM: 0/14 configurazioni |
| **E1b** scaling dati (d=3) | 25k→0.50×, 100k→0.67×, 800k→1.02× (non significativo) |
| **E2** crosstalk | la rete vince a d=3 (1.14–1.19×); perde a d=5 |
| **E3** validatore | AUC 0.941 nel predire "MWPM ha sbagliato" |
| **E4** ibrido | vince in **8/8** configurazioni con crosstalk: +18–21% a d=3, +1–3% a d=5, **0% a d=7** |

### Seconda ondata — gli attacchi al risultato

| Esperimento | Esito |
|---|---|
| **E5** trasferibilità | il decoder regge il cambio di profilo di rumore senza riaddestramento |
| **E6** mis-calibrazione | perturbando i parametri fino a un ordine di grandezza, p_L varia dell'1–3%: la cecità che conta è **strutturale, non di calibrazione** |
| **E7** BP+OSD | decoder analitico migliore: +14.6% a d=3 e +33.9% a d=5 sul rumore nominale. Il suo guadagno **decresce** col crosstalk, quello dell'ibrido **cresce** |

### Terza ondata — gli attacchi alle conclusioni (2026-08-10)

| Esperimento | Esito |
|---|---|
| **E8** somma dei guadagni | **smentita**: il combinato eguaglia sempre il migliore dei due, mai il prodotto. Il residuo migliora BP+OSD in 1/5 configurazioni a d=5 |
| **E9** distanza o detector? | **il numero di detector**. A 336 il residuo si astiene a qualunque distanza e con fino a 1.9·10⁵ esempi; a 144 interviene anche a d=7 con tre volte meno esempi |
| **E10** pavimento comune | sotto crosstalk MWPM+residuo, BP+OSD+residuo e **la rete sola** atterrano entro l'1–2% sullo stesso p_L; senza crosstalk il pavimento non esiste (19.4% di dispersione) |
| **E11** il pavimento è del modello? | **no**: rete con 40× i parametri sul pavimento entro 0.8%, tabella empirica peggiore del 2–4%. Ma la tabella ha profondità 7–32 campioni per sindrome, quindi **non** stabilisce un limite informativo |
| **E12** cieca o indecisa? | **né l'una né l'altra**: AUC 0.57–0.77 a 336 detector, ma guadagno oracolo 1.0000 |

## Enunciato che ne discende

*Sostituire il decoder analitico non conviene; affiancarlo sì, ma solo dove il rumore esce
dalla **struttura** del suo modello.* Il guadagno richiede due condizioni congiunte:

1. **il rumore non è decomponibile** in archi del grafo (E2, E6, e il nullo sugli errori
   coerenti in M12 — una sovrarotazione su un singolo qubit resta decomponibile);
2. **la sindrome è stretta abbastanza** perché la rete la discrimini (E9, E12).

La seconda condizione ha ora un criterio quantitativo, ed è il risultato più utile della
campagna. Il ribaltamento è **simmetrico**: rovinare uno shot corretto costa quanto salvarne
uno sbagliato. Perché l'operazione sia in attivo serve dunque **precisione > 50% fra gli shot
ribaltati** — una soglia netta, non un ottimo graduale. L'AUC necessaria a raggiungerla
dipende dal tasso di base; l'AUC ottenuta decade con la larghezza della sindrome. Sotto il
punto critico il guadagno non degrada: vale **esattamente 1.000**.

Ne segue un criterio verificabile *prima* di costruire un'architettura alternativa
(convoluzionale o a grafo): misurarne l'AUC e controllare se supera la soglia al tasso di
base d'interesse.

Osservazione inattesa (E2, d=3): fornire al matching il modello di rumore **esatto** lo rende
peggiore che fornirgli quello nominale sbagliato. Con rumore non graph-like la decomposizione
in archi introduce archi spurî.

## Note metodologiche

- **Soglia di ribaltamento scelta in validazione**, mai sul test set: fra le candidate c'è
  "non ribaltare mai", quindi il criterio può sempre ricadere su MWPM puro. E12 mostra che
  questa astensione è **corretta e non conservativa**: la soglia oracolo, scelta sul test
  stesso, non guadagna nulla di più.
- **McNemar invece della stima binomiale**: ibrido e MWPM differiscono *solo* sugli shot
  ribaltati, quindi le coppie discordanti coincidono con essi e il test appaiato è esatto.
- **Bracci sugli stessi campioni** da E8 in poi. Le campagne precedenti usavano 8·10⁵ e
  2·10⁵ shot con seed diversi, e la variazione run-to-run (~1.3% su p_L) era dello stesso
  ordine degli scarti da misurare.
- **Ipotesi alternative dichiarate prima dell'esecuzione** in E8, E9, E11 e E12, ciascuna nel
  docstring del proprio script. In E8 l'ipotesi sfavorevole al risultato è quella confermata.
- **Seed** passato sia al campionatore Stim sia alla rete, deterministico per configurazione.

## Limiti dichiarati in tesi

Rete densa (128,64) di capacità modesta, scelta per continuità con lo strumento della prima
fase — E11 verifica che il limite non dipenda da questa scelta; distanze ≤ 7; un solo errore
fisico sotto soglia (p=0.003); rumore correlato di tipo Pauli. I risultati verificano un
**principio**, non stimano il potenziale della decodifica neurale allo stato dell'arte.

Un limite metodologico va aggiunto perché nessuno degli esperimenti qui elencati lo copre:
tutti i controlli usano la **medesima pipeline** che ha prodotto i risultati che verificano.
Un errore sistematico in `build_circuit`, `with_crosstalk` o `train_nn` resterebbe invisibile
a tutti. L'unica verifica esterna disponibile è il confronto della soglia del surface code
con la letteratura (§9.4), ed è qualitativo.
