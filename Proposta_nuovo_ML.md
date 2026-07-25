# Proposta: un nuovo algoritmo di decodifica per Shor *informato dalla topologia della QPU*

**Autore:** Claudio Dragotta
**Contesto:** tesi magistrale — Shor su hardware NISQ, correzione d'errore e strategie di recupero del risultato
**Stato:** proposta di contributo originale (da valutare come capitolo sperimentale o come sezione di *Sviluppi Futuri*)

---

## 1. Il problema

Nella tesi sono già state confrontate due strategie per estrarre il risultato corretto dell'algoritmo di Shor da un'esecuzione rumorosa:

- **TOP-K (TOP-4):** si tentano i *K* esiti più frequenti dell'istogramma. Economico ed efficace, ma **cieco all'hardware**: usa solo le frequenze, non sa nulla di come sono fatti i qubit o di come sono collegati.
- **Classificatore ML a posteriori:** impara a distinguere gli istogrammi "buoni" da quelli distrutti dal rumore. L'ablazione ha dimostrato che **non aggiunge nulla** rispetto al TOP-4, e per di più richiede una **fase di addestramento separata** (generare migliaia di istogrammi, allenare il modello) *prima* di poter essere usato.

Entrambe condividono un limite: per arrivare a un risultato affidabile richiedono **esecuzioni separate aggiuntive** — l'ML un intero run di generazione dataset, il classico molte ripetizioni per accumulare statistica. L'obiettivo di questa proposta è un algoritmo che decide in **una sola passata**, senza addestramento e senza calibrazione dedicata, **risparmiando tempo**.

---

## 2. L'intuizione chiave: la QPU pubblica già la propria "natura"

Non serve *eseguire* nulla per caratterizzare la QPU: una QPU reale **espone la propria calibrazione** come metadato. Su IBM, tramite `backend.properties()` / `backend.target`, sono disponibili — senza alcuna esecuzione del circuito:

- la **coupling map**: quali qubit sono fisicamente collegati (il grafo di connettività);
- **T₁ e T₂ per ogni qubit**;
- l'**errore di gate per ogni arco CX** — fondamentale: ε₂q **non è uniforme**, dipende dalla coppia di qubit specifica;
- l'**errore di readout per ogni qubit**.

Questo ribalta l'impostazione: la caratterizzazione del rumore **è un dato che si legge**, non un esperimento da ripetere. Un algoritmo che sfrutta questi metadati può informare la decodifica **in una singola esecuzione**, evitando la doppia esecuzione (calibrazione + calcolo, oppure addestramento + inferenza).

---

## 3. La proposta

**Nome di lavoro:** *Decodifica QPE Informata dalla Topologia* (DIT) — in inglese *Topology-Aware QPE Decoding* (TAQD).

Due leve complementari che, insieme, sostituiscono sia il TOP-4 sia l'ML a posteriori.

### Leva A — Prima dell'esecuzione: placement consapevole del rumore, mirato allo Shor

Il transpiler di Qiskit esegue già un layout "noise-aware" generico. Qui lo si **specializza per la struttura dell'algoritmo di Shor**:

- si assegnano i **qubit di conteggio** (quelli la cui misura porta il periodo `r`) ai **qubit fisici più fedeli** (readout basso, T₂ alto);
- si instrada la **moltiplicazione modulare controllata** privilegiando gli **archi CX a errore minore** della coupling map.

**Obiettivo:** far **sopravvivere il picco QPE già in un singolo shot**, invece di doverlo recuperare a valle.

> **Perché questo NON ricade nel risultato negativo della tesi.** La tesi ha mostrato che *ciò che il rumore ha distrutto non è più recuperabile con post-processing*. La Leva A non è post-processing: agisce **prima** dell'esecuzione e **previene** la perdita di informazione invece di tentare di ricostruirla. È un contributo strutturalmente diverso.

### Leva B — Dopo l'esecuzione: ranking a *confidenza*, non a frequenza

Invece di prendere i *K* esiti più frequenti (TOP-4), ogni bitstring misurata viene pesata con una **confidenza per-bit** derivata **analiticamente** dai metadati della QPU.

Per ogni qubit di conteggio `i` si definisce una **affidabilità**:

```
reliability_i = (1 - readout_error_i) * exp( - Σ_e ε₂q(e) )
```

dove la somma è sugli **archi CX `e`** che quel qubit ha effettivamente attraversato nel circuito traspilato (informazione nota dal circuito + coupling map). Qubit letti male o coinvolti in molti CX ad alto errore → confidenza bassa.

Due modalità d'uso, in ordine di ambizione:

1. **Readout unfolding matrix-free (O(n)):** si correggono le probabilità marginali di ciascun bit usando `reliability_i`, senza costruire la matrice di assegnazione 2ⁿ×2ⁿ (intrattabile). Poi si ri-ordinano i candidati per punteggio corretto invece che per frequenza grezza.

2. **Decoder MAP bayesiano sul periodo:** per ogni candidato periodo `r ∈ {2,…,N−1}` si calcolano i picchi QPE attesi `y_k = round(k·2ⁿ/r)`; si assegna a `r` un punteggio confrontando l'istogramma **pesato per confidenza** con questi picchi, dove la **larghezza attesa** di ciascun picco è derivata dal rumore complessivo degli archi realmente usati (coupling map). Si sceglie `argmax_r` e da lì si estraggono i fattori.

**Pseudocodice (Leva B, modalità 2):**

```
input:  counts (istogramma di 1 esecuzione), backend.properties, circuito traspilato, N, a
1. per ogni qubit di conteggio i: reliability_i  ← f(readout_error_i, Σ ε₂q sugli archi usati)
2. counts_pesati  ← riscala counts usando le reliability per-bit (unfolding marginale)
3. per r in 2..N-1:
       picchi_attesi  ← { round(k·2ⁿ/r) : k = 0..r-1 }
       σ_r            ← larghezza attesa dei picchi dal rumore totale del circuito
       score[r]       ← Σ_y counts_pesati[y] · kernel(y, picco più vicino; σ_r)
4. r*  ← argmax_r score[r]
5. estrai (p, q) da r*  →  verifica p·q = N
output: fattori, in UNA sola esecuzione, senza addestramento
```

---

## 4. Confronto con le strategie esistenti

| Strategia | Usa l'hardware? | Serve addestramento? | Esecuzioni necessarie |
|---|---|---|---|
| Classico TOP-1 | No | No | molte (M̄ ≈ 6 su UC1) |
| TOP-4 | No | No | ~1, ma cieco alla topologia |
| ML a posteriori | No | **Sì (fase separata)** | 1 + generazione dataset |
| **DIT/TAQD (proposta)** | **Sì (coupling map + errori)** | **No** | **1, puramente analitico** |

Il punto di forza: è **hardware-aware come vorrebbe essere l'ML**, ma **training-free come il TOP-4**, e in più agisce anche *prima* dell'esecuzione (Leva A), cosa che nessuna delle due fa.

---

## 5. Piano di validazione

Per dimostrare un vantaggio serve un rumore **eterogeneo per arco** (altrimenti la topologia non porta informazione):

1. **Su simulatore (via più veloce):** in Qiskit Aer assegnare ε₂q **diversi per ogni arco CX** e readout error diversi per qubit, replicando una coupling map realistica (es. quella di un backend IBM). Confrontare, a parità di shot:
   - TOP-4 (baseline),
   - DIT Leva B (ranking a confidenza),
   - DIT Leva A+B (placement + confidenza).
   Metrica: success rate a **1 sola esecuzione** e numero medio di iterazioni M̄.
2. **Con `properties` reali (senza eseguire su hardware):** scaricare `backend.properties()` di un backend IBM reale e usarne i valori nel simulatore — così l'esperimento è ancorato a dati veri senza costi di coda hardware.

**Ipotesi da verificare:** su coupling map eterogenea, DIT ottiene success rate a singolo shot **superiore** al TOP-4, senza alcun addestramento.

---

## 6. Fattibilità, rischi e scope

- **Rischio principale:** su **N=15** il circuito è piccolo e, con rumore quasi uniforme, il vantaggio topologico può non emergere. È **essenziale** usare una coupling map con errori marcatamente eterogenei (punto 1 sopra) perché l'idea abbia modo di mostrarsi.
- **Rischio secondario:** con l'entanglement un singolo qubit non ha un vettore di Bloch pulito; la confidenza per-bit va intesa come peso euristico sulla misura finale (dopo il collasso), non come stato intermedio — la formulazione della Leva B è coerente con questo.
- **Costo di implementazione:**
  - **Leva B** è la più rapida da validare (solo post-processing su istogrammi già prodotti): candidata ideale per un primo risultato.
  - **Leva A** richiede intervenire sul layout/transpilazione: più lavoro, ma è la parte concettualmente più forte (sfugge al risultato negativo della tesi).
- **Collocazione nella tesi:**
  - *Opzione minima (realistica entro ottobre):* sezione ben formalizzata in **Sviluppi Futuri**, con la Leva B validata su un mini-esperimento simulato.
  - *Opzione piena:* capitolo sperimentale dedicato con confronto DIT vs TOP-4 su coupling map eterogenea.

---

## 7. Domanda aperta da chiarire

Con **"eseguire l'algoritmo due volte in maniera separata"** si intende:

1. la **fase di addestramento** separata dell'ML (→ la Leva B la elimina: è analitica, zero training);
2. una **calibrazione** separata prima del calcolo (→ eliminata leggendo `backend.properties`);
3. le **ripetizioni M̄** dell'algoritmo per accumulare statistica (→ ridotte dal placement della Leva A + dal ranking a confidenza della Leva B, che puntano al successo in un singolo shot).

La risposta orienta su quale leva concentrare l'esperimento principale.
