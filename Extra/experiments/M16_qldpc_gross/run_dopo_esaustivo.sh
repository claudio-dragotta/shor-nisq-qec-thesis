#!/usr/bin/env bash
# M16 — attende la fine dell'enumerazione esaustiva e lancia run_secondo_elenco.sh con il
# suo JSON, letto dalla riga "Salvato" del log di quella corsa (input esplicito).
set -uo pipefail
cd "$(dirname "$0")"
LOG=run_M16_esaustivo_serial_w5.log

until grep -q "Salvato: " "$LOG"; do
    if ! pgrep -f enumerazione_esaustiva.py > /dev/null; then
        sleep 5
        grep -q "Salvato: " "$LOG" && break
        echo "ENUMERAZIONE TERMINATA SENZA FILE: catena interrotta"
        exit 1
    fi
    sleep 20
done

if grep -q "Corregge tutti gli errori fino a peso 5: True" "$LOG"; then
    echo "Enumerazione: nessun fallimento fino a peso 5"
else
    echo "ATTENZIONE: l'enumerazione ha trovato fallimenti sotto peso 6 (si prosegue)"
fi
ESAUSTIVO=$(grep "Salvato: " "$LOG" | tail -1 | sed 's/.*Salvato: //')
echo "ESAUSTIVO=$ESAUSTIVO"
ESAUSTIVO="$ESAUSTIVO" bash run_secondo_elenco.sh 2>&1 | tee run_M16_secondo_elenco.log
echo "CATENA TERMINATA con codice ${PIPESTATUS[0]}"
