#!/usr/bin/env bash
# M16 — secondo elenco, test "basso rumore" e "surface d=15/17" (criteri: REGISTRO, sez. 16).
# Uso:
#     ESAUSTIVO=artifacts/v2_20260926/<results_M16_esaustivo_...json> bash run_secondo_elenco.sh
# Ogni passo riceve i file dei passi precedenti in modo esplicito: il nome si legge dalla
# riga "Salvato"/"Risultati salvati in" del log del passo stesso.
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
A=artifacts/v2_20260926
if [ -z "${ESAUSTIVO:-}" ]; then
    echo "indicare in ESAUSTIVO il JSON della enumerazione esaustiva" >&2
    exit 1
fi
export PYTHONUNBUFFERED=1

salvato() {   # ultimo percorso salvato in un log
    grep -E "Salvato: |Risultati salvati in: " "$1" | tail -1 | sed -E 's/.*(Salvato|salvati in): //'
}
SURFACE_MWPM=(
    $A/results_M16_gross_code_capacity_20260926_031028.json
    $A/results_M16_gross_code_capacity_basso_rumore_20260926_033631.json
    $A/results_M16_gross_code_capacity_surface_estensione_20260926_041513.json
)

echo "### A — f(w) con pesi bassi esatti: Gross serial, surface d=11 e d=13"
$PY analisi_fallimenti.py --seed 42 --seed-base 3100 --etichetta basso_rumore \
    --codici gross_144_12_12:serial surface_d11:mwpm surface_d13:mwpm \
    --esaustivo-json "$ESAUSTIVO" --garanzia-mwpm \
    --w-max 30 --shots-max 20000000 --min-failures 1000 --output-dir $A \
    2>&1 | tee run_M16_basso_rumore_fw.log
FW=$(salvato run_M16_basso_rumore_fw.log)

echo "### B — controllo diretto: Gross serial a q = 1%, 10^8 shot"
$PY famiglia_bb.py --seed 42 --variante serial --codici gross_144_12_12 --q-list 0.01 \
    --shots-max 100000000 --min-failures 1000000000 --indice-base 7000 \
    --etichetta gross_q001_1e8 --output-dir $A 2>&1 | tee run_M16_gross_q001_1e8.log

echo "### C — controllo diretto: surface d=13 a q = 1%, fino a 10^9 shot"
$PY gross_code_capacity.py --seed 42 --senza-gross --decoder-surface mwpm \
    --distances 13 --q-list 0.01 --shots-max 1000000000 --min-failures 300 \
    --chunk 50000 --etichetta d13_q001 --output-dir $A 2>&1 | tee run_M16_d13_q001.log

echo "### D — confronto a basso rumore dalla decomposizione per peso"
$PY confronto_basso_rumore.py --input-json "$FW" --decoder-gross serial \
    --output-dir $A 2>&1 | tee run_M16_confronto_basso_rumore.log

echo "### E — surface d=15 e d=17, MWPM, griglia completa"
$PY gross_code_capacity.py --seed 42 --senza-gross --decoder-surface mwpm \
    --distances 15 17 --shots-max 100000000 --min-failures 100 --chunk 50000 \
    --etichetta surface_d15_d17 --output-dir $A 2>&1 | tee run_M16_surface_d15_d17.log
D1517=$(salvato run_M16_surface_d15_d17.log)

echo "### F — [[288,12,18]] a q = 2% e 3% con piu' statistica"
$PY famiglia_bb.py --seed 42 --variante serial --codici bb_288_12_18 --q-list 0.02 0.03 \
    --shots-max 100000000 --min-failures 300 --indice-base 7100 \
    --etichetta bb288_estensione --output-dir $A 2>&1 | tee run_M16_bb288_estensione.log
B288=$(salvato run_M16_bb288_estensione.log)

echo "### G — confronto consolidato di [[288,12,18]] con il surface fino a d=17"
$PY analisi_consolidata.py --codice bb_288_12_18 --variante-gross serial \
    --etichetta bb288_d17 \
    --gross-json $A/results_M16_test4_famiglia_bb_20260926_120439.json "$B288" \
    --surface-json "${SURFACE_MWPM[@]}" "$D1517" \
    --output-dir $A 2>&1 | tee run_M16_analisi_bb288_d17.log
