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
# SCELTA DEI LIVELLI. Il primo tentativo usava 0,3 / 0,1 / 0,03 e misurava pavimento:
# con AGI media 0,0104 sui 20 archi del layout, gli errori attesi sono 155 / 52 / 15,5
# sulla QFT piena da 49.661 ECR. Il circuito e' cenere molto prima. L'incrocio sta dove
# uno sopravvive e l'altro no, cioe' dove gli errori attesi scendono sotto l'unita':
#   fattore 0,01  -> 5,2 errori (piena)  2,4 (troncata)
#   fattore 0,003 -> 1,5                 0,7
# Si tiene 0,03 come estremo alto, anche perche' la tesi ha gia' mostrato che questo
# conto e' pessimista: la frazione coerente efficace dava k_eff fra 14 e 20 invece
# delle 166 porte nominali.
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

for F in 0.03 0.01 0.003; do
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
