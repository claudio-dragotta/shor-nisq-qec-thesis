# M16 — Gross code e codici bivariate bicycle in code-capacity (esplorativo)

Verifica numerica del Gross code [[144,12,12]] e della sua famiglia di codici bivariate
bicycle (Bravyi et al., *Nature* 627, 2024), citati nella tesi come riferimento qLDPC,
con la libreria `ldpc` già usata in M10/E7.

**Stato: esplorativo.** Non è integrato nella tesi e va discusso col relatore. Il diario
di lavoro, con tutte le corse, i criteri fissati in anticipo e le decisioni, è in
`REGISTRO_M16.md` (privato).

## Modello

- errori X indipendenti con probabilità `q` sui qubit di dato; sindromi perfette, un ciclo;
- codici BB: polinomi in `codici_bb.py`; Gross code `l=12, m=6, A = x^3+y+y^2, B = y^3+x+x^2`;
- riferimento: surface code ruotato `d = 3…13`, stesso rumore, MWPM (PyMatching);
- confronto a parità di qubit logici: un blocco BB con `k` logici contro `k` patch di
  surface indipendenti, `P_blocco = 1 − (1 − p_L)^k`; "migliore/peggiore" solo con IC 95%
  non sovrapposti.

**Decoder definitivo dei codici BB:** BP+OSD con BP *min-sum*, schedulazione **serial**,
fattore di scala 0,625, 100 iterazioni, OSD-CS ordine 10. Scelto con due sweep di 12
varianti ciascuno sugli stessi shot (test 1 e 1b) e confermato su semi indipendenti
(test 4). Sul surface code BP+OSD e MWPM coincidono entro l'incertezza.

**Il decoder conta quanto il codice.** Con la schedulazione parallela usata nelle prime
corse il Gross code falliva già con 3 errori e risultava fino a ~70× peggiore a q = 1%;
con il product-sum ancora peggio; con il min-sum parallelo l'esito dipende in modo
erratico dal fattore di scala. Qualunque numero sui codici BB va accompagnato dalla
configurazione del decoder.

**Limite interpretativo:** confronto fra codici nello stesso modello code-capacity. Non è
confrontabile con M7 (livello di circuito) né con i numeri IBM a livello di circuito, e
non dice nulla sui costi di estrazione delle sindromi o sulla connettività richiesta.

## Esecuzione

```bash
cd Extra/experiments/M16_qldpc_gross
PY=/home/claudio/quantum-env/bin/python
$PY verifica_distanza.py --distances 3 5 7
$PY gross_code_capacity.py --seed 42 --output-dir artifacts/v2_20260926   # corsa base
bash run_approfondimenti.sh          # basso rumore e prime sensibilità del decoder
bash run_approfondimenti_2.sh        # min-sum 0,625 e statistica del surface
bash run_approfondimenti_3.sh        # min-sum a basso rumore, surface con BP+OSD
bash run_analisi_consolidata.sh      # confronto con il decoder min-sum parallelo (storico)
bash run_test_1_4.sh 1               # test 1: sweep del decoder
$PY sweep_decoder.py --seed 42 --giro-1b --riferimento serial \
    --q-list 0.01 0.02 0.03 0.04 --shots-scala 2 --etichetta giro1b \
    --output-dir artifacts/v2_20260926                         # test 1b
VARIANTE=serial bash run_test_1_4.sh 2 3 4   # fallimenti, distanza, famiglia
bash run_analisi_consolidata_serial.sh       # confronto finale col decoder definitivo
```

## Controlli

- codici BB: `n` e `k` attesi per tutti e cinque; **distanza pubblicata ritrovata per tutti**
  (6, 10, 10, 12, 18) con la ricerca a insieme d'informazione, logici verificati;
- surface code: distanza verificata per forza bruta (d = 3, 5, 7) e ritrovata dalla
  ricerca (d = 5, 7, 9);
- nessuna correzione viola la sindrome in nessuna corsa;
- decoder saturo: nessuna variante del giro 1b migliora serial di oltre il 10%;
- replica: il Gross code con semi nuovi (test 4) concorda con il test 1b entro il 10%;
- il campionamento a peso fissato (test 2) ricostruisce p_L(q) entro pochi punti
  percentuali dalle simulazioni dirette.

## Esito — decoder definitivo (`analysis_M16_consolidata_serial_20260926_120628.json`)

P(almeno uno dei 12 qubit logici errato); fra parentesi i qubit di dato:

| q | Gross (144) | 12×d=9 (972) | 12×d=11 (1452) | 12×d=13 (2028) |
|---|---|---|---|---|
| 0,005 | 0 su 10⁷ (< 3·10⁻⁷) | 3,4·10⁻⁶ | 2,0·10⁻⁷ | < 1,2·10⁻⁷ |
| 0,01 | 1,1·10⁻⁶ | 6,8·10⁻⁵ | 1,2·10⁻⁵ | 1,6·10⁻⁶ |
| 0,02 | 8,2·10⁻⁵ | 2,2·10⁻³ | 6,0·10⁻⁴ | 1,9·10⁻⁴ |
| 0,03 | 1,0·10⁻³ | 1,4·10⁻² | 5,7·10⁻³ | 2,8·10⁻³ |
| 0,04 | 7,4·10⁻³ | 4,8·10⁻² | 2,8·10⁻² | 1,5·10⁻² |
| 0,05 | 2,8·10⁻² | 1,2·10⁻¹ | 8,0·10⁻² | 5,2·10⁻² |

- da q = 2% in su il Gross code batte tutte le patch fino a d = 13: **oltre 14× meno qubit
  di dato**;
- a q = 1% batte fino a d = 11 ed è compatibile con d = 13;
- a q = 0,5% nessun fallimento su 10⁷ shot: batte fino a d = 9, oltre non si decide.

Perché il decoder cambia tutto (test 2, campionamento a peso fissato): il decoder serial
non fallisce mai sotto i 6 errori, come un decoder a distanza piena (⌊(12−1)/2⌋ = 5);
quello parallelo falliva già con 3.

### Famiglia BB (test 4, `results_M16_test4_famiglia_bb_20260926_120439.json`)

| Codice | Qubit di dato | Eguaglia il surface (k patch) a distanza | Risparmio |
|---|---|---|---|
| [[72,12,6]] | 72 | fra 5 e 7 | ~4× |
| [[90,8,10]] | 90 | fra 9 e 13 | ~7× |
| [[108,8,10]] | 108 | oltre 11; oltre 13 da q = 5% | ~9× |
| [[144,12,12]] | 144 | oltre 13 da q = 2% | > 14× |
| [[288,12,18]] | 288 | oltre 13 da q = 1% (0 fallimenti su 10⁷ a 1%) | > 7×, limite del confronto |

Il vantaggio vale per tutta la famiglia e cresce con la dimensione del codice. A parità
di `k` e `d`, [[108,8,10]] fa meglio di [[90,8,10]]: non conta solo la distanza.

## Storico

Il primo confronto consolidato (`analysis_M16_consolidata_20260926_042019.json`) usava il
min-sum con schedulazione parallela e concludeva che a basso rumore il Gross code
eguagliava solo il surface d = 7–9. Quella conclusione era un artefatto del decoder ed è
superata; il file resta come traccia.
