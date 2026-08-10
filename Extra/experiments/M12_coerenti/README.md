# M12 — Il decoder appreso guadagna di più sugli errori coerenti?

Esperimento del 2026-08-07. Mette alla prova una previsione che il criterio della tesi
sembrava implicare e che invece **non regge**.

## La previsione

Il criterio unificante dice che un modello appreso rende quando il metodo analitico è
*strutturalmente cieco* a una classe di informazione. Gli errori coerenti sembravano
soddisfare la condizione più fortemente del crosstalk di Pauli già studiato in M10: il MWPM
non è mal calibrato sulle sovrarotazioni, è costruito su un modello di Pauli e una
sovrarotazione **non è** un errore di Pauli. La cecità appariva totale, non parziale.

Previsione falsificabile: *il guadagno del decoder appreso dev'essere maggiore sotto errori
coerenti che sotto errori di Pauli di pari probabilità marginale.*

## Perché non si può usare Stim

Stim è un simulatore a stabilizzatori: rappresenta solo errori di Pauli. Una sovrarotazione
coerente richiede un simulatore full-state — ed è precisamente questa impossibilità a rendere
l'esperimento interessante. Il sistema è quindi ricostruito a mano su Qiskit Aer: surface code
ruotato d=3, memory Z, 9 qubit dati + 4 ancilla, 4 cicli, 3·10⁵ shot.

Confronto a parità di probabilità marginale:

- **Pauli** — X con probabilità p su ogni qubit dato, a ogni ciclo
- **Coerente** — RX(θ) con sin²(θ/2) = p, stessa probabilità di flip in un ciclo, ma le
  ampiezze si accumulano fra un ciclo e l'altro invece delle probabilità

Il MWPM riceve in **entrambi** i casi i pesi del modello di Pauli: è ciò di cui un operatore
dispone realmente.

## Risultato

| rumore | p | p_L MWPM | p_L ibrido | guadagno |
|---|---|---|---|---|
| Pauli | 0.01 | 0.01520 | 0.01492 | 1.019 |
| coerente | 0.01 | 0.01425 | 0.01385 | 1.029 |
| Pauli | 0.02 | 0.04215 | 0.04068 | 1.036 |
| coerente | 0.02 | 0.04372 | 0.04172 | 1.048 |
| Pauli | 0.03 | 0.07671 | 0.07367 | 1.041 |
| coerente | 0.03 | 0.07892 | 0.07501 | 1.052 |

Flag dello script: **GIALLO — nessuna differenza apprezzabile fra i due tipi di rumore.**
Lo scarto è di circa un punto percentuale, dell'ordine di una deviazione standard su p_L
(σ ≈ 9.6·10⁻⁴ su 7.5·10⁴ campioni di test). Il segno è però lo stesso in tutti e tre i punti,
il che è compatibile con un effetto reale ma di entità pari a circa un decimo di quello
atteso.

## Perché la previsione era sbagliata

Due ragioni, entrambe finite in tesi (§9.5).

1. **L'estrazione ciclica della sindrome fa da twirling parziale.** Misurare gli
   stabilizzatori proietta lo stato a ogni ciclo, convertendo l'accumulo di ampiezza in
   statistica di Pauli prima che possa crescere quadraticamente. Il divario che la figura a
   singolo qubit mostra (fattore ~7 a N=8 operazioni) non si riproduce dentro un codice
   attivo: la penalità complessiva è del ~12%, non di ordini di grandezza.
2. **Una sovrarotazione su un singolo qubit resta decomponibile in archi.** Quando produce un
   flip accende gli stessi stabilizzatori di un errore X, ed è rappresentabile nel grafo del
   matching esattamente come quello.

Ne segue una precisazione del criterio, non un'eccezione: la cecità che l'apprendimento
sfrutta **non è genericamente il "non essere Pauli"**, è la *non decomponibilità* — un
meccanismo che accende più di due detector, come il crosstalk fra qubit dati adiacenti.

La sorgente non-Pauli che avrebbe la firma giusta è il **leakage**: la fuga verso |2⟩ non è
rappresentabile nello spazio degli errori del decoder, persiste per più cicli e corrompe più
stabilizzatori. È la direzione indicata in Sviluppi Futuri; richiede un modello a tre livelli
e confina l'esperimento a distanze molto piccole.

## Uso

```bash
source ~/quantum-env/bin/activate
python decoder_coerente.py [--shots 300000]
```

Risultati in `results_M12_coerenti_*.json`, log in `run_M12.log`.
Il braccio MWPM è riportato in §9.5 della tesi, quello del decoder appreso pure (paragrafo
"Una previsione che il twirling porta con sé").
