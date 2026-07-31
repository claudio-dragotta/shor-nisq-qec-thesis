# M10 — Decodifica appresa vs MWPM sul surface code

Milestone aggiuntiva (2026-07-31), non prevista dal documento di indirizzo originario: chiude
il cerchio fra la prima fase sperimentale (il ML a valle **non** serve, Cap. 10) e la parte QEC,
verificando se lo stesso strumento applicato alla **sindrome** produca invece un guadagno.

È la gamba sperimentale del §12.7 della tesi e rende verificata l'affermazione del §6.3.4
("il modello apprenditivo sostituisce il decoder analitico"), che prima era solo un richiamo
alla letteratura.

## File

| File | Contenuto |
|---|---|
| `qec_neural_decoder.py` | E1 (confronto leale), E1b (scaling dati), E2 (rumore correlato), E3 (validatore) |
| `qec_hybrid_decoder.py` | E4 (decoder ibrido MWPM + rete, forma residuale) — importa dal precedente |
| `results_M10_neural_decoder_*.json` | risultati E1/E1b/E2/E3 |
| `results_M10_hybrid_*.json` | risultati E4, con test di McNemar |
| `run_M10.log`, `run_M10_hybrid.log` | log completi dei due run |

Figure prodotte da `figure_src/gen_qec_neural.py` → `file_latex/figure/qec_neural_{leale,crosstalk,flag,ibrido}.pdf`

## Come si esegue

```bash
source ~/quantum-env/bin/activate     # richiede scikit-learn oltre a stim+pymatching
python qec_neural_decoder.py --shots 400000 --shots-scaling 900000 --distances 3 5
python qec_hybrid_decoder.py  --shots 800000 --distances 3 5
```

Tempi indicativi sulla macchina di sviluppo (CPU, 22 core): ~34 min il primo, ~32 min il secondo.
Il costo è quasi interamente nell'addestramento della rete: il campionamento con Stim e la
decodifica MWPM sono dell'ordine dei centesimi di secondo.

## Il dataset non richiede infrastruttura

È già ciò che Stim produce per stimare `p_L`:

```python
det, obs = sampler.sample(shots, separate_observables=True)
#  X = det (detection events = sindrome)   y = obs (flip logico)
```

Decoder analitico e decoder appreso ricevono quindi **esattamente la stessa informazione**.

## Il modello di crosstalk

`with_crosstalk()` inserisce un `DEPOLARIZE2` correlato fra qubit **dati adiacenti** sulla
griglia, una volta per ciclo di sindrome. Non viola l'ipotesi di Pauli (che resta soddisfatta)
ma quella di **decomponibilità in archi** su cui il MWPM si fonda: un errore correlato accende
fino a quattro detector e nessun arco lo rappresenta. È il modello elementare della quarta
fonte di rumore del Cap. 5.

## Risultati in sintesi

| Esperimento | Esito |
|---|---|
| **E1** sostituzione, modello esatto | la rete **non** batte MWPM: 0/14 configurazioni; pareggia a d=3, perde a d=5 |
| **E1b** scaling dati (d=3, p=0.003) | 25k→0.50×, 50k→0.62×, 100k→0.67×, 300k→0.93×, 800k→1.02× (non significativo) |
| **E2** crosstalk | la rete vince a d=3 (1.14–1.19×); perde a d=5. **Il MWPM col DEM *reale* è il peggiore a d=3** |
| **E3** validatore | AUC 0.941 nel predire "MWPM ha sbagliato"; precision 0.859 segnalando lo 0.59% degli shot |
| **E4** ibrido | vince in **8/8** configurazioni con crosstalk (McNemar da 1e-3 a 1e-312): +18–21% a d=3, +1–3% a d=5 |

Enunciato che ne discende: *sostituire il decoder analitico non conviene; affiancarlo sì. Il
guadagno compare a due condizioni congiunte — il rumore esce dal modello del decoder, e la
taglia del codice resta alla portata del modello appreso.*

Osservazione inattesa (E2, d=3): fornire al matching il modello di rumore **esatto** lo rende
peggiore che fornirgli quello nominale sbagliato. Con rumore non graph-like la decomposizione
in archi introduce archi spurî, e il limite è la **struttura** del decoder, non la calibrazione.

## Note metodologiche

- **Soglia di ribaltamento di E4 scelta in validazione**, non sul test set: fra le candidate c'è
  "non ribaltare mai", quindi il criterio può sempre ricadere su MWPM puro. La garanzia vale
  sul criterio di validazione, non punto per punto sul test (a d=3, p_ct=0 l'ibrido è 0.14σ
  peggiore — rumore statistico).
- **McNemar invece della stima binomiale**: ibrido e MWPM differiscono *solo* sugli shot
  ribaltati, quindi le coppie discordanti coincidono con essi e il test appaiato è esatto.
  È molto più potente: con la stima non appaiata 6/10 configurazioni risultavano significative,
  con McNemar 8/8 fra quelle con crosstalk.
- **Seed** passato sia al campionatore Stim sia alla rete, deterministico per configurazione.

## Limiti dichiarati in tesi

Rete densa (128,64) di capacità modesta, scelta per continuità con lo strumento della prima
fase; distanze ≤ 5; un solo errore fisico sotto soglia (p=0.003); rumore correlato di tipo
Pauli. I risultati verificano un **principio**, non stimano il potenziale della decodifica
neurale allo stato dell'arte (che usa architetture ricorrenti e ~10⁷ campioni).
