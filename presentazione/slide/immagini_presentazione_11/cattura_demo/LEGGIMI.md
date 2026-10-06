# Catture della demo su sfondo bianco

`cattura.mjs` apre la demo locale (http://localhost:8501), inietta `tema_chiaro.css`,
porta la scheda Rumore in "Confronto visivo" allo stadio 6/6 e salva due PNG a 2x:
il confronto ideale/rumoroso e lo schema "dove entra il rumore". Le frecce di Bloch,
che la demo colora con HSL al 68% di luminosità, vengono scurite al 40% prima dello scatto.
La demo non viene modificata.

    # demo avviata in Extra/shor-demo: python -m uvicorn server:app --port 8501
    npm init -y && npm install playwright@1.63.0
    node cattura.mjs chiaro out      # oppure "scuro" per il tema originale
