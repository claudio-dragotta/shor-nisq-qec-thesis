#!/usr/bin/env bash
# M16 — enumerazione esaustiva fino a peso 5 e, subito dopo, i passi A–G del secondo elenco.
set -uo pipefail
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1
/home/claudio/quantum-env/bin/python enumerazione_esaustiva.py --variante serial --w-max 5 \
    --output-dir artifacts/v2_20260926 2>&1 | tee run_M16_esaustivo_serial_w5.log
bash run_dopo_esaustivo.sh
