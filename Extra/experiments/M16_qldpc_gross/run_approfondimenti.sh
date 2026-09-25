#!/usr/bin/env bash
# M16 — approfondimenti: statistica a basso rumore e sensibilita' di BP+OSD.
# Le corse di sensibilita' usano lo stesso seed della corsa base: per il Gross code i
# campioni coincidono e il confronto e' appaiato (cambia solo il decoder).
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
OUT=artifacts/v2_20260926

$PY gross_code_capacity.py --seed 42 --q-list 0.005 0.01 0.02 --distances 7 9 11 13 \
    --shots-max 5000000 --min-failures 1000 --chunk 10000 \
    --etichetta basso_rumore --output-dir "$OUT" 2>&1 | tee run_M16_basso_rumore.log

$PY gross_code_capacity.py --seed 42 --solo-gross --bp-max-iter 1000 --osd-order 20 \
    --etichetta sens_iter1000_osd20 --output-dir "$OUT" 2>&1 | tee run_M16_sens_iter1000_osd20.log

$PY gross_code_capacity.py --seed 42 --solo-gross --bp-method minimum_sum \
    --etichetta sens_minsum --output-dir "$OUT" 2>&1 | tee run_M16_sens_minsum.log
