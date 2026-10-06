# Brief per Claude Design: presentazione di laurea

## Chi sono e che cosa serve

Presentazione per la discussione della tesi magistrale di **Claudio Dragotta**,
*Shor's Algorithm under Noise: Machine-Learning Ablation, Quantum Error Correction, and
Approximate QFT*. Relatore Prof. Paolo Soda, correlatore Prof. Floriano Caprio. Università
Campus Bio-Medico di Roma, CdLM Ingegneria dei Sistemi Intelligenti (LM-32), A.A. 2025/2026,
sessione di ottobre 2026. Durata: **[__ minuti]**.

Ti chiedo di **ridisegnare graficamente** la presentazione esistente, 23 slide, mantenendo
**percorso, testi e numeri**. Ogni numero è verificato sulla tesi: non cambiarlo, non
arrotondarlo diversamente, non aggiungerne di nuovi. Se per spazio devi accorciare un testo,
togli parole ma lascia numeri, unità e qualificazioni ("nel modello code-capacity", "su
holdout", "modello illustrativo").

## Il percorso narrativo (da rispettare)

È lo stesso schema della presentazione di un collega già discussa: si parte dall'argomento
generale e si stringe fino al problema, poi approcci, fondamenti, obiettivi, metodo,
risultati e conclusioni. **Le slide sono 23**; il contenuto completo di ciascuna è nella
sezione "Contenuto slide per slide" in fondo.

| # | Sezione | Titolo | Ruolo nel percorso |
|---|---|---|---|
| 1 | — | Copertina | titolo, laureando, relatore, correlatore, sfera di Bloch |
| 2 | Indice | Indice | cinque sezioni con slide di inizio |
| 3 | Contesto | Dal vantaggio teorico al rumore | argomento di base: RSA, GNFS sub-esponenziale contro Shor polinomiale |
| 4 | Contesto | L'algoritmo di Shor | le quattro fasi, periodicità di 7^x mod 15, circuito N = 15 |
| 5 | Contesto | Il problema: il rumore porta Shor al livello casuale | problema quantificato: 74,89% → ≈ 24,6% |
| 6 | Contesto | Approcci esistenti contro il rumore | tre famiglie con promessa e rischio, poi il gap |
| 7 | Contesto | Fondamenti: QEC e QFT approssimata | ciclo QEC, AQFT, notazione p, p_L, p_g |
| 8 | Obiettivi | Obiettivi del lavoro | tre livelli di intervento |
| 9 | Obiettivi | Domande di ricerca | DR1–DR5 con la metrica di ciascuna |
| 10 | Metodo | Perimetro sperimentale e strumenti | istanze, strumenti, riproducibilità |
| 11 | Metodo | Confronto appaiato e ablazione | stesso istogramma per TOP-1, TOP-4, M2 |
| 12 | Risultati | DR1 · Post-processing e machine learning | 1,00 iterazioni con TOP-4; il ML non aiuta |
| 13 | Risultati | DR2 · Correzione d'errore e soglia | soglia 0,86% (Z) e 0,81% (X) |
| 14 | Risultati | DR3 · Decoder analitici, appresi e ibridi | ibrido −15,6–17,6% a d = 3 |
| 15 | Risultati | DR3 · Gross code e surface code | 144 contro 2028 qubit di dato, code-capacity |
| 16 | Risultati | DR4 · Sensibilità di Shor al rumore | 74,89% senza rumore, plateau 63/256 |
| 17 | Risultati | DR5 · QFT approssimata su N = 15 | 0,4792 → 0,6279, ECR 362 → 279 |
| 18 | Risultati | DR5 · AQFT su N = 21 e QPE isolata | beneficio non dimostrato su N = 21 |
| 19 | Conclusioni | Risposte alle domande di ricerca | tabella DR / risposta / evidenza |
| 20 | Conclusioni | Conclusione centrale | la complessità paga solo sul collo di bottiglia |
| 21 | Conclusioni | Limiti e sviluppi futuri | quattro limiti, cinque sviluppi |
| 22 | — | Grazie per l'attenzione | tre takeaway, resta a schermo durante le domande |
| 23 | Riserva | Demo interattiva | catture della demo su sfondo bianco |

## Vincoli obbligatori (Ufficio Audiovisivi dell'Ateneo)

- Formato **16:9**. File finale **PowerPoint (.pptx)** e **PDF**, nome `Dragotta Claudio`.
- Il PDF dell'Ateneo vieta i **programmi online** per la versione consegnata: usa Claude
  Design per il progetto grafico, poi la versione finale va esportata e controllata in
  PowerPoint.
- **Non usare layout UCBM preimpostati**; il logo si inserisce come immagine.
- Font **Arial** ovunque. **Nessuna animazione, nessuna transizione.**
- Video solo .mp4, uno per slide, riproduzione **automatica**.

## Sistema grafico attuale (da mantenere e raffinare)

- Sfondo bianco. Titolo in alto a sinistra, blu `#125C97`, linea sottile `#3F73B0` sotto.
- In alto a destra: etichetta `Sezione | n` (grigio) e logo UCBM.
- Schede bianche con bordo blu e intestazione piena `#125C97` con testo bianco.
- Cerchi numerati e riquadri di enfasi blu scuro `#0B2F5B` con testo bianco.
- Riquadri chiari `#E8EFF6` per note e righe alterne delle tabelle.
- Testo `#1F2933`, didascalie `#5B6573`. Seconda serie dei grafici arancio `#D9822B`.
- Corpo non sotto 20 pt; solo didascalie, fonti e tabelle semplici a 13–15 pt.
- **Virgola decimale** ovunque. Titoli al massimo su due righe.

## Regole di contenuto

- Tutto è **simulazione**: "modello illustrativo", mai "realistico".
- p_g è un proxy per gate e **non** è p_L; le soglie QEC valgono per i memory experiment.
- Decoder ibrido: **15,6–17,6%** è una riduzione relativa di p_L. Mai 18–21%.
- Gross code solo nel **modello code-capacity**.
- Dichiara i risultati negativi: il classificatore non migliora TOP-4, la rete da sola non
  batte MWPM, l'AQFT non è dimostrata su N = 21, nessun vantaggio significativo a d = 7.
- I numeri della demo (seed 42, preset UC1) non sono risultati della tesi.

## Immagini

Cartella `Extra/slide/immagini_presentazione_11/` (allegale a Claude Design):

| File | Slide |
|---|---|
| `s01_copertina_sfera_bloch.png` | 1 e 22, sfera di Bloch su sfondo trasparente |
| `logo_ucbm.png` | tutte |
| `s03_shor_successo_vs_pg.png` | 5 e 16, curva del successo contro p_g |
| `s09_iterazioni_primo_successo.png` | 12, iterazioni TOP-1 / TOP-4 / M2 |
| `s10_decoder_bposd_ibrido.png` | 14, BP+OSD e ibrido contro MWPM |
| `r_aqft_n15_holdout.png` | 17, AQFT su N = 15 |
| `r_surface_code_soglia_orig_5_4.png` | 13, surface code (ha ancora il punto decimale) |
| `r_aqft_qpe_holdout_orig_5_10.png` | 18, QPE isolata (ha ancora il punto decimale) |
| `r_demo_confronto_ideale_rumore.png`, `r_demo_dove_entra_il_rumore.png` | 23, demo su sfondo bianco |
| `orig_3_2_pipeline_shor.png`, `orig_4_2_pipeline_appaiata.png` | modelli per ridisegnare gli schemi delle slide 4 e 11 |

La foto di IBM Quantum System One della slide 3 e il circuito della slide 4 sono nel pptx
attuale. Nella slide 4 il grafico della periodicità e il circuito vengono dalla tesi
(Fig. 3.1 e circuito N = 15).

Usa i grafici così come sono: non ridisegnarli con dati stimati a occhio.

## Contenuto slide per slide

Testo estratto dalla presentazione attuale. "Ruolo" dice a che cosa serve la slide nel
percorso; il resto è il contenuto da impaginare.

### Slide 1 — UNIVERSITÀ CAMPUS BIO-MEDICO DI ROMA

- Ruolo: Copertina
- FACOLTÀ DIPARTIMENTALE DI INGEGNERIA / CORSO DI LAUREA MAGISTRALE IN INGEGNERIA DEI SISTEMI INTELLIGENTI
- SHOR'S ALGORITHM UNDER NOISE: / MACHINE-LEARNING ABLATION, / QUANTUM ERROR CORRECTION, / AND APPROXIMATE QFT
- Relatore
- Prof. Paolo Soda
- Correlatore
- Prof. Floriano Caprio
- Laureando
- Claudio Dragotta
- A.A. 2025/2026
- Immagini nella slide: 1

### Slide 2 — Indice

- Ruolo: Indice
- Contesto
- da / 3
- Obiettivi
- da / 8
- Metodo
- da / 10
- Risultati
- da / 12
- Conclusioni
- da / 19
- Immagini nella slide: 1

### Slide 3 — Dal vantaggio teorico al rumore

- Ruolo: Argomento di base: fattorizzazione, RSA, Shor (aggancio: il limite è il rumore)
- La sicurezza di RSA si fonda sulla difficoltà di fattorizzare interi di grandi dimensioni.
- Il miglior algoritmo classico generale, il General Number Field Sieve, ha costo sub-esponenziale.
- Nel 1994 Shor mostra che un computer quantistico ideale fattorizza in tempo polinomiale.
- Classico · GNFS
- sub-esponenziale
- Quantistico · Shor
- polinomiale
- Il limite attuale: il rumore
- Errori di gate, decoerenza, readout imperfetto, connettività limitata e crosstalk riducono la profondità dei circuiti eseguibili con affidabilità.
- IBM Quantum System One: al centro il criostato che contiene il chip
- Immagini nella slide: 2

### Slide 4 — L'algoritmo di Shor

- Ruolo: Contesto tecnico: come funziona Shor
- 1
- Pre-processing classico
- 2
- Ricerca del periodo
- 3
- QFT inversa e misura
- 4
- Post-processing classico
- scelta di a, gcd(a, N)
- esponenziazione modulare e QPE
- esito y, con y / 2^m ≈ s / r
- frazioni continue e gcd
- Per N = 15 e a = 7 la sequenza 7^x mod 15 si ripete ogni 4 valori: r = 4, da cui 15 = 3 × 5.
- Circuito per N = 15: 8 qubit di controllo (C) e 4 di lavoro (T), esponenziazione modulare controllata, QFT inversa e misura
- Immagini nella slide: 3

### Slide 5 — Il problema: il rumore porta Shor al livello casuale

- Ruolo: IL PROBLEMA, quantificato con un numero
- Preparazione
- Errori di preparazione dello stato
- Esponenziazione modulare
- Decoerenza ed errori sulle porte a due qubit
- QFT inversa
- Errori di fase e rumore di gate
- Misura
- Errori di lettura (readout)
- Shor N = 15, a = 7: successo per singola misura al variare del proxy di errore per gate p_g
- 74,89% → ≈ 24,6%
- Ad alto rumore resta solo il 63/256 che la verifica classica accetterebbe anche da esiti casuali.
- probabilità di ricavare i fattori per singola misura, da nessun rumore a rumore elevato; con p_g = 1% è già 56,5%
- Immagini nella slide: 2

### Slide 6 — Approcci esistenti contro il rumore

- Ruolo: Approcci esistenti e gap (frase "Rimane aperto...")
- Famiglia | Promessa | Rischio da controllare
- Post-processing e ML | sfruttare l'informazione residua nell'istogramma | il guadagno viene dai candidati provati, non dal modello
- QEC e decoder appresi | sopprimere l'errore logico | baseline analitica debole; soglia valida solo per la memoria
- QFT approssimata | meno porte, meno rumore | perdita di precisione di fase
- Rimane aperto il problema di valutare ogni tecnica contro la baseline corretta, sulla metrica finale.
- Yang e Markidis 2026 · Bausch et al., Nature 2024 · Roffe et al. 2020 · Bravyi et al., Nature 2024 · Barenco et al. 1996
- Immagini nella slide: 1

### Slide 7 — Fondamenti: QEC e QFT approssimata

- Ruolo: Fondamenti delle tecniche usate dopo (QEC e AQFT)
- Codifica
- più qubit fisici formano un qubit logico
- Sindrome
- rivela l'errore senza misurare lo stato logico
- Decoder
- MWPM, BP+OSD o una rete scelgono la correzione
- Soglia
- sotto p_th, più distanza d riduce p_L
- Complementari: l'AQFT contiene le risorse del circuito, la QEC protegge l'esecuzione dal rumore.
- Notazione: p errore fisico · p_L errore logico dopo la decodifica · p_g proxy di errore per gate applicato a Shor
- QEC · durante il calcolo
- Protegge l'informazione mentre il calcolo è in corso. Conviene solo sotto soglia: sopra soglia l'overhead amplifica l'errore.
- AQFT · nel circuito
- Elimina le rotazioni controllate di piccolo angolo: meno porte e profondità, al prezzo di precisione di fase.
- Immagini nella slide: 1

### Slide 8 — Obiettivi del lavoro

- Ruolo: Obiettivi
- Punto di partenza: misurare come Shor degrada al crescere del rumore. Poi valutare, con baseline esplicite, tre livelli di intervento.
- 1
- A VALLE DELLA MISURA
- Sfruttare l'informazione residua
- Post-processing degli esiti di Shor: ricerca TOP-K, classificatore ML, confronto con ZNE
- Domanda DR1
- 2
- DURANTE IL CALCOLO
- Proteggere l'informazione
- Quantum Error Correction: ripetizione, Steane, surface code, Gross code; decoder analitici e appresi
- Domande DR2 e DR3
- 3
- NEL CIRCUITO
- Ridurre le operazioni esposte al rumore
- QFT approssimata: meno porte e meno profondità, al prezzo di precisione di fase
- Domanda DR5
- Immagini nella slide: 1

### Slide 9 — Domande di ricerca

- Ruolo: Domande di ricerca
- 1
- Post-processing e machine learning
- 2
- Codici di correzione d'errore
- 3
- Decoder analitici, appresi e ibridi
- 4
- Sensibilità di Shor al rumore
- 5
- QFT approssimata
- Cercare più candidati riduce le iterazioni? Un classificatore aggiunge valore?
- In quale regime la codifica batte il qubit fisico? Quanto conta la distanza?
- Un decoder appreso supera quello analitico con rumore correlato?
- Come cala il successo al crescere dell'errore per gate p_g?
- Quando meno porte compensano la perdita di precisione di fase?
- Metrica / iterazioni fino ai fattori
- Metrica / p_L(p, d) e soglia p_th
- Metrica / differenza di p_L sugli stessi campioni
- Metrica / P_succ(p_g) e P cumulativa
- Metrica / P_succ, porte a due qubit, profondità
- Immagini nella slide: 1

### Slide 10 — Perimetro sperimentale e strumenti

- Ruolo: Metodo: perimetro e strumenti
- Tutti gli esperimenti sono simulazioni classiche di circuiti quantistici: nessuna esecuzione su hardware reale e nessuna previsione per moduli di dimensione crittografica.
- Istanze
- N = 15, a = 7, r = 4 / campagna rumorosa principale: 12 qubit, 224 CX, profondità 412
- N = 21, a = 2, r = 6 / validazione ideale e AQFT esplorativa
- N = 35, a = 6, r = 2 / controllo ideale dell'aritmetica
- Strumenti
- Qiskit e Aer / Shor, modelli di rumore, AQFT
- Stim e PyMatching / surface code e decoder MWPM
- scikit-learn / SVM, MLP e correzione residuale
- ldpc (BP+OSD) / Gross code
- Riproducibilità
- Tracciabilità / seed, manifest, versioni e hash della netlist
- Dati separati / partizioni selection / holdout
- Confronti appaiati / stessi campioni per tutte le strategie
- Immagini nella slide: 1

### Slide 11 — Confronto appaiato e ablazione

- Ruolo: Metodo: confronto appaiato e ablazione
- Simulazione
- Shor N = 15, a = 7 / un istogramma da 1024 shot per iterazione
- TOP-1
- solo l'esito più frequente
- TOP-4
- i quattro candidati più frequenti
- M2
- classificatore ML, poi TOP-4
- Verifica classica
- frazioni continue e gcd, stessa regola per tutte
- Metrica
- iterazioni fino ai fattori / Wilcoxon-Pratt e correzione di Holm
- Ablazione: M2 contro TOP-4 senza filtro isola il contributo del classificatore.
- Numerosità: 30 repliche appaiate per scenario di rumore, fino a 50 iterazioni; classificatore addestrato su 2000 istogrammi per scenario.
- Immagini nella slide: 1

### Slide 12 — DR1 · Post-processing e machine learning

- Ruolo: Risultato DR1
- Iterazioni medie al primo successo nei due scenari di rumore simulati (UC1 moderato, UC2 più severo)
- 1,00
- iterazioni medie con TOP-4, in 30 repliche su 30 e in entrambi gli scenari (TOP-1: 1,37 e 1,50)
- Classificatore accurato, ma non utile: la SVM raggiunge F1 0,919 / 0,923 e AUC 0,965 / 0,958, ma M2 richiede 1,50 / 1,37 iterazioni ed è peggiore della propria ablazione TOP-4 (p_Holm 0,0033 e 0,0096).
- Il beneficio viene dalla ricerca multi-candidato, non dal filtro appreso.
- Immagini nella slide: 2

### Slide 13 — DR2 · Correzione d'errore e soglia

- Ruolo: Risultato DR2
- Surface code, memoria in base Z con rumore circuit-level e decoder MWPM; la linea tratteggiata è l'incrocio visivo delle curve, circa 0,9%
- 0,86%
- soglia stimata del surface code in base Z (0,81% in base X), dal fit sotto soglia
- Sotto soglia (p = 2×10⁻³, base Z): l'errore logico scende da 1,94×10⁻³ a d = 3 fino a 2,01×10⁻⁵ a d = 9.
- Sopra soglia (p = 10⁻²): l'ordine si inverte, circa 3,9% a d = 3 contro 5,6% a d = 9.
- Steane [[7,1,3]]: pendenza 1,94, compatibile con la soppressione quadratica; pseudo-soglia a p ≈ 0,08.
- La codifica conviene solo sotto soglia: lì aumentare la distanza sopprime l'errore logico.
- Immagini nella slide: 2

### Slide 14 — DR3 · Decoder analitici, appresi e ibridi

- Ruolo: Risultato DR3
- Rapporto di guadagno rispetto a MWPM: sopra 1 il metodo ha errore logico inferiore
- 15,6–17,6%
- riduzione relativa dell'errore logico con il decoder ibrido (MWPM + rete) a d = 3, in presenza di crosstalk
- Rete come sostituto: a modello corretto non supera MWPM; servono 10⁵–10⁶ campioni solo per pareggiarlo a d = 3.
- Con la scala il margine cala: 0,5–3,2% a d = 5, non significativo a d = 7.
- BP+OSD è una baseline analitica forte: −25,5% a d = 5 senza crosstalk.
- Il ML aiuta come correttore residuale, quando il decoder analitico non rappresenta la struttura dell'errore.
- Immagini nella slide: 2

### Slide 15 — DR3 · Gross code e surface code

- Ruolo: Risultato DR3 (Gross code)
- Confronto esplorativo nel modello code-capacity: quanti qubit di dato servono per proteggere gli stessi 12 qubit logici?
- Gross code
- [[144,12,12]]
- 144
- qubit di dato
- vs
- 12 × surface code
- distanza 13
- 2028
- qubit di dato
- Con il decoder adeguato (BP+OSD a schedulazione seriale) il Gross code protegge meglio per errore fisico ≥ 0,75%, con circa un quattordicesimo dei qubit di dato.
- Il decoder conta quanto il codice: da schedulazione parallela a seriale il fallimento a errore 1% scende di circa 100 volte (9,8×10⁻⁵ → 1,0×10⁻⁶).
- Immagini nella slide: 1

### Slide 16 — DR4 · Sensibilità di Shor al rumore

- Ruolo: Risultato DR4
- Shor N = 15, a = 7: successo per singola misura al variare del proxy di errore per gate p_g
- 74,89%
- probabilità di ricavare i fattori per singola misura in assenza di rumore
- Degrado regolare: 64,5% a p_g = 0,005, 56,5% a 0,01 e 45,2% a 0,02.
- Plateau a circa 24,5% da p_g ≈ 0,1: è il pavimento 63/256 della verifica classica, che accetta 63 esiti su 256 anche da una distribuzione uniforme.
- Il plateau non indica periodicità residua; p_g è un proxy per gate, non un tasso di errore logico QEC.
- Immagini nella slide: 2

### Slide 17 — DR5 · QFT approssimata su N = 15

- Ruolo: Risultato DR5 (N = 15)
- Successo holdout al variare del grado di troncamento della QFT inversa finale; la linea tratteggiata è la QFT piena
- Grandezza | QFT piena | AQFT | Variazione
- P_succ holdout | 0,4792 | 0,6279 | +14,87 punti
- Porte ECR | 362 | 279 | −22,9%
- Profondità | 1351 | 1141 | −15,5%
- Grado di troncamento scelto sui dati di selezione e valutato su holdout disgiunto; IC Newcombe 95% dell'incremento: [12,73; 16,99] punti.
- Istanza favorevole: r = 4 produce fasi rappresentabili esattamente con due bit.
- Meno porte danno più informazione utile quando il rumore evitato supera la perdita di precisione di fase.
- Immagini nella slide: 2

### Slide 18 — DR5 · AQFT su N = 21 e QPE isolata

- Ruolo: Risultato DR5 (N = 21 e QPE)
- Shor su N = 21
- Porte ECR: 49 661 → 23 178 troncando l'aritmetica
- Successo ideale: 0,4667 → 0,4013
- Con rumore, a budget ridotto: nessun vantaggio dimostrato
- QPE isolata
- 9 stime su 9 a favore della variante troncata, 6 intervalli su 9 interamente sopra zero; evidenza esplorativa, senza correzione simultanea
- Il grado AQFT va scelto per istanza e per regime di rumore.
- QPE isolata: differenza di successo AQFT − QFT piena su holdout, con IC Newcombe individuali al 95%
- Immagini nella slide: 2

### Slide 19 — Risposte alle domande di ricerca

- Ruolo: Conclusioni: risposte alle domande
- DR | Risposta | Evidenza principale
- DR1 | TOP-K è utile; il filtro ML considerato non aggiunge valore operativo | TOP-4: 1,00 iterazioni medie nei due scenari; M2 perde contro la propria ablazione
- DR2 | La QEC sopprime l'errore sotto soglia; il beneficio cresce con la distanza | Steane: pendenza 1,94; surface code: soglia 0,86% (Z) e 0,81% (X)
- DR3 | Il ML è utile come correttore residuale; il decoder conta anche fra codici diversi | p_L ridotto del 15,6–17,6% a d = 3 con crosstalk; Gross code migliore per p ≥ 0,75%
- DR4 | Il successo di Shor decresce con p_g fino al pavimento del post-processing | Da 0,7489 senza rumore a circa 0,245 per rumore elevato (63/256)
- DR5 | L'AQFT aiuta quando le porte evitate compensano la perdita di fase | N = 15: 0,4792 → 0,6279, ECR 362 → 279; beneficio non dimostrato su N = 21
- Immagini nella slide: 1

### Slide 20 — Conclusione centrale

- Ruolo: Conclusione centrale
- La complessità aggiuntiva è giustificata solo quando agisce sul collo di bottiglia effettivo e produce un beneficio misurabile rispetto a una baseline adeguata.
- TOP-K
- usa meglio informazione già disponibile
- QEC
- cambia l'ordine dell'errore, ma solo sotto soglia
- Decoder appreso
- recupera struttura assente dal modello analitico
- AQFT
- aiuta se il costo evitato supera la perdita algoritmica
- Immagini nella slide: 1

### Slide 21 — Limiti e sviluppi futuri

- Ruolo: Limiti e sviluppi futuri
- Limiti dello studio
- Scala: campagne simulate; N = 15 con r = 4 è un'istanza favorevole a TOP-K e AQFT
- Rumore: modello uniforme e stazionario; controlli hardware-aware su snapshot offline, non su QPU live
- QEC: surface code studiato come memoria, non uno Shor fault-tolerant; decoder appreso MLP denso
- Inferenza: sweep e benchmark QPE esplorativi, senza correzione simultanea
- Sviluppi futuri, in ordine di priorità
- 1
- Hardware: ripetere Shor e AQFT su QPU, con simulazione dalla calibrazione coeva
- 2
- Scala: variare separatamente N, ordine r, qubit di conteggio e aritmetica
- 3
- Fault tolerance: sostituire p_g con gate logici, cicli QEC e decoder espliciti
- 4
- Decoder e codici: modelli strutturali contro BP+OSD; Gross code a livello di circuito
- 5
- Costo circuitale: ottimizzare aritmetica modulare e AQFT, verificando il successo finale
- Immagini nella slide: 1

### Slide 22 — Grazie / per l'attenzione

- Ruolo: Chiusura con i takeaway (resta a schermo durante le domande)
- 1
- Post-processing: con TOP-4 bastano 1,00 iterazioni medie; il filtro ML non aggiunge valore
- 2
- QEC e decoder: sotto soglia la distanza sopprime l'errore; l'ibrido riduce p_L del 15,6–17,6% a d = 3
- 3
- AQFT: su N = 15 il successo sale da 0,4792 a 0,6279 con 83 porte ECR in meno
- Claudio Dragotta
- Corso di Laurea Magistrale in Ingegneria dei Sistemi Intelligenti · A.A. 2025/2026
- Immagini nella slide: 1

### Slide 23 — Demo interattiva: Shor con e senza rumore

- Ruolo: Riserva: demo interattiva
- Ideale e rumoroso
- Stesso circuito per N = 15, senza rumore e con il preset UC1: le frecce sulle sfere di Bloch dei qubit di conteggio si accorciano, lo stato perde coerenza.
- Dove entra il rumore
- 70 porte SX con errore a un qubit, 224 CX con errore a due qubit, 302 RZ virtuali senza rumore, 8 misure con errore di lettura.
- Demo web illustrativa con modello di rumore uniforme: non è una misura su hardware. / shor-demo-6knp.onrender.com
- Immagini nella slide: 3
