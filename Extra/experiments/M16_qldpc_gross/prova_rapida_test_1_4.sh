#!/usr/bin/env bash
# M16 — prova rapida degli script dei test 1–4 (--quick: pochi shot, nessun file salvato).
set -euo pipefail
cd "$(dirname "$0")"
PY=/home/claudio/quantum-env/bin/python
for s in sweep_decoder.py analisi_fallimenti.py cerca_distanza.py famiglia_bb.py; do
  echo "################ $s"
  $PY "$s" --quick
done
