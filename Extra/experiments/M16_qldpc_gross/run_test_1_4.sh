#!/usr/bin/env bash
# M16 — test 1–4 (criteri in REGISTRO_M16, sez. 10). Uso:
#     bash run_test_1_4.sh            # tutti e quattro
#     bash run_test_1_4.sh 3 4        # solo alcuni
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
A=artifacts/v2_20260926
TEST=("${@:-1 2 3 4}")
TEST=(${TEST[@]})

# corse dirette di riferimento, sempre esplicite
GROSS_MINSUM=(
    $A/results_M16_gross_code_capacity_sens_minsum_0625_20260926_034008.json
    $A/results_M16_gross_code_capacity_minsum_basso_rumore_20260926_041723.json
)
SURFACE_MWPM=(
    $A/results_M16_gross_code_capacity_20260926_031028.json
    $A/results_M16_gross_code_capacity_basso_rumore_20260926_033631.json
    $A/results_M16_gross_code_capacity_surface_estensione_20260926_041513.json
)

for t in "${TEST[@]}"; do
  case "$t" in
    1) $PY sweep_decoder.py --seed 42 --output-dir $A 2>&1 | tee run_M16_test1_sweep_decoder.log ;;
    2) $PY analisi_fallimenti.py --seed 42 --output-dir $A \
           --diretti-json "${GROSS_MINSUM[@]}" "${SURFACE_MWPM[@]}" \
           2>&1 | tee run_M16_test2_fallimenti.log ;;
    3) $PY cerca_distanza.py --seed 42 --output-dir $A 2>&1 | tee run_M16_test3_distanza.log ;;
    4) $PY famiglia_bb.py --seed 42 --output-dir $A --surface-json "${SURFACE_MWPM[@]}" \
           2>&1 | tee run_M16_test4_famiglia_bb.log ;;
    *) echo "test sconosciuto: $t" >&2; exit 1 ;;
  esac
done
