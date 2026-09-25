# M16 — Gross code in code-capacity (esplorativo)

Prima verifica numerica del Gross code [[144,12,12]] (Bravyi et al., *Nature* 627, 2024),
citato nella tesi come riferimento qLDPC, con la libreria `ldpc` già usata in M10/E7.

**Stato: esplorativo.** Non è integrato nella tesi e va discusso col relatore. Il diario
di lavoro, con tutte le corse e le decisioni, è in `REGISTRO_M16.md` (privato).

## Modello

- errori X indipendenti con probabilità `q` sui qubit di dato; sindromi perfette, un ciclo;
- Gross code: bivariate bicycle `l=12, m=6, A = x^3 + y + y^2, B = y^3 + x + x^2`;
- riferimento: surface code ruotato `d = 3…13`, stesso rumore;
- confronto a parità di 12 qubit logici: un blocco Gross contro 12 patch indipendenti,
  `P_blocco = 1 − (1 − p_L)^12`.

**Decoder di riferimento.** Gross code: BP+OSD con BP *min-sum*, fattore di scala 0,625,
100 iterazioni, `osd_cs` ordine 10. Surface code: MWPM (PyMatching); BP+OSD con lo stesso
min-sum dà gli stessi valori entro l'incertezza.

La scelta del decoder conta: con BP *product-sum* il Gross code risulta peggiore del
33–72% a `q = 1–3%`; con il min-sum senza fattore di scala le curve diventano non monotone.

**Limite interpretativo:** confronto fra codici nello stesso modello code-capacity. Non è
confrontabile con M7 (livello di circuito) né con i numeri IBM a livello di circuito, e
non dice nulla sui costi di estrazione delle sindromi o sulla connettività richiesta.

## Esecuzione

```bash
cd Extra/experiments/M16_qldpc_gross
PY=/home/claudio/quantum-env/bin/python
$PY verifica_distanza.py --distances 3 5 7
$PY gross_code_capacity.py --seed 42 --output-dir artifacts/v2_20260926   # corsa base
bash run_approfondimenti.sh      # basso rumore e sensibilità del decoder
bash run_approfondimenti_2.sh    # min-sum 0,625 e statistica del surface
bash run_approfondimenti_3.sh    # min-sum a basso rumore, sensibilità, surface BP+OSD
bash run_analisi_consolidata.sh  # confronto finale da input espliciti
```

## Controlli

- Gross code: `n = 144`, `k = 12`, rango 66 per `Hx` e `Hz`, controlli di peso 6;
  la distanza 12 è quella pubblicata, non verificata qui;
- surface code: distanza verificata per forza bruta per `d = 3, 5, 7`;
- nessuna correzione viola la sindrome in nessuna corsa;
- pendenza log–log del surface `d = 3`: 1,89, attesa 2;
- sensibilità del riferimento min-sum a 1000 iterazioni e OSD ordine 20: −3…−18%, entro
  il margine del 20% fissato in anticipo.

## Esito — `artifacts/v2_20260926/analysis_M16_consolidata_20260926_042019.json`

P(almeno uno dei 12 qubit logici errato); fra parentesi i qubit di dato:

| q | Gross (144) | 12×d=7 (588) | 12×d=9 (972) | 12×d=11 (1452) | 12×d=13 (2028) |
|---|---|---|---|---|---|
| 0,005 | 9,6·10⁻⁶ | 3,5·10⁻⁵ | 3,4·10⁻⁶ | 2,0·10⁻⁷ | < 1,2·10⁻⁷ |
| 0,01 | 9,8·10⁻⁵ | 5,0·10⁻⁴ | 6,8·10⁻⁵ | 1,2·10⁻⁵ | 1,6·10⁻⁶ |
| 0,02 | 7,6·10⁻⁴ | 7,3·10⁻³ | 2,2·10⁻³ | 6,0·10⁻⁴ | 1,9·10⁻⁴ |
| 0,03 | 3,1·10⁻³ | 3,1·10⁻² | 1,4·10⁻² | 5,7·10⁻³ | 2,8·10⁻³ |
| 0,04 | 1,0·10⁻² | 8,5·10⁻² | 4,8·10⁻² | 2,8·10⁻² | 1,5·10⁻² |
| 0,05 | 3,2·10⁻² | 1,8·10⁻¹ | 1,2·10⁻¹ | 8,0·10⁻² | 5,2·10⁻² |

Distanza del surface code che il blocco Gross eguaglia (IC 95% non sovrapposti):

| q | Gross migliore di | Gross peggiore di | qubit di dato risparmiati |
|---|---|---|---|
| 0,5–1% | d ≤ 7 | d ≥ 9 | 4–7× |
| 2% | d ≤ 9 | d ≥ 11 | 7–10× |
| 3% | d ≤ 11 | — (≈ d=13) | 10–14× |
| 4–6% | d ≤ 13 | — | > 14× |

Il vantaggio in qubit del Gross code è reale in tutto l'intervallo, ma dipende dal rumore:
cresce con `q` e si riduce a basso rumore, dove il codice non ha ancora raggiunto il
regime in cui domina la distanza 12.
