#!/bin/sh
# Sweep di sensibilita' al rumore per M15.
#
# A rumore di calibrazione pieno N=21 sta sul pavimento uniforme (65/256 = 0,2539) e il
# confronto fra QFT piena e troncata non e' risolvibile: IC Newcombe [-0,0365; +0,0981],
# contiene lo zero. La domanda diventa quindi di sensibilita':
#
#     a quale frazione dell'errore di calibrazione la QFT approssimata inizia a pagare?
#
# Attesa: a rumore basso vince la QFT PIENA, perche' l'approssimazione costa 6,5 punti
# ideali; a rumore alto vince la TRONCATA, perche' ha meta' delle porte. Fra i due deve
# esserci un incrocio, ed e' quello il risultato.
#
# ESPLORATIVO: 256 shot per configurazione danno un errore standard di circa 0,04 su
# holdout. Serve a vedere l'andamento e l'incrocio, non a dare un intervallo stretto.
#
# Costo stimato: ~55 minuti per livello di rumore, ~2h45m in tutto.

# mkdir -p su /mnt/c puo fallire con "File exists": non deve
# abortire lo sweep, quindi e neutralizzato sopra.
set -e
PY=/home/claudio/quantum-env/bin/python
RUN=artifacts/sensibilita
mkdir -p "$RUN/logs" 2>/dev/null || true

for F in 0.3 0.1 0.03; do
  ETICHETTA=$(echo "$F" | tr -d '.')
  echo "=== fattore di rumore $F ==="
  $PY -u qft_approssimata.py \
      --N 21 --shots 256 --batches 4 --holdout-fraction 0.5 --seed 42 \
      --fattore-rumore "$F" \
      --configurazioni "7:6,7:1" \
      --checkpoint "$RUN/checkpoint_f$ETICHETTA.json" \
      --output-dir "$RUN" \
      > "$RUN/logs/f$ETICHETTA.stdout.log" 2> "$RUN/logs/f$ETICHETTA.stderr.log"
  echo "fattore $F concluso: $(date '+%H:%M')"
done

echo "SWEEP COMPLETO"
