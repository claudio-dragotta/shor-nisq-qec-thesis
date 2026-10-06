# Prompt: presentazione di laurea in 11 slide

## RUOLO E OBIETTIVO

Sei un progettista di presentazioni per tesi di laurea magistrale in ingegneria. Devi
costruire la presentazione per la discussione della mia tesi: **11 slide principali** che
seguono il template ufficiale del corso, più **10 slide di riserva** per le domande.

Questo prompt contiene già titoli, testi, numeri, immagini e posizioni di ogni slide. Ogni
numero è stato verificato sui capitoli della tesi (file_latex_v2) ed è riportato con la sua
fonte. Il tuo compito è impaginarli bene, non riscriverli. Se per motivi di spazio devi
accorciare un testo, accorcialo senza cambiare numeri, unità o qualificazioni (per esempio
"nel modello code-capacity" o "su holdout"). **Non aggiungere numeri, citazioni o figure che
non trovi qui.** Se ti manca un dato, lascia un segnaposto tra parentesi quadre e
segnalamelo.

## DATI DELLA TESI

- Titolo ufficiale (in inglese, come nel frontespizio): **Shor's Algorithm under Noise:
  Machine-Learning Ablation, Quantum Error Correction, and Approximate QFT**
- Laureando: Claudio Dragotta
- Relatore: Prof. Paolo Soda
- Correlatore: Prof. Floriano Caprio
- Università Campus Bio-Medico di Roma, Facoltà Dipartimentale di Ingegneria, CdLM in
  Ingegneria dei Sistemi Intelligenti (LM-32)
- A.A. 2025/2026, sessione di laurea di ottobre 2026
- Durata assegnata: **[__ minuti]** (da completare). Le 11 slide principali devono starci con
  circa il 10% di margine. Le note del relatore, a fine prompt, riportano un tempo indicativo
  per slide, calcolato su 12 minuti: riproporzionalo sul tempo vero.

## FONTI, IN ORDINE DI AUTORITÀ

1. `file_latex_v2/capitoli/`: Capitolo1Finale … Capitolo5Finale e Capitolo6Sintesi (il file
   Capitolo6Finale include solo Capitolo6Sintesi). Ogni numero in slide deve comparire lì.
2. `Extra/laurea_amministrativo/info_laurea_ottobre/Template_Presentazione_Tesi_ISI_UCBM.docx`:
   struttura e regole di qualità.
3. `Extra/laurea_amministrativo/info_laurea_ottobre/Info Slide Tesi di Laurea.pdf`:
   vincoli dell'Ufficio Audiovisivi.
4. Immagini: questa cartella, `Extra/slide/immagini_presentazione_11/`. Video della demo:
   `Extra/video_demo/demo_shor_it.mp4`.

Da NON usare in nessun caso:
- le immagini "ChatGPT Image …" in `Extra/slide/slide presentazione tesi/`;
- il mockup di luglio `Extra/slide/mockup_tesi_shor_dettagliato.pptx`;
- la figura `fig_istogrammi_qpe.pdf`: viene da un capitolo che non fa più parte della tesi
  finale;
- qualunque numero precedente alla campagna v2, per esempio 162 CX, ρ = 6,4, soglia 0,9%
  come valore di fit, 18–21% come "riduzione" del decoder;
- i numeri della demo web (seed 42, preset UC1): non sono risultati della tesi.

## VINCOLI DELL'UFFICIO AUDIOVISIVI (obbligatori)

- Formato **16:9**. Software: **PowerPoint** o compatibile, **in locale**: il PDF vieta i
  programmi online, quindi niente Google Slides, Canva o simili.
- **Non usare layout UCBM già impostati**: costruisci le slide su un layout vuoto. Il logo UCBM
  si può inserire come immagine, non come tema.
- Font standard: **Arial** ovunque. **Nessuna transizione e nessuna animazione.**
- Nome del file: **`Dragotta Claudio.pptx`**, esportato anche come **`Dragotta Claudio.pdf`**.
- Video: solo **.mp4**, al massimo uno per slide, riproduzione **automatica** (non al clic),
  da consegnare insieme alle slide entro il giorno prima della discussione.

## SISTEMA GRAFICO

Lavora su una tela di riferimento di **1920 × 1080 px**. In PowerPoint (13,333 × 7,5 pollici)
**1 px corrisponde a 0,5 pt**: 40 px = 20 pt.

### Colori

| Token | Valore | Uso |
|---|---|---|
| Sfondo | `#FFFFFF` | tutte le slide |
| Blu titolo | `#125C97` | titoli, serie principale dei grafici, bordi delle schede |
| Linea | `#3F73B0` | linea sottile sotto il titolo, 2 px |
| Blu scuro | `#0B2F5B` | cerchi numerati dei blocchi, numeri grandi, intestazioni di tabella |
| Riquadro chiaro | `#E8EFF6` | fasce di sintesi, righe alterne delle tabelle |
| Testo | `#1F2933` | corpo |
| Testo secondario | `#5B6573` | didascalie, fonti, piè di pagina |
| Arancio | `#D9822B` | solo seconda serie dei grafici (UC2, ibrido); mai per il testo |

Non introdurre altri colori. Il rosso non serve: i risultati negativi si dichiarano con le
parole, non con il colore.

### Griglia e misure (px sulla tela 1920 × 1080)

- Margini laterali: 96 px. Area contenuto: x 96–1824, y 250–1000.
- **Titolo**: x 96, y 48, larghezza massima 1500, Arial grassetto **52 px**, colore `#125C97`,
  al massimo **due righe**, interlinea 1,1.
- **Linea** sotto il titolo: y 214, da x 96 a x 1824, 2 px, `#3F73B0`.
- **Etichetta di sezione** in alto a destra, allineata a destra a x 1700, y 64: formato
  `Sezione | n`, Arial 24 px, `#5B6573`, con la sezione in grassetto.
- **Logo UCBM** (`logo_ucbm.png`): in alto a destra, x 1724–1824, altezza 96 px, proporzioni
  originali.
- **Piè di pagina** a y 1036: a sinistra "Claudio Dragotta · Shor's Algorithm under Noise",
  a destra "n / 11"; Arial 22 px, `#5B6573`. Assente in copertina. Nelle riserve il numero
  diventa "R n".
- **Schede**: fondo bianco, bordo 2 px `#125C97`, raggio 12 px, padding interno 32 px.
- **Blocchi numerati**: cerchio pieno `#0B2F5B` di 64 px con cifra bianca grassetta 32 px,
  a sinistra del titolo del blocco.
- **Fasce di sintesi**: fondo `#E8EFF6`, nessun bordo, padding 24 px, testo grassetto
  `#0B2F5B`.

### Testo

- Corpo: **40 px** (20 pt), mai meno. Titoletti delle schede: 40 px grassetto.
- Numeri grandi (KPI): 88–96 px grassetto `#0B2F5B`, con l'etichetta sotto a 30 px.
- Solo **didascalie, fonti e celle di tabelle semplici** possono scendere a **26–30 px**.
- Niente paragrafi: parole chiave, frasi brevi, numeri. Indicativamente **≤ 40 parole per
  slide**, titolo, didascalie e piè di pagina esclusi. Le slide 7 e 8 sono tabelle e possono
  superare il limite, con celle di poche parole.
- **Virgola decimale** ovunque (0,86%, non 0.86%). Separatore delle migliaia: spazio sottile
  (49 661).
- Notazione: p (errore fisico), p_L (errore logico), p_g (proxy di errore per gate),
  p_th (soglia), d (distanza). Scrivi i pedici come veri pedici: p<sub>L</sub>,
  p<sub>g</sub>, p<sub>th</sub>.
- Il titolo dice **il messaggio**, non l'argomento.

### Immagini e grafici

- I file `s##_…` sono già pronti per le slide: Arial, virgola decimale, testo leggibile
  quando il grafico occupa almeno 1000 px di larghezza. **Non ritagliarli, non deformarli e
  non ricolorarli.**
- I file `orig_…` sono le figure originali della tesi: punto decimale e testo piccolo. Servono
  come riferimento per ridisegnare gli schemi con le forme native di PowerPoint, **non** vanno
  incollati nelle slide principali.
- I file `r_…` servono alle slide di riserva.
- Gli schemi (pipeline, flussi) vanno **ridisegnati con forme native** nello stile delle schede,
  non incollati come immagini.

## IMMAGINI DISPONIBILI IN QUESTA CARTELLA

| File | Contenuto | Fonte nella tesi | Dove |
|---|---|---|---|
| `s01_copertina_sfera_bloch.png` | sfera di Bloch, sfondo trasparente | Fondamenti, `bloch_sphere.png` | slide 1 |
| `logo_ucbm.png` | logo dell'Ateneo | frontespizio | tutte tranne la copertina |
| `s03_shor_successo_vs_pg.png` | successo di Shor contro p_g, con linee 3/4 e 63/256 | Tab. 5.15, Fig. 5.7 | slide 3 |
| `s09_iterazioni_primo_successo.png` | iterazioni medie TOP-1 / TOP-4 / M2, UC1 e UC2 | Tab. 5.3, Fig. 5.1 | slide 9 |
| `s10_decoder_bposd_ibrido.png` | guadagno di BP+OSD e ibrido rispetto a MWPM | Tab. 5.12, Fig. 5.6 | slide 10 |
| `r_aqft_n15_holdout.png` | successo su holdout contro il grado k_QPE, N = 15 | Tab. 5.18, Fig. 5.9 | riserva R6 |
| `r_surface_code_soglia_orig_5_4.png` | p_L contro p, d = 3–9, basi Z e X | Fig. 5.4 | riserva R2 |
| `r_aqft_qpe_holdout_orig_5_10.png` | ΔP AQFT − QFT nei 9 benchmark QPE | Fig. 5.10 | riserva R7 |
| `r_shor_cumulativa_orig_5_8.png` | probabilità cumulativa dopo k esecuzioni | Fig. 5.8 | riserva R5 |
| `orig_3_2_pipeline_shor.png` | pipeline di Shor in quattro fasi | Fig. 3.2 | modello per slide 3 e 5 |
| `orig_3_3_sorgenti_rumore.png` | dove agisce il rumore | Fig. 3.3 | modello per slide 3 |
| `orig_3_5_disegno_sperimentale.png` | DR1–DR5 e loro test | Fig. 3.5 | modello per slide 5 e 8 |
| `orig_4_2_pipeline_appaiata.png` | un istogramma → TOP-1, TOP-4, M2 | Fig. 4.2 | modello per slide 6 |
| `orig_4_3_flusso_decoder.png` | flusso dei decoder | Fig. 4.3 | modello per slide 6 |
| `orig_4_1_architettura_piattaforma.png` | piattaforma a quattro livelli | Fig. 4.1 | modello per slide 7 |
| `orig_5_1_…`, `orig_5_6_…`, `orig_5_7_…`, `orig_5_9_…` | originali dei grafici rigenerati | Cap. 5 | solo confronto |

`genera_immagini.py` rigenera tutti i file `s##_` e `r_` dalle tabelle del Capitolo 5.

---

## LE 11 SLIDE PRINCIPALI

Ogni slide riporta: etichetta, titolo, layout, testo esatto, immagine e note del relatore.
Le note vanno nel campo "Note" di PowerPoint, **non** sulla slide.

### Slide 1 — Copertina

- Etichetta: nessuna. Piè di pagina: nessuno. Logo UCBM in alto a destra come nelle altre.
- Layout: colonna di testo a sinistra (x 96–1150), sfera di Bloch a destra.
- Testo, dall'alto:
  1. y 150, 28 px maiuscoletto `#5B6573`: "Tesi di Laurea Magistrale · Ingegneria dei
     Sistemi Intelligenti (LM-32)"
  2. y 230, **80 px grassetto `#0B2F5B`**, due righe: "Shor's Algorithm / under Noise"
  3. y 440, 40 px `#125C97`: "Machine-Learning Ablation, Quantum Error Correction, and
     Approximate QFT". Le parole chiave del titolo lungo sono Shor, Noise, Ablation, Error
     Correction e QFT: le prime due stanno nella riga grande, le altre restano in questa.
  4. y 600, tre righe in coppia etichetta/nome; etichetta 26 px maiuscoletto `#5B6573`, nome
     36 px `#1F2933`:
     - LAUREANDO — Claudio Dragotta
     - RELATORE — Prof. Paolo Soda
     - CORRELATORE — Prof. Floriano Caprio
  5. y 960, 26 px `#5B6573`: "Università Campus Bio-Medico di Roma · A.A. 2025/2026 ·
     Sessione di laurea, ottobre 2026"
- Immagine: `s01_copertina_sfera_bloch.png`, centrata in x 1200–1824, altezza circa 640 px,
  verticalmente centrata. È **l'unico** elemento grafico: niente picchi, niente collage.
- Note (≈ 20 s): "Buongiorno. Presento una tesi sull'algoritmo di Shor in presenza di rumore
  e su tre modi di contenerlo, ciascuno valutato contro una baseline esplicita."

### Slide 2 — Tesi in 30 secondi

- Etichetta: **Sommario | 2**
- Titolo: **"Tre livelli di intervento contro il rumore, ciascuno misurato contro la propria
  baseline"**
- Layout: tre schede affiancate (larghezza 528 px ciascuna, spazio 72 px, y 280–800), ognuna
  con cerchio numerato e titoletto; sotto, fascia di sintesi a tutta larghezza, y 850–960.
- Testo:
  - ① **Problema** — "Il rumore porta il successo di Shor da 0,75 a ≈ 0,245: il livello
    dell'ipotesi casuale"
  - ② **Approccio** — "Tre livelli: dopo la misura, durante il calcolo, nel circuito. Baseline
    esplicite, stessi campioni"
  - ③ **Evidenza** — tre righe brevi:
    "TOP-4 senza ML: 1,00 iterazioni" ·
    "Decoder ibrido: −15,6–17,6% p<sub>L</sub>" ·
    "AQFT, N = 15: 0,479 → 0,628"
  - Fascia: **"La complessità aggiuntiva è giustificata solo se agisce sul collo di bottiglia
    effettivo."**
- Fonti dei numeri: 0,7489 e ≈ 0,245 (Cap. 6, DR4); 1,00 (Tab. 5.3); 15,6–17,6% (Tab. 5.11);
  0,4792 → 0,6279 (Tab. 5.19).
- Note (≈ 40 s): "Il problema: il successo di Shor scende fino al livello casuale. Intervengo
  su tre livelli e confronto ogni tecnica con la propria baseline. Un risultato per livello:
  TOP-4 basta senza il classificatore, il decoder ibrido aiuta quando c'è struttura non
  modellata, la QFT approssimata migliora N = 15. Il filo conduttore è nella fascia in basso."

### Slide 3 — Introduzione e contesto

- Etichetta: **Introduzione | 3**
- Titolo: **"Shor fattorizza in tempo polinomiale, ma il rumore ne porta il successo al livello
  casuale"**
- Layout: colonna sinistra x 96–700 con la pipeline; destra x 760–1824 con il grafico.
- Colonna sinistra, dall'alto:
  - riga 32 px grassetto `#0B2F5B`: "Minaccia RSA: tempo polinomiale contro sub-esponenziale
    (GNFS)"
  - pipeline **verticale** di quattro schede compatte (altezza 120 px, frecce `#3F73B0` tra
    l'una e l'altra), testo 30 px:
    1. "Pre-processing classico · scelta di a, gcd(a, N)"
    2. "Period finding quantistico · esponenziazione modulare + QPE"
    3. "QFT⁻¹ e misura"
    4. "Post-processing classico · frazioni continue, gcd"
  - le schede 2 e 3 hanno bordo più spesso (4 px) e, a destra, un'etichetta 26 px
    `#0B2F5B` "qui agisce il rumore", collegata con una parentesi graffa sottile.
- Colonna destra: `s03_shor_successo_vs_pg.png`, larghezza 1064 px. Didascalia sotto, 26 px
  `#5B6573`: "N = 15, a = 7 · 20 × 4096 shot per punto · errore Pauli dopo ogni gate
  compilato, modello illustrativo · Tab. 5.15"
- Riferimento bibliografico in basso a sinistra, 24 px: "Shor, FOCS 1994"
- Numeri della curva, se servono a voce: 0,7489 senza rumore; 0,5651 a p<sub>g</sub> = 0,01;
  0,4518 a 0,02; 0,2953 a 0,05; pavimento 63/256 ≈ 0,2461 da p<sub>g</sub> ≈ 0,1 in su.
- Note (≈ 75 s): "Shor riduce la fattorizzazione alla ricerca del periodo; RSA si basa sulla
  difficoltà di questo problema. La parte quantistica è il period finding; il rumore agisce
  lì e nella QFT inversa. Il grafico misura quanto: con N = 15 il successo per misura parte da
  0,75 e scende verso 63/256, il valore che la verifica classica concederebbe anche a esiti
  casuali. p<sub>g</sub> è un proxy per gate, non un tasso logico."

### Slide 4 — Stato dell'arte e gap

- Etichetta: **Stato dell'arte | 4**
- Titolo: **"Ogni tecnica promette un guadagno, ma il guadagno può avere un'altra causa"**
- Layout: tabella a tutta larghezza (y 270–800), tre righe più intestazione; sotto, fascia di
  sintesi y 850–960.
- Tabella: intestazione fondo `#0B2F5B`, testo bianco grassetto 30 px; celle 30 px; prima
  colonna grassetta `#125C97`; righe alterne `#E8EFF6`. Colonne 30% / 30% / 40%.

  | Famiglia | Promessa | Rischio da controllare |
  |---|---|---|
  | Post-processing e ML | sfruttare l'informazione residua nell'istogramma | il guadagno viene dai candidati provati, non dal modello |
  | QEC e decoder appresi | sopprimere l'errore logico | baseline analitica debole; soglia valida solo per la memoria |
  | QFT approssimata (AQFT) | meno porte, meno rumore | perdita di precisione di fase |

- Fascia: **"Rimane aperto il problema di valutare ogni tecnica contro la baseline corretta,
  sulla metrica finale."**
- Fonti in basso, 24 px `#5B6573`: "Yang e Markidis 2026 · Bausch et al., Nature 2024 · Roffe
  et al. 2020 · Bravyi et al., Nature 2024 · Barenco et al. 1996"
- Note (≈ 60 s): "Per ogni famiglia c'è una promessa e un rischio. Il ML può sembrare utile
  quando il merito è di aver provato più candidati. Un decoder appreso può vincere solo perché
  la baseline è debole. L'AQFT toglie porte ma anche precisione. Da qui la domanda della tesi."

### Slide 5 — Metodo I: soluzione proposta

- Etichetta: **Metodo | 5**
- Titolo: **"La tesi interviene in tre punti della pipeline e li valuta con cinque domande di
  ricerca"**
- Layout: fascia orizzontale con la pipeline di Shor (quattro schede compatte in fila,
  y 290–410, testo 30 px: "Pre-processing", "Period finding + QPE", "QFT⁻¹ e misura",
  "Post-processing"). Sotto, tre schede grandi (y 480–860) con cerchio numerato, ognuna
  collegata con una freccia verticale `#3F73B0` al punto della pipeline su cui agisce.
- Testo delle schede:
  - ① **Nel circuito** (freccia su "QFT⁻¹ e misura") — "DR5 · AQFT: meno rotazioni, meno
    porte"
  - ② **Durante il calcolo** (freccia su "Period finding + QPE") — "DR2 · codici QEC e soglia" /
    "DR3 · decoder analitici, appresi, Gross code"
  - ③ **Dopo la misura** (freccia su "Post-processing") — "DR1 · TOP-K e ablazione del ML"
  - Ordina le schede da sinistra a destra secondo la posizione della freccia nella pipeline:
    ② Durante il calcolo, ① Nel circuito, ③ Dopo la misura. I numeri seguono l'ordine di
    lettura.
- Fascia di sintesi a tutta larghezza, y 900–980: "DR4 · sensibilità di Shor al proxy
  p<sub>g</sub>: misura il problema che i tre livelli affrontano"
- Note (≈ 60 s): "Tre livelli. Dopo la misura sfrutto meglio l'istogramma. Durante il calcolo
  proteggo l'informazione con la QEC e studio i decoder. Nel circuito riduco le porte con
  l'AQFT. La quarta domanda misura la sensibilità di Shor e motiva le altre. Le cinque
  campagne usano metriche diverse e non vengono sommate."

### Slide 6 — Metodo II: dettaglio tecnico

- Etichetta: **Metodo | 6**
- Titolo: **"Lo stesso istogramma alimenta ogni strategia: l'ablazione isola il contributo del
  classificatore"**
- Layout: schema a sinistra (x 96–1250) ridisegnato da `orig_4_2_pipeline_appaiata.png`;
  colonna destra (x 1310–1824) con due schede piccole impilate.
- Schema, con forme native e testo 30 px:
  - scheda "Shor N = 15 · 1 istogramma da 1024 shot" → tre frecce verso
  - "TOP-1 · 1 candidato", "TOP-4 · 4 candidati", "M2 · SVM + TOP-4" → tutte verso
  - "Frazioni continue + gcd" → "Iterazioni al primo successo"
  - una parentesi graffa tra TOP-4 e M2 con l'etichetta 28 px grassetta `#0B2F5B`:
    "ablazione: differiscono solo per il filtro ML"
- Colonna destra:
  - scheda "**Decoder ibrido**" — "MWPM decide; la rete inverte solo sopra una soglia scelta
    su validation"
  - scheda "**AQFT**" — "grado k scelto su selection, misurato su holdout disgiunto"
- Note (≈ 70 s): "Il cuore del metodo è l'appaiamento. Ogni istogramma viene generato una volta
  e consegnato a tutte e tre le strategie, quindi le differenze dipendono solo dalla regola. M2
  è TOP-4 preceduto da un classificatore: confrontarlo con TOP-4 è l'ablazione. Lo stesso
  principio vale per il decoder ibrido, che parte da MWPM e lo corregge solo quando la rete è
  abbastanza sicura, e per l'AQFT, dove il grado si sceglie su dati separati da quelli di
  verifica."

### Slide 7 — Configurazione I: ambiente e dati

- Etichetta: **Configurazione | 7**
- Titolo: **"Tutto in simulazione, con circuiti validati e un modello di rumore dichiarato"**
- Layout: tre schede affiancate (y 270–900), titoletto 36 px grassetto, contenuto 28–30 px.
- Scheda **Istanze**:
  - "N = 15, a = 7, r = 4 · istanza rumorosa principale"
  - "12 qubit (8 di controllo + 4 di lavoro) · 224 CX · profondità 412"
  - "base rz/sx/x/cx, optimization level 2, seed fissato"
  - "N = 21 (r = 6) e N = 35 (r = 2): validazione ideale; N = 21 anche AQFT esplorativa"
- Scheda **Strumenti**:
  - "Qiskit 2.5 + Aer → Shor"
  - "Stim 1.16 + PyMatching 2.4 → surface code"
  - "scikit-learn → SVM e MLP"
  - "ldpc 2.4.1 → BP+OSD"
  - "CPU · WSL2 Ubuntu 24.04 · Python 3.12"
- Scheda **Rumore (modello illustrativo uniforme)**, come mini-tabella 28 px:

  | | UC1 riferimento | UC2 stress |
  |---|---|---|
  | λ<sub>1q</sub> / λ<sub>2q</sub> | 10⁻³ / 10⁻² | 5×10⁻³ / 5×10⁻² |
  | T1 / T2 | 100 / 80 µs | 50 / 30 µs |
  | readout | 0,02 | 0,05 |

  sotto: "AQFT: snapshot offline FakeSherbrooke, non una QPU reale"
- Fascia di sintesi y 930–990, 28 px: "Riproducibilità: seed, manifest, hash della netlist,
  artefatti JSON"
- Fonti: Cap. 3, Tab. 3.4 e 3.6; Cap. 4, Sez. 4.1 e righe sulla compilazione N = 15.
- Note (≈ 60 s): "Nessun risultato viene da hardware reale. L'istanza principale è N = 15 con
  dodici qubit; N = 21 e 35 servono a validare l'aritmetica. Uso uno strumento per classe di
  circuito: Shor ha rotazioni non-Clifford e va su Aer; i codici di correzione sono circuiti
  Clifford e Stim li campiona in modo efficiente. UC1 e UC2 sono preset uniformi, non la
  calibrazione di un dispositivo."

### Slide 8 — Configurazione II: protocollo di valutazione

- Etichetta: **Configurazione | 8**
- Titolo: **"Baseline, metrica e test sono fissati prima di guardare i risultati"**
- Layout: tabella a tutta larghezza y 270–900; intestazione `#0B2F5B` con testo bianco 28 px;
  celle 28 px; colonna DR grassetta `#125C97`; righe alterne `#E8EFF6`.

  | DR | Confronto | Metrica | Test e campioni |
  |---|---|---|---|
  | DR1 | TOP-1 · TOP-4 · M2 | iterazioni al primo successo | Wilcoxon-Pratt + Holm · 30 repliche × 1024 shot |
  | DR2 | repetition · Steane · surface d = 3–9 | p<sub>L</sub>(p, d), soglia p<sub>th</sub> | fit sotto soglia · 2×10⁵–4×10⁷ shot |
  | DR3 | MWPM · rete · ibrido · BP+OSD | Δp<sub>L</sub> sugli stessi shot | McNemar |
  | DR4 | Shor con p<sub>g</sub> crescente | P<sub>succ</sub>(p<sub>g</sub>) | IC Wilson 95% · 20 × 4096 shot |
  | DR5 | QFT piena · AQFT | P<sub>succ</sub>, porte ECR, profondità | selection/holdout · IC Newcombe 95% |

- Fascia y 930–990, 28 px: "Metriche non convertibili fra loro: p<sub>g</sub> non è
  p<sub>L</sub>"
- Fonti: contratto sperimentale del Cap. 2 (Sez. 2.5), Tab. 3.4, Sez. 5.1–5.5.
- Note (≈ 60 s): "Per ogni domanda la baseline, la metrica e il test sono decisi prima. Dove
  i campioni sono appaiati uso test appaiati: Wilcoxon per le iterazioni, McNemar per i
  decoder. Per l'AQFT il grado si sceglie su una parte dei dati e si misura sull'altra.
  p<sub>g</sub> e p<sub>L</sub> restano separati."

### Slide 9 — Risultati I: evidenza principale

- Etichetta: **Risultati | 9**
- Titolo: **"TOP-4 trova i fattori alla prima iterazione: il beneficio viene dai candidati, non
  dal ML"**
- Layout: grafico a sinistra (x 96–1250); colonna destra (x 1310–1824) con due KPI
  impilati sotto il titoletto 30 px `#5B6573` "Gli altri due livelli".
- Grafico: `s09_iterazioni_primo_successo.png`, larghezza 1150 px. Didascalia 26 px:
  "30 repliche appaiate · 1024 shot per iterazione · max 50 iterazioni · Tab. 5.3"
- Sotto il grafico, una riga 30 px: "M2 è peggiore della propria ablazione: p<sub>Holm</sub> =
  0,0033 (UC1) e 0,0096 (UC2)"
- KPI 1: numero grande **"0,86% · 0,81%"**; etichetta "soglia del surface code, base Z · base
  X · memory experiment"
- KPI 2: numero grande **"0,479 → 0,628"**; etichetta "AQFT su N = 15, successo su holdout ·
  ECR 362 → 279"
- Valori esatti se te li chiedono: TOP-1 1,37 (UC1) e 1,50 (UC2); TOP-4 1,00 e 1,00; M2 1,50
  e 1,37; TOP-4 contro TOP-1 p<sub>Holm</sub> 0,0024 e 0,0015; SVM F1 0,919 / 0,923, AUC 0,965
  / 0,958; AQFT +14,87 punti, IC Newcombe 95% [12,73; 16,99].
- Note (≈ 90 s): "Il risultato centrale. TOP-4 trova i fattori alla prima iterazione in tutte
  le trenta repliche, in entrambi gli scenari. Aggiungere il classificatore davanti a TOP-4 non
  aiuta, anzi peggiora significativamente, pur avendo F1 sopra 0,9: predire bene non basta. A
  destra gli altri due livelli: il surface code ha soglia intorno allo 0,8%, sotto la quale
  aumentare la distanza riduce l'errore; l'AQFT su N = 15 porta il successo da 0,48 a 0,63 con
  83 porte ECR in meno."

### Slide 10 — Risultati II: analisi e limiti

- Etichetta: **Risultati | 10**
- Titolo: **"Il ML aiuta come correttore residuale, non come sostituto, e solo dentro un
  perimetro preciso"**
- Layout: grafico a sinistra (x 96–1150); colonna destra (x 1210–1824) con quattro righe
  brevi, 34 px, ognuna preceduta da un quadratino `#0B2F5B`; in basso fascia dei limiti a
  tutta larghezza.
- Grafico: `s10_decoder_bposd_ibrido.png`, larghezza 1050 px. Didascalia 26 px: "Surface code,
  memory experiment, rumore circuit-level con crosstalk simulato · Tab. 5.12"
- Righe a destra:
  - "Ibrido, d = 3: p<sub>L</sub> −15,6–17,6% rispetto a MWPM"
  - "d = 7: nessun vantaggio significativo"
  - "BP+OSD, d = 5 senza crosstalk: −25,5%"
  - "AQFT su N = 21: −53,3% ECR, beneficio non dimostrato"
- Fascia dei limiti y 900–990, 28 px: "**Limiti** · solo simulazioni · N = 15 con r = 4 è
  un'istanza favorevole · p<sub>g</sub> non è p<sub>L</sub> · Gross code solo nel modello
  code-capacity"
- Regola: 15,6–17,6% è una **riduzione relativa** di p<sub>L</sub> sulle quattro intensità di
  crosstalk da 0,005 a 0,04. Non scrivere 18–21%: è il rapporto di guadagno 1,185–1,213, cioè
  la grandezza sull'asse del grafico. Se serve spiegarlo, nella didascalia: "asse: rapporto
  p<sub>L</sub><sup>MWPM</sup>/p<sub>L</sub>; 1,185–1,213 equivale a una riduzione di
  15,6–17,6%".
- Note (≈ 90 s): "Il grafico separa due fonti di guadagno. In blu BP+OSD: un decoder analitico
  migliore vince quando il modello di rumore è corretto, e perde il vantaggio quando compare il
  crosstalk. In arancio l'ibrido: a distanza 3 recupera la struttura che MWPM non rappresenta,
  ma a distanza 7 il vantaggio sparisce. Una rete usata da sola non batte MWPM. Anche l'AQFT ha
  un perimetro: su N = 21 dimezza le porte ma il beneficio non è dimostrato. E tutto è
  simulazione su un'istanza favorevole."

### Slide 11 — Conclusioni e contributo personale

- Etichetta: **Conclusioni | 11**
- Titolo: **"La complessità aggiuntiva paga solo quando agisce sul collo di bottiglia
  effettivo"**
- Layout: tre schede affiancate (y 270–960), titoletto 36 px grassetto con cerchio numerato.
  Questa slide resta a schermo durante le domande: **non** aggiungere una slide "Grazie".
- Testo, 32 px:
  - ① **Cosa è stato dimostrato**
    - "Più candidati, non il ML, riducono le iterazioni"
    - "QEC e decoder appresi aiutano sotto soglia o con struttura non modellata"
    - "AQFT: +14,87 punti su N = 15, non dimostrata su N = 21"
  - ② **Il mio contributo**
    - "Protocollo appaiato con ablazione"
    - "Piattaforma riproducibile: seed, manifest, hash"
    - "Demo web interattiva"
  - ③ **Prossimo passo**
    - "Hardware reale con calibrazione coeva"
    - "Catena fault-tolerant che sostituisca p<sub>g</sub>"
- Note (≈ 45 s): "Tre messaggi: il beneficio del post-processing viene dai candidati; QEC e ML
  servono solo nel loro regime; l'AQFT dipende dall'istanza. Il mio contributo è soprattutto
  metodologico: confronti appaiati, ablazione e una piattaforma che rende ogni numero
  verificabile. Il passo successivo è l'hardware e una catena fault-tolerant completa. Grazie,
  sono a disposizione per le domande."

---

## SLIDE DI RISERVA (dopo la 11)

Stesso sistema grafico. Etichetta **`Riserva | R n`**, piè di pagina "R n". Ogni riserva
risponde a una domanda prevedibile e ha un titolo-messaggio. Se nella presentazione esistente
c'è già una slide equivalente con gli stessi numeri, riusala e aggiorna solo etichetta e
numerazione; altrimenti costruiscila con i dati qui sotto.

**R1 — DR1 nel dettaglio.** Titolo: "Il classificatore predice bene TOP-1, ma non riduce il
costo della fattorizzazione". Tabella: SVM UC1 F1 0,919, accuratezza 0,895, AUC 0,965; UC2 F1
0,923, accuratezza 0,888, AUC 0,958 (Tab. 5.2). Confronto appaiato (Tab. 5.3): successi 30/30
per tutte le strategie; p<sub>Holm</sub> rispetto a TOP-1: TOP-4 0,0024 / 0,0015; M2 0,7314 /
0,0874. Dataset: 2000 istogrammi per scenario, split 60/20/20.

**R2 — DR2 surface code.** Titolo: "Sotto soglia aumentare la distanza riduce p<sub>L</sub>;
sopra soglia lo aumenta". Immagine `r_surface_code_soglia_orig_5_4.png`. Numeri: fit
p<sub>th</sub> 0,86% (Z) e 0,81% (X) (Tab. 5.7), punti p ≤ 6×10⁻³, RMS 0,08 in ln p<sub>L</sub>; a p =
2×10⁻³ in base Z p<sub>L</sub> da 1,94×10⁻³ (d = 3) a 2,01×10⁻⁵ (d = 9). Repetition:
p<sub>L</sub> = 3p² − 2p³. Steane: pendenza 1,94, pseudo-soglia ≈ 0,08. Nota a piè di slide:
"l'incrocio visivo nella figura (≈ 0,9% Z, ≈ 0,7% X) è un controllo; la stima è il fit". La
figura ha il punto decimale: segnalalo nella didascalia o chiedimi di rigenerarla.

**R3 — DR3 decoder ibrido.** Titolo: "Con crosstalk l'ibrido riduce p<sub>L</sub> a d = 3; a
d = 5 il margine è piccolo". Tabella (Tab. 5.11), riduzione relativa rispetto a MWPM: d = 3 →
15,6% / 16,8% / 17,6% / 15,9% a crosstalk 0,005 / 0,01 / 0,02 / 0,04; d = 5 → 1,1% / 3,2% /
2,8% / 0,5%. d = 7: nessun vantaggio significativo. Test: McNemar sugli stessi shot.

**R4 — Gross code (M16).** Titolo: "Nel modello code-capacity il Gross code protegge 12 qubit
logici con 144 qubit di dato". Tabella (Tab. 5.14): a q = 1% Gross 1,01×10⁻⁶,
12 patch d = 11 (1452 qubit di dato) 1,15×10⁻⁵, 12 patch d = 13 (2028) 1,63×10⁻⁶; migliore di
d = 13 per q ≥ 0,75%, compatibile a 0,5%, peggiore a 0,2–0,3%. Decoder BP+OSD seriale: corregge
tutte le 498 685 189 configurazioni di peso ≤ 5; il parallelo falliva già con 3 errori ed era
circa 100 volte peggiore a q = 1%. Limite obbligatorio sulla slide: "solo code-capacity, soli
qubit di dato; con le ancille 288 contro 4044; non confrontabile con le soglie circuit-level".

**R5 — DR4 sensibilità di Shor.** Titolo: "Ripetere l'esecuzione compensa un run meno
affidabile, ma non elimina il costo del rumore". Immagini `s03_shor_successo_vs_pg.png` e
`r_shor_cumulativa_orig_5_8.png`. Formula P(k) = 1 − (1 − P<sub>succ</sub>)<sup>k</sup>.
Limite: "p<sub>g</sub> è un proxy fenomenologico per gate, non un tasso logico QEC".

**R6 — DR5 AQFT su N = 15.** Titolo: "Su N = 15 il grado scelto in selezione migliora
l'holdout e riduce le porte". Immagine `r_aqft_n15_holdout.png`. KPI: successo 0,4792 → 0,6279
(+14,87 punti, IC Newcombe 95% [12,73; 16,99]); ECR 362 → 279 (−22,9%); profondità 1351 → 1141
(−15,5%). Limite: "r = 4 dà fasi esatte su due bit: istanza favorevole".

**R7 — DR5 AQFT su N = 21 e QPE.** Titolo: "Su N = 21 meno porte non bastano; nella QPE isolata
l'AQFT è favorevole ma esplorativa". Numeri: N = 21 ECR 49 661 → 23 178 (−53,3%), successo
ideale 0,4667 → 0,4013 (−6,54 punti), test rumorosi con tutti gli intervalli che includono lo
zero. QPE: 9/9 stime favorevoli, 6/9 IC individuali sopra zero, massimo +12,55 punti su 10
qubit, nessuna correzione simultanea. Immagine `r_aqft_qpe_holdout_orig_5_10.png` (punto
decimale: segnalalo).

**R8 — Risposte alle domande di ricerca.** Titolo: "Ogni domanda ha una risposta, un'evidenza
e un limite". Tabella DR | Risposta | Evidenza | Limite, presa da Tab. 6.1 del Capitolo 6,
abbreviando le celle senza cambiare i numeri.

**R9 — Limiti e sviluppi futuri.** Titolo: "I limiti sono dichiarati e indicano l'ordine dei
prossimi passi". Due colonne. Limiti: scala e validità esterna; rumore uniforme stazionario e
snapshot offline; Steane con sindrome ideale, surface code come memoria, MLP denso; sweep e QPE
esplorativi senza correzione simultanea. Sviluppi, in ordine: hardware con calibrazione coeva;
variare N e r separatamente; catena fault-tolerant che sostituisca p<sub>g</sub>; decoder
strutturali contro BP+OSD e Gross code a livello di circuito; riduzione controllata del costo
circuitale (Cap. 6, Sez. 6.3–6.4).

**R10 — Demo interattiva.** Titolo: "La demo web mostra la pipeline di Shor passo per passo".
Video `Extra/video_demo/demo_shor_it.mp4` (1920 × 1080, circa 1:59, senza audio), inserito a
tutta area, **riproduzione automatica**, un solo video nella slide. Dicitura fissa 26 px sotto
il video: "Numeri della demo: seed 42, preset UC1, modello illustrativo. Non sono risultati
della tesi. N = 21 e N = 35 sono mostrati solo nella vista ideale."

---

## REGOLE SUI CONTENUTI

- La riduzione del decoder ibrido è **15,6–17,6%** (riduzione relativa di p<sub>L</sub> a
  d = 3). Mai 18–21%: è il rapporto di guadagno, una grandezza diversa.
- p<sub>g</sub> è un proxy per gate e non va mai convertito in p<sub>L</sub>. Le soglie QEC
  valgono per i memory experiment, non per Shor.
- Il Gross code si confronta **solo nel modello code-capacity**.
- Tutto è simulazione: "modello illustrativo", **mai "realistico"**.
- Dichiara i risultati negativi: il classificatore non migliora TOP-4, la rete da sola non
  sostituisce MWPM, l'AQFT non è dimostrata su N = 21, nessun vantaggio significativo a d = 7.
- N = 15 con r = 4 è un'istanza favorevole sia per TOP-K sia per l'AQFT: dillo dove serve.
- Non inventare numeri, citazioni o figure.

## COME PROCEDERE

1. Leggi questo prompt, il template e i vincoli dell'Ufficio Audiovisivi. Mandami **solo i
   titoli delle 11 slide e delle 10 riserve** e aspetta il mio ok.
2. Costruisci le 11 slide principali e le riserve, con le note del relatore.
3. Controlli prima di consegnare:
   - ogni cifra contro la fonte indicata accanto;
   - anteprima di ogni slide: nessun testo sotto la dimensione minima, nessun riquadro che
     trabocca, nessuna sovrapposizione fra testo e immagini, titoli entro due righe;
   - nessuna animazione o transizione; Arial ovunque; video in riproduzione automatica;
   - parole per slide principale ≤ 40 circa, escluse le tabelle delle slide 7 e 8;
   - virgola decimale ovunque, incluse le tabelle.
4. Alla fine dimmi in poche righe cosa hai abbreviato rispetto a questo prompt, quali
   segnaposto restano aperti e cosa devo verificare io.
