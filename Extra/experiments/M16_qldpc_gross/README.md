# M16 — Gross code in code-capacity (esplorativo)

Prima verifica numerica del Gross code [[144,12,12]] (Bravyi et al., *Nature* 627, 2024),
citato nella tesi come riferimento qLDPC, con lo stesso decoder BP+OSD usato in M10/E7.

**Stato: esplorativo.** Non è ancora integrato nella tesi e va discusso col relatore.

## Modello

- errori X indipendenti con probabilità `q` sui qubit di dato; sindromi perfette, un ciclo;
- Gross code: bivariate bicycle `l=12, m=6, A = x^3 + y + y^2, B = y^3 + x + x^2`;
- riferimento: surface code ruotato `d = 3…13`, stesso rumore, MWPM (PyMatching) e BP+OSD;
- confronto a parità di 12 qubit logici: un blocco Gross contro 12 patch indipendenti,
  `P_blocco = 1 − (1 − p_L)^12`.

**Limite interpretativo:** è un confronto fra codici nello stesso modello code-capacity.
Non è confrontabile con M7 (livello di circuito) né con i numeri IBM a livello di circuito,
e non dice nulla sui costi di estrazione delle sindromi o sulla connettività richiesta.

## Esecuzione canonica

```bash
cd Extra/experiments/M16_qldpc_gross
PY=/home/claudio/quantum-env/bin/python
$PY verifica_distanza.py --distances 3 5 7
$PY gross_code_capacity.py --seed 42 --output-dir artifacts/v2_20260926
```

## Artefatti

| File | Contenuto |
|---|---|
| `artifacts/v2_20260926/results_M16_gross_code_capacity_20260926_031028.json` | risultati, schema 2.0, manifest, seed 42 |
| `run_M16_gross_code_capacity.log` | output della corsa |

## Controlli

- Gross code: `n = 144`, `k = 12`, rango 66 per `Hx` e `Hz`, controlli di peso 6;
- surface code: distanza verificata per forza bruta per `d = 3, 5, 7`;
- nessuna correzione viola la sindrome;
- pendenza log–log del surface `d = 3`: 1,89, attesa 2 = `(d+1)/2`.

## Esito (seed 42, fino a 200 000 shot per punto)

P(almeno uno dei 12 qubit logici errato):

| q | Gross (144 dati) | 12 × d=9 (972) | 12 × d=11 (1452) | 12 × d=13 (2028) |
|---|---|---|---|---|
| 0,01 | 3,05·10⁻⁴ | 6,0·10⁻⁵ | 0 su 200 000 | 0 su 200 000 |
| 0,02 | 1,54·10⁻³ | 2,16·10⁻³ | 7,2·10⁻⁴ | 1,8·10⁻⁴ |
| 0,03 | 4,56·10⁻³ | 1,40·10⁻² | 5,69·10⁻³ | 2,76·10⁻³ |
| 0,04 | 1,30·10⁻² | 4,78·10⁻² | 2,83·10⁻² | 1,45·10⁻² |
| 0,05 | 3,47·10⁻² | 1,21·10⁻¹ | 7,99·10⁻² | 5,18·10⁻² |

Fra `q = 0,02` e `0,05` il blocco Gross protegge 12 qubit logici quanto 12 patch di surface
code di distanza fra 9 e 13, con 7–14 volte meno qubit di dato. Sotto `q = 0,01` il vantaggio
si riduce: i fallimenti sono pochi (8 a `q = 0,005`) e il regime asintotico non è raggiunto.
