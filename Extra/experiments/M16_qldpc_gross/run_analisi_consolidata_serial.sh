#!/usr/bin/env bash
# M16 — confronto consolidato con il decoder definitivo (serial, test 1b).
# Gross: test 4 (famiglia_bb, semi indipendenti da quelli usati per scegliere il decoder).
# Surface: MWPM dalla corsa base, dalla corsa basso_rumore e dall'estensione.
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
A=artifacts/v2_20260926

$PY analisi_consolidata.py --variante-gross serial --etichetta serial \
    --gross-json \
        $A/results_M16_test4_famiglia_bb_20260926_120439.json \
    --surface-json \
        $A/results_M16_gross_code_capacity_20260926_031028.json \
        $A/results_M16_gross_code_capacity_basso_rumore_20260926_033631.json \
        $A/results_M16_gross_code_capacity_surface_estensione_20260926_041513.json \
    --output-dir $A 2>&1 | tee run_M16_analisi_consolidata_serial.log
