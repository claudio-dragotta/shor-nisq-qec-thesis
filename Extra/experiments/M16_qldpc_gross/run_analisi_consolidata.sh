#!/usr/bin/env bash
# M16 — confronto consolidato con input espliciti.
# Gross: decoder di riferimento min-sum 0,625 (griglia completa + basso rumore).
# Surface: MWPM dalla corsa base, dalla corsa basso_rumore e dall'estensione.
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
A=artifacts/v2_20260926

$PY analisi_consolidata.py \
    --gross-json \
        $A/results_M16_gross_code_capacity_sens_minsum_0625_20260926_034008.json \
        $A/results_M16_gross_code_capacity_minsum_basso_rumore_20260926_041723.json \
    --surface-json \
        $A/results_M16_gross_code_capacity_20260926_031028.json \
        $A/results_M16_gross_code_capacity_basso_rumore_20260926_033631.json \
        $A/results_M16_gross_code_capacity_surface_estensione_20260926_041513.json \
    --output-dir $A 2>&1 | tee run_M16_analisi_consolidata.log
