# Analisi dell'utilità delle tabelle della tesi

**Nota successiva alla revisione:** su richiesta dell'utente sono state rimosse le sette tabelle ridondanti delle prime cinque azioni. La tesi ora contiene 76 tabelle. La numerazione e le valutazioni riportate sotto si riferiscono alla versione precedente ai tagli; i riferimenti nei sorgenti e nel PDF aggiornato sono stati ricalcolati.

Analisi dei sorgenti attuali di `file_latex_v2` e del PDF `Claudio_Dragotta_tabelle_revisionate.pdf`, 6 ottobre 2026. Sono presenti **83 tabelle: 82 numerate e una senza numero nel Capitolo 2**. I numeri riportati qui corrispondono alla numerazione del PDF attuale, non ai suffissi delle etichette LaTeX storiche. Questa revisione è editoriale: non verifica gli esperimenti né le fonti esterne e non modifica la tesi.

Una tabella è utile se permette un confronto, documenta un risultato o rende verificabile il metodo. Una duplicazione integrale fra corpo e appendice ha invece poco valore quando non aggiunge campioni, incertezza, condizioni o altri dettagli. Eliminare una tabella non significa eliminare automaticamente le informazioni che contiene.

## Interventi prioritari

1. **Una sola tabella dei preset:** conservare 3.6; eliminare 4.3 e C.1 dopo aver trasferito in 3.6 gli eventuali dettagli aggiuntivi, in particolare il periodo e l'equivalenza delle notazioni. Usare rinvii nelle altre sezioni.
2. **Un solo contratto generale:** conservare 3.8, che include anche il Gross code; sostituire la tabella senza numero del Capitolo 2 con un rinvio, mantenendo nel testo gli eventuali criteri non presenti in 3.8.
3. **Un solo contratto AQFT:** conservare 3.7; assorbire il controllo SWAP di 4.4 nel testo del Capitolo 4 e rimuovere quella tabella.
4. **Una sola sintesi conclusiva:** conservare 6.1, che esplicita anche i limiti; eliminare 5.23 mantenendo la discussione integrata del Capitolo 5.
5. **Metriche SVM e baseline combinatoria:** conservare 5.2 e 5.4; eliminare D.11 e D.14 sostituendole con rinvii.
6. **Griglie complete nelle appendici, confronti essenziali nel corpo:** mantenere E.24–E.27; ridurre 5.16 a pochi punti rappresentativi, assorbire 5.18 in 5.19, eliminare 5.21 e 5.22 come tabelle autonome mantenendone nel testo risultati, limiti e rinvii. La figura QPE resta nel corpo. È una scelta di impaginazione, non una ragione per nascondere risultati non significativi.
7. **Convertire in prosa le tabelle descrittive semplici:** 3.1, 4.5, D.2, E.3, E.21 ed E.23. Il loro contenuto resta disponibile nel testo.

Le prime cinque azioni eliminerebbero **7 tabelle** mantenendo il contenuto rilevante. Con le azioni 6 e 7 si possono eliminare **altre 9 tabelle** e abbreviare 5.16, passando da 83 a circa **67 tabelle**. Il totale è un possibile assetto editoriale, non un obiettivo da raggiungere a ogni costo.

## Valutazione di tutte le tabelle

### Capitoli 2–4

| Tabella | Valutazione | Motivazione e intervento |
|---|---|---|
| Cap. 2, senza numero | Accorpare con 3.8 | Ripete confronti, metriche e criteri inferenziali. Conservare una sola versione completa in 3.8 e un rinvio nel Capitolo 2. |
| 3.1 | Convertire in prosa | Quattro associazioni elementari fra porte e ruolo nella tesi; il paragrafo introduttivo contiene già buona parte della spiegazione. |
| 3.2 | Conservare | Distingue errore fisico, fallimento logico e proxy per gate: previene un errore interpretativo centrale. |
| 3.3 | Conservare | Chiarisce il diverso ruolo di N=15, N=21, N=35 e degli esperimenti di memoria QEC. |
| 3.4 | Conservare | Riunisce numerosità e unità statistiche; è utile per interpretare affidabilità e appaiamento. |
| 3.5 | Conservare | Offre una mappa dei diversi sweep e delle domande associate. Gli esiti dettagliati appartengono all'Appendice D. |
| 3.6 | Conservare come riferimento unico | È la sede naturale dei preset della campagna principale. Incorporare i dettagli esclusivi di 4.3 e C.1. |
| 3.7 | Conservare | Separa i tre esperimenti AQFT, che usano circuiti, budget ed endpoint diversi. |
| 3.8 | Conservare e integrare | Contratto metodologico completo, compreso il Gross code. Può assorbire la tabella del Capitolo 2. |
| 4.1 | Conservare | Associa strumenti e metodi di simulazione alle campagne effettivamente eseguite. |
| 4.2 | Spostare in B, se si alleggerisce il corpo | La mappa di moduli e artefatti aiuta la navigazione del codice; nel corpo rallenta la lettura scientifica. Non è una duplicazione esatta di 4.1. |
| 4.3 | Eliminare dopo accorpamento | Ripete sostanzialmente i preset di 3.6. |
| 4.4 | Accorpare con 3.7 | Ripete bracci AQFT e split; il controllo SWAP è un dettaglio aggiuntivo da mantenere nel testo implementativo. |
| 4.5 | Convertire in elenco o prosa | È una checklist di metadati più che un confronto. Il contenuto è utile, l'ambiente tabella non è necessario. |

### Capitolo 5 e conclusioni

| Tabella | Valutazione | Motivazione e intervento |
|---|---|---|
| 5.1 | Conservare | Riporta esiti quantitativi delle validazioni ideali, non soltanto il perimetro già descritto in 3.3. |
| 5.2 | Conservare | Permette di distinguere accuratezza predittiva e beneficio operativo del classificatore. |
| 5.3 | Conservare | È il confronto centrale TOP-1/TOP-4/M2 con significatività; la figura non sostituisce tutti questi dati. |
| 5.4 | Conservare | Quantifica la baseline combinatoria e limita l'interpretazione del successo TOP-K. D.14 è ridondante. |
| 5.5 | Conservare o ridurre a punti rappresentativi | Confronta struttura residua e proxy di nessun evento, due quantità diverse. La figura rende leggibile l'andamento, la tabella fornisce i valori. |
| 5.6 | Facoltativa nel corpo | Tre punti Steane sono già discussi e accompagnati dalla curva. Può diventare un breve paragrafo; non la considero una priorità di taglio. |
| 5.7 | Conservare | Rende confrontabili soglie da incrocio e da fit nei due settori. |
| 5.8 | Spostabile in appendice | Sono estrapolazioni oltre le distanze simulate. Utile per l'overhead, ma secondaria rispetto ai risultati misurati; mantenere sempre l'avvertenza sul modello. |
| 5.9 | Conservare | Documenta la differenza fra decoder nominale, modello con crosstalk e rete. Non è equivalente a 5.11. |
| 5.10 | Spostabile in appendice | Il compromesso precision/recall spiega il correttore residuale; nel corpo si può riportare un punto esemplificativo. |
| 5.11 | Conservare | Quantifica il risultato principale del decoder ibrido e la dipendenza dalla distanza. |
| 5.12 | Conservare nel corpo | BP+OSD è una baseline decisiva. E.9 aggiunge i test statistici: si può abbreviare il corpo, ma non eliminare l'evidenza aggiuntiva. |
| 5.13 | Conservare | Il confronto a peso fissato spiega perché la scelta del decoder cambia il risultato sul Gross code. Non coincide con 5.14. |
| 5.14 | Conservare | È il confronto principale fra un blocco Gross e 12 patch. E.16 riguarda più codici e stime dirette: non è un duplicato integrale. |
| 5.15 | Conservare o abbreviare | Documenta la curva di successo Shor e gli IC. Il grafico permette eventualmente di ridurre i punti nel corpo conservando la griglia completa altrove. |
| 5.16 | Ridurre nel corpo | Ripete integralmente E.24. Conservare qui pochi livelli di rumore e la distinzione tra successo per misura, TOP-1, TOP-4 e pareggi. |
| 5.17 | Conservare | Sintesi breve dei due controlli hardware-aware; le tabelle E.20–E.23 descrivono il metodo, non gli stessi risultati. |
| 5.18 | Accorpare con 5.19 | La griglia completa è già in E.25. Nel corpo basta il confronto della variante scelta con la QFT piena, presente in 5.19. |
| 5.19 | Conservare | Confronto compatto fra beneficio holdout, porte e profondità. |
| 5.20 | Conservare | Mostra il compromesso strutturale e la perdita ideale su N=21; non è sostituibile dalla sola tabella rumorosa. |
| 5.21 | Tenere una sola versione con E.26 | Stessi tre punti e stessi IC. Preferisco E.26 completa e un paragrafo nel corpo che riporti il risultato non conclusivo. |
| 5.22 | Tenere una sola versione con E.27 | Ripete i nove contrasti holdout. Preferisco la griglia in appendice e figura più sintesi nel corpo, mantenendo il conteggio degli IC positivi. |
| 5.23 | Eliminare | Ripete la sintesi di 6.1, che include anche limiti ed evidenza Gross. La discussione integrata può restare discorsiva. |
| 6.1 | Conservare | Collega ogni domanda alla risposta, all'evidenza e al limite: ha una funzione conclusiva chiara. |

### Appendici A–D

| Tabella | Valutazione | Motivazione e intervento |
|---|---|---|
| A.1 | Facoltativa, conservarla solo come contesto | Confronto di tecnologie QPU; è periferico rispetto alle simulazioni svolte. Non sostiene direttamente una conclusione sperimentale. |
| A.2 | Conservare | Confronto compatto dei canali di rumore, utile per la teoria estesa e i modelli usati. |
| B.1 | Riscrivere o eliminare | Le categorie «Completo», «Parziale», «Limitato» non definiscono un criterio verificabile nella tabella. La toolchain effettiva è già documentata in 4.1. Un confronto fra framework avrebbe valore solo con requisiti specifici e motivazione delle classificazioni. |
| C.1 | Eliminare dopo accorpamento | Terza presentazione degli stessi preset. Riportare notazioni e conversione delle unità nella tabella unica 3.6 o nel testo. |
| D.1 | Conservare | Conteggi, versione e identificativo della netlist contribuiscono alla riproducibilità. |
| D.2 | Convertire in prosa | Ripete il perimetro di 3.3 e 5.1 con meno informazioni quantitative. Mantenere la distinzione fra campagna principale e prove esplorative N=21. |
| D.3 | Conservare | Lo sweep K mostra che il beneficio può saturare già prima di TOP-4. Non eliminarlo solo perché molte righe sono uguali. |
| D.4 | Conservare | Documenta la sensibilità all'errore 2Q e il costo in iterazioni. La tabella 5.5 riguarda un'altra metrica. |
| D.5 | Conservare | Controlla la sensibilità al budget di shot. |
| D.6 | Conservare | Controlla la sensibilità a T1/T2. |
| D.7 | Conservare | Controlla la sensibilità all'errore 1Q. |
| D.8 | Conservare | Controlla la sensibilità al readout. |
| D.9 | Conservare | Collega compilazione, costo circuitale e prestazione operativa. |
| D.10 | Conservare | Il confronto ZNE include il costo totale in shot: informazione decisiva assente nelle altre tabelle TOP-K. |
| D.11 | Eliminare | Ripete le metriche SVM di 5.2 senza aggiungere valori o confronti; il numero di istogrammi può essere esplicitato nella didascalia di 5.2. |
| D.12 | Conservare | L'audit delle etichette TOP-1/TOP-16 spiega perché TOP-16 non forma un problema discriminante. |
| D.13 | Conservare, secondaria | La distribuzione empirica della moda aiuta l'audit degli istogrammi. Può diventare prosa se si accorcia molto l'appendice. |
| D.14 | Eliminare | Gli stessi K e le stesse probabilità sono già in 5.4. |

### Appendice E

| Tabella | Valutazione | Motivazione e intervento |
|---|---|---|
| E.1 | Conservare, eventualmente abbreviare | Mappa didattica dei codici e del loro ruolo. Le righe su codici non sperimentati sono comprimibili, ma il confronto ha una funzione. |
| E.2 | Conservare | Lookup table che documenta la verifica della sindrome del codice a ripetizione. |
| E.3 | Convertire in prosa | Espande i parametri [[7,1,3]] già esposti; basta una frase con tipo CSS e capacità di correzione. |
| E.4 | Conservare | Tabella operativa sindrome–qubit del codice di Steane. |
| E.5 | Conservare e distinguere piano/eseguito | Il disegno sperimentale è utile; chiarire sempre che 2d è un'estensione e non parte della campagna eseguita. |
| E.6 | Conservare | Il controllo incrociato distingue distanza del codice e larghezza dell'ingresso. È evidenza aggiuntiva essenziale per il limite di scala. |
| E.7 | Conservare | Il confronto fra guadagno di validazione e oracolo distingue limiti di discriminazione e di scelta della soglia. |
| E.8 | Conservare | Controllo di modello miscalibrato: domanda diversa dal crosstalk non rappresentato. |
| E.9 | Conservare come dettaglio statistico | Riprende 5.12 ma aggiunge McNemar, campionamento e confronto dei migliori metodi. Questa aggiunta giustifica l'appendice. |
| E.10 | Conservare | Verifica se il residuo sopra BP+OSD combina i vantaggi dei due metodi. |
| E.11 | Conservare | Confronta sei bracci sugli stessi campioni e misura la convergenza dei metodi appresi. |
| E.12 | Conservare | Modelli più potenti e tabella empirica verificano un'ipotesi diversa da quella di E.11. |
| E.13 | Conservare | Documenta trasferibilità fra profili di rumore; non presente nelle tabelle principali. |
| E.14 | Conservare | Documenta ricerca di operatori logici e controlli di costruzione. La spiegazione deve distinguere peso trovato, limite superiore e distanza dimostrata. |
| E.15 | Conservare | Lo sweep delle configurazioni del decoder giustifica la baseline seriale sul Gross code. |
| E.16 | Conservare | Estende il confronto all'intera famiglia BB e mostra campioni con zero o pochi eventi. Non confonderla con la ricostruzione a basso rumore di 5.14. |
| E.17 | Accorpare con la spiegazione di 3.2/E.19 | I quattro livelli sono già spiegati più volte. Si può sostituire questa tabella con un paragrafo introduttivo. |
| E.18 | Facoltativa, mantenere come contesto separato | Presenta stime esterne di risorse, non risultati della tesi. Non confrontare le righe come una serie omogenea; non è una priorità di eliminazione se il contesto crittografico resta parte del lavoro. |
| E.19 | Utile, ma correggere la notazione | La mancata conversione QEC→Shor è centrale. La prima riga usa però «pL di M8» per un proxy chiamato pg in 3.2: va uniformata. Può assorbire E.17. |
| E.20 | Conservare | Il protocollo M11 consente di interpretare e riprodurre il risultato hardware-aware. Distinguere layout richiesti e layout validi analizzati. |
| E.21 | Convertire in prosa | Le quattro interpretazioni delle stime si possono esprimere nel testo senza una tabella separata. |
| E.22 | Conservare | Protocollo M11b e unità indipendente del bootstrap sono necessari per interpretare il confronto. |
| E.23 | Convertire in prosa | Le etichette delle strategie possono essere definite in un breve elenco nel metodo; il contenuto resta utile. |
| E.24 | Conservare come griglia completa | Sede dei dettagli M13; ridurre 5.16 nel corpo. Uniformare pL in pg anche qui. |
| E.25 | Conservare come griglia completa | Sede della griglia AQFT N=15; nel corpo resta 5.19. |
| E.26 | Conservare come griglia completa | Sede del confronto rumoroso N=21; sostituire 5.21 con sintesi e rinvio. |
| E.27 | Conservare come griglia completa | Sede dei nove contrasti QPE; sostituire 5.22 con figura, sintesi e rinvio. |

## Cautele per l'eventuale revisione

- Non eliminare risultati negativi o non significativi perché sembrano poco interessanti: delimitano le conclusioni della tesi.
- Non accorpare come se fossero lo stesso esperimento 5.9, 5.11 ed E.9: alcuni valori differiscono e i confronti non hanno tutti lo stesso contenuto statistico.
- Conservare gli intervalli di confidenza quando si abbrevia una griglia; un valore medio da solo può cambiare l'impressione sul risultato.
- E.19 ed E.24 presentano una notazione da uniformare con 3.2. È un problema di chiarezza, non un motivo per eliminare il controllo.
- Le etichette LaTeX hanno numeri storici diversi dalla numerazione stampata. Per qualsiasi taglio occorre aggiornare rinvii, didascalie, elenco delle tabelle e impaginazione con una nuova compilazione.

Nessuna tabella è stata rimossa durante questa analisi.
