# Revisione delle appendici

La revisione considera le appendici A–E, la loro impaginazione e il rapporto con i capitoli principali. Un richiamo necessario al protocollo non è considerato inutile: il criterio di taglio è la ripetizione di dati o rappresentazioni senza informazioni aggiuntive.

## Valutazione dei contenuti

| Appendice | Materiale da mantenere | Materiale alleggeribile |
|---|---|---|
| A — Trattazione teorica estesa | Postulati, operatori, derivazioni dei canali, distinzione fra probabilità di errore e successo, richiami QEC e aritmetica. Servono a sostenere il formalismo del Capitolo 3. | Le foto dell'hardware sono illustrative; lo schema della QPU è più direttamente utile. La rassegna generale dei fondamenti può essere abbreviata se si desidera un'appendice meno didattica. Il grafico del proxy di nessun evento è opzionale: l'equazione e l'esempio numerico già spiegano il meccanismo. |
| B — Strumenti, ambiente e codice | Versionamento, manifest, contratto dei dati e listati della pipeline. I listati permettono di capire i passaggi implementativi. | La panoramica dei framework e le motivazioni generali di Qiskit/WSL riprendono il Capitolo 4. La tabella di confronto dei framework non documenta risultati sperimentali e potrebbe essere eliminata in una successiva sintesi. |
| C — Contesto e motivazione | Dettagli RSA e protocollo statistico, soprattutto sentinella dei fallimenti, pareggi e confronto appaiato. | È l'appendice meno necessaria nel complesso: storia del calcolo quantistico, PQC e NISQ riprendono l'introduzione. La sezione C.1 è il primo candidato a un taglio ulteriore; C.2 conserva dettagli operativi richiamati altrove. |
| D — Campagna classica | Griglie degli sweep, confronto ZNE, numerosità, audit delle etichette, ROC e istogramma in cui TOP-1 fallisce ma TOP-4 recupera i fattori. | Il secondo grafico combinatorio non aggiunge dati: mostra il complemento della probabilità già rappresentata dalla Figura 5.2. È stato sostituito con un rimando. |
| E — Campagna QEC | Sindromi, controlli non-Pauli, esperimenti E5–E12, trasferibilità, controlli Gross code, M11/M11b/M13 e protocolli AQFT. Sono evidenze aggiuntive o dettagli di riproducibilità. | Le tre tabelle AQFT finali ripetevano integralmente le griglie N=15, la sensibilità N=21 e i nove contrasti QPE del Capitolo 5. Sono state sostituite con rimandi alle tabelle principali; protocolli, ipotesi, controlli e limiti restano nell'appendice. |

## Tagli effettuati

- Rimossa la figura `fig:tetto_classe_negativa` da D: mantenuti formula, esempio TOP-16 e interpretazione; rimando alla Figura 5.2 per la probabilità complementare.
- Rimosse da E le tabelle `tab:aqft_n15_completa`, `tab:aqft_n21_sensibilita` e `tab:aqft_qpe_completa`. I dati restano nel Capitolo 5, rispettivamente nelle tabelle con etichette `tab:finale_5_22`, `tab:finale_5_25` e `tab:finale_5_26`. La numerazione visibile viene aggiornata da LaTeX.
- Non sono state eliminate derivazioni, risultati aggiuntivi, numerosità, intervalli di confidenza, protocolli o limiti sperimentali.

## Revisione estetica

| Figure / elementi | Intervento |
|---|---|
| Tutte le didascalie delle figure nelle appendici | Dimensione uniforme `small`, etichetta in grassetto e didascalia sotto il contenuto. |
| A.3 — Schema QPU | Didascalia abbreviata; spiegazione su accoppiamenti e qubit di riferimento nel testo. |
| A.4 — Foto hardware | Altezza massima ridotta da 52 a 36 mm; due celle di uguale larghezza, sottodidascalie brevi e collocazione flessibile. Eliminata la pagina dedicata quasi esclusivamente alle foto. |
| A.5 — Chip | Larghezza ridotta dal 62% al 48%; didascalia breve, credito conservato, spiegazione nel testo. |
| A.6 — Proxy illustrativo | Grafico rigenerato dalle stesse formule e dagli stessi parametri, con etichette leggibili. Corretto il titolo e l'asse: rappresenta il proxy di nessun evento, non la probabilità di successo di Shor. Dimensione controllata. |
| A.7 — Canali sul piano di Bloch | Grafico vettoriale rigenerato mantenendo canali e parametri, con titoli, poli e valori più leggibili. Dimensione controllata per convivere con la tabella dei canali. |
| D.1 — ROC | Larghezza fino al 90% per lasciare leggibili i due pannelli; altezza controllata. |
| D.2 — Istogramma negativo | Larghezza del 76% e altezza controllata; conservate annotazioni, legenda e interpretazione. |
| E.1 — Errore coerente | Riduzione moderata, mantenendo curve e marcatori leggibili. |
| E.2 — Confronto decoder | Quasi tutta larghezza per i due pannelli; didascalia breve, spiegazione nel testo. |
| E.3 — Layout M11 | Dimensioni controllate e didascalia breve; spiegazione dello split, distinzione dalla correlazione e limiti osservazionali nel testo. |
| Listati B | Interlinea singola locale, spazio riservato all'inizio degli estratti e raggruppamento degli ultimi tre listati (confronto appaiato, crosstalk e Stim/PyMatching) per evitare la coda isolata di Stim/PyMatching. |

I grafici scientifici non sono stati ridotti tutti allo stesso valore: pannelli affiancati, legende e annotazioni richiedono dimensioni diverse. I file originali delle figure restano disponibili nella cartella `figure`.

## Eventuali tagli ulteriori

Per una versione più essenziale, l'ordine consigliato è: abbreviare C.1; ridurre la panoramica generale di B.1; scegliere se mantenere entrambe le illustrazioni hardware A.4 e A.5; valutare il grafico puramente illustrativo A.6. Questi contenuti non sono stati rimossi nella presente revisione perché hanno una funzione didattica, pur non essendo necessari a verificare i risultati.

## Verifica finale

Il PDF completo passa da 202 a 192 pagine, mantenendo le precedenti correzioni dei capitoli principali. Compilazione riuscita senza riferimenti irrisolti né contenuti oltre i margini segnalati da LaTeX. Verificate le pagine delle figure e la disposizione dei listati QEC finali. PDF e ZIP per Overleaf sono stati aggiornati.

## Sintesi di B.2.3

Ridotti i listati da 13 a 5: moltiplicazione modulare, noise model, confronto sullo stesso istogramma, crosstalk e Stim/PyMatching. Aggiornati i richiami agli estratti eliminati e aggiunto il rimando al repository completo. La versione precedente è conservata in `_archivio/capitoli_storici/appendici_pre_pulizia_2026-10-06/B_estratti_completi_prima_sintesi.tex`.
