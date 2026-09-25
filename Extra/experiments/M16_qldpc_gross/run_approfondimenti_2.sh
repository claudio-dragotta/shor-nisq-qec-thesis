#!/usr/bin/env bash
# M16 — approfondimenti, secondo giro (criteri del REGISTRO, sez. 5).
#  1. min-sum con il fattore di scala standard 0,625: la variante min-sum del primo giro,
#     con il default di ldpc, dava curve non monotone.
#  2. statistica del surface code a basso rumore: punti con meno di 100 fallimenti.
#     Solo MWPM, che sul surface coincide con BP+OSD entro l'incertezza ed e' ~20x piu'
#     veloce. Senza Gross code, gli indici delle configurazioni cambiano e i campioni sono
#     indipendenti da quelli del primo giro.
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
OUT=artifacts/v2_20260926

$PY gross_code_capacity.py --seed 42 --solo-gross --bp-method minimum_sum \
    --ms-scaling-factor 0.625 --etichetta sens_minsum_0625 --output-dir "$OUT" \
    2>&1 | tee run_M16_sens_minsum_0625.log

$PY gross_code_capacity.py --seed 42 --senza-gross --decoder-surface mwpm \
    --q-list 0.005 0.01 0.02 --distances 7 9 11 13 \
    --shots-max 300000000 --min-failures 100 --chunk 50000 \
    --etichetta surface_estensione --output-dir "$OUT" \
    2>&1 | tee run_M16_surface_estensione.log
