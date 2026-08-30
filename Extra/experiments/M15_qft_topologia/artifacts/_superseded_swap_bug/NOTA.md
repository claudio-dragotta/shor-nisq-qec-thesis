# Risultati superati — bug nell'eliminazione degli SWAP

Prodotti il 30/08/2026 prima della correzione di `inverse_qft_approx`.

Il braccio `elimina_swap=True` toglieva i SWAP e rinominava i bit classici alla misura.
I SWAP stanno pero' PRIMA della cascata, non dopo: la scorciatoia produceva un circuito
diverso, con `P_success` ideale 0,4542 e picchi in 0/255/128 invece di 0/64/128/192.

Il braccio `elimina_swap=False` di questi file e' corretto, ma i due bracci non erano
confrontabili, quindi l'esito primario riportato non e' valido.

Conservati come traccia secondo la regola permanente 4 di CLAUDE.md.
