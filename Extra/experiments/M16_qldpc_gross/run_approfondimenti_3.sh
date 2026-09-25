#!/usr/bin/env bash
# M16 — approfondimenti, terzo giro. Il min-sum con fattore di scala 0,625 migliora molto
# il Gross code a basso rumore (criterio 3 del REGISTRO non soddisfatto): per la regola
# fissata in anticipo diventa il decoder di riferimento e si applica anche al surface.
#  1. Gross, min-sum 0,625, q = 0,5–2%, fino a 2e7 shot o 1000 fallimenti. Stessi indici
#     di seed della corsa basso_rumore: confronto appaiato con product_sum.
#  2. Sensibilita' del nuovo riferimento: min-sum 0,625 con 1000 iterazioni e OSD ordine 20.
#  3. Surface d = 3…13 con BP+OSD min-sum 0,625 sulla griglia base, per un confronto alla
#     pari fra i due codici con lo stesso decoder.
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
OUT=artifacts/v2_20260926
MS="--bp-method minimum_sum --ms-scaling-factor 0.625"

$PY gross_code_capacity.py --seed 42 --solo-gross $MS \
    --q-list 0.005 0.01 0.02 --shots-max 20000000 --min-failures 1000 --chunk 10000 \
    --etichetta minsum_basso_rumore --output-dir "$OUT" \
    2>&1 | tee run_M16_minsum_basso_rumore.log

$PY gross_code_capacity.py --seed 42 --solo-gross $MS --bp-max-iter 1000 --osd-order 20 \
    --etichetta sens_minsum_iter1000_osd20 --output-dir "$OUT" \
    2>&1 | tee run_M16_sens_minsum_iter1000_osd20.log

$PY gross_code_capacity.py --seed 42 --senza-gross --decoder-surface bposd $MS \
    --etichetta surface_bposd_minsum --output-dir "$OUT" \
    2>&1 | tee run_M16_surface_bposd_minsum.log
