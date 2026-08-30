# M15 — QFT approssimata e resa in fattori

Aperto il 30 agosto 2026, dopo la chiamata col relatore del 29.

## La domanda

Approssimare la trasformata di Fourier — scartare le rotazioni controllate sotto una soglia
di angolo — toglie porte e quindi rumore, ma peggiora il circuito ideale. Sotto rumore i due
effetti competono, e l'ottimo non è necessariamente la QFT piena.

M15 misura dove sta l'ottimo **sulla resa in fattori**, non sulla fedeltà.

## Perché proprio questa domanda

Viene da due risultati che la tesi ha già:

1. **M11** ha mostrato che il punteggio di fedeltà è un cattivo predittore del successo
   (Spearman `-0,184`, IC `[-0,456; 0,124]`). Ottimizzare la fedeltà non è la stessa cosa
   che ottimizzare ciò che serve a Shor: è la leva rimasta libera.
2. **La correzione su `P_surv` del 7 agosto** ha mostrato che le `cp` della QFT inversa
   sopravvivono alla traspilazione e pesano più delle `cx` — su UC1 sono 52 contro 114. Il
   costo si concentra dove la QFT mette le rotazioni.

## Le due leve

| leva | cosa tronca | dove agisce |
|---|---|---|
| `k_qpe` | rotazioni della QFT inversa finale del QPE | N=15 e N=21 |
| `k_arith` | rotazioni delle QFT dentro gli addizionatori di Beauregard | solo N=21 |

Si tengono le `cp` con distanza `j − m ≤ k`. A `n_count = 8` le coppie per distanza sono
7, 6, 5, 4, 3, 2, 1, e l'ultima rotazione vale `π/128 ≈ 0,025 rad` al prezzo di due CX come
tutte le altre.

Per N=15 il moltiplicatore è `c_amod15`, che non contiene QFT: agisce la sola `k_qpe`.
**È in N=21 che vive il meccanismo**, perché la diagnostica di compilazione conta 11.436
`cp` contro 3.406 `cx`, e quelle `cp` stanno negli addizionatori.

Una terza leva, l'eliminazione dei quattro SWAP di inversione dei bit, è implementata e dà
**esattamente zero**: i due bracci producono numeri identici cifra per cifra, perché il
transpiler assorbe già la permutazione nel layout. Documentata come esito negativo.

> **Attenzione, errore corretto il 30/08/2026.** La prima implementazione toglieva i SWAP e
> rinominava i bit classici alla misura. I SWAP stanno però *prima* della cascata, non dopo:
> la scorciatoia produceva un circuito diverso, con `P_success` ideale `0,4542` e picchi in
> 0/255/128 invece di 0/64/128/192. La forma corretta è per coniugazione — detta `R`
> l'inversione e `C` la cascata, da `C R = R (R C R)` segue che si applica la cascata sugli
> indici invertiti e la `R` finale si assorbe nella misura. Gli output della versione
> sbagliata sono in `artifacts/_superseded_swap_bug/`.

## Limite dichiarato su N=15

Con `r = 4` i picchi cadono su `{0, 64, 128, 192}`, cioè fasi `0, ¼, ½, ¾`, rappresentabili
esattamente con **due bit**. L'approssimazione può quindi non costare nulla fino a `k` molto
piccolo, e **un esito positivo su N=15 è debole per costruzione**.

È la stessa degenerazione che ha reso poco discriminante M13. N=21, con `r = 6` e fasi `j/6`
non rappresentabili esattamente, è il test vero.

## Criterio preregistrato

La configurazione si sceglie sui batch di **train** e si riporta sui batch di **holdout**,
che sono disgiunti. Scegliere il massimo su tutte le stime e poi riportarlo sulle stesse
stime è winner's curse — la stessa obiezione che M11 si era posta su 60 layout.

**Esito primario**: `P_success` su holdout della configurazione selezionata sul train,
contro `P_success` su holdout della QFT piena, sugli stessi batch e con gli stessi semi.
Differenza con IC di Newcombe al 95%, la stessa convenzione del contrasto primario di M13.

## Il circuito canonico non viene modificato

`shor_core.py` e `beauregard.py` hanno prodotto gli artefatti v2 e il loro SHA è vincolato
da `CLAUDE.md`. Questo script **non li tocca**: riassembla il circuito dai loro mattoni e
applica l'approssimazione localmente. Le QFT interne di Beauregard sono sostituite da un
context manager che ripristina sempre l'originale, anche in caso di eccezione.

Il controllo di correttezza in testa a ogni esecuzione verifica che a grado pieno il
circuito ricostruito abbia lo SHA canonico
`c7f4cf3bc1735dce9d5b56d8e09686ee4ab43cabead65e734ea23d5a50f4ba2c`. **Verificato**: la
ricostruzione è bit-per-bit identica. Senza questa identità i confronti non sarebbero
interpretabili, e lo script si interrompe.

## Comandi

Ambiente canonico, da PowerShell `wsl -d Ubuntu`:

```bash
cd Extra/experiments/M15_qft_topologia
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/v1_20260830

# N=15 -- pilota
$PY qft_approssimata.py --N 15 --shots 8192 --batches 8 \
  --holdout-fraction 0.5 --seed 42 --output-dir "$RUN"

# solo conteggi porte e profondita', senza simulare (economico)
$PY qft_approssimata.py --N 21 --solo-struttura --output-dir "$RUN"

# N=21 -- test discriminante; dimensionare gli shot, vedi Costi
$PY qft_approssimata.py --N 21 --shots 1024 --batches 8 \
  --k-arith-max 3 --seed 42 --output-dir "$RUN"
```

## Costi

Il costo di simulazione di N=21 è misurato e va rispettato: **16,8 s/shot**, cioè circa
4,8 ore per 1024 shot (sessione del 7 agosto, macchina dedicata). La griglia completa a
`k_arith_max=4` conta 70 configurazioni: non è eseguibile a shot pieni.

Strategia consigliata:

1. `--solo-struttura` su N=21 per la riduzione di porte, che è **gratuita** e già
   informativa;
2. sulla base di quella, restringere la griglia a poche configurazioni e simulare solo
   quelle, con un budget di shot dichiarato.

## Risultati — N=15 (pilota)

`8192` shot, 8 batch (4 train / 4 holdout), seed 42, layout fisso su snapshot
FakeSherbrooke. Il braccio senza SWAP dà numeri identici cifra per cifra ed è omesso.

| `k_qpe` | 1 | 2 | 3 | 4 | 5 | 6 | 7 (piena) |
|---|---|---|---|---|---|---|---|
| ECR | 279 | 305 | 328 | 360 | 365 | 360 | 362 |
| profondità | 1141 | 1242 | 1330 | 1414 | 1391 | 1306 | 1351 |
| `P_holdout` | **0,6279** | 0,5422 | 0,5210 | 0,4771 | 0,4607 | 0,4749 | 0,4792 |
| `P_success` ideale | 0,7505 | 0,7505 | 0,7505 | — | — | — | 0,7505 |

**Esito primario**: la configurazione selezionata sul train è `k_qpe = 1`, e sull'holdout
rende `0,6279` contro `0,4792` della QFT piena. Differenza **+0,1487**, IC di Newcombe 95%
**`[+0,1273; +0,1699]`**, con **83 porte a due qubit in meno** (279 contro 362).

### Il risultato è vinto per costruzione, e va detto

La riga delle distribuzioni ideali è la più importante: **`P_success` ideale vale `0,7505`
per ogni `k`, fino a `k=1`**, con i picchi esatti in 0/64/128/192.

Su N=15 troncare la QFT non costa **nulla** in termini ideali, perché con `r=4` le fasi
sono `0, ¼, ½, ¾` ed esatte in due bit: le rotazioni fini non trasportano informazione.
Tutto il guadagno sotto rumore viene quindi dalle sole porte risparmiate, e il confronto è
sbilanciato in partenza.

Non è un difetto del disegno: era **preregistrato** in questo README e nel docstring prima
di eseguire. Ma è la ragione per cui il numero da citare non è questo.

### Esito negativo, valido

Eliminare i quattro SWAP di inversione dei bit dà **esattamente zero**: i due bracci
producono numeri identici, perché il transpiler assorbe già la permutazione nel layout.
È il tipo di ottimizzazione «ovvia» che conviene misurare prima di proporla.

## Manca il test vero

Su N=21, con `r=6`, le fasi valgono `j/6` e non sono rappresentabili esattamente: le
rotazioni fini servono, il compromesso è reale e l'ottimo non è banale. **È lì che il
meccanismo si misura davvero**, ed è anche l'unica istanza in cui agisce `k_arith`, cioè
la leva sulle QFT degli addizionatori dove stanno le 11.436 `cp`.

## File

- `qft_approssimata.py` — generatore e analisi, entrambe le istanze
- `artifacts/v1_20260830/` — risultati, `schema_version 2.0`
- `artifacts/v1_20260830/logs/` — stdout e stderr delle esecuzioni

## Stato

- [x] Script, controllo di correttezza contro lo SHA canonico
- [x] Campagna rumorosa N=15 (pilota)

- [ ] Sweep strutturale N=21
- [ ] Campagna rumorosa N=21, griglia ristretta

## Avvertenza sul perimetro

Nella chiamata del 29 agosto il relatore ha indicato di **non** eseguire un esperimento su
questa direzione (*«sono due paragrafi»*, *«non ci pensare proprio»*), mentre nei messaggi
WhatsApp successivi ha scritto che *«servirebbero benchmark comparativi»*. La contraddizione
è agli atti nel diario e va sciolta con lui.

M15 esiste perché il numero serva comunque a scrivere conclusioni e sviluppi futuri in forma
difendibile. **Non va promosso a capitolo senza una decisione esplicita del relatore.**
