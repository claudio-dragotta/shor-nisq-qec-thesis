# M5 — Codice a ripetizione a 3 qubit

**Blocco M5** del documento di indirizzo (§7, prima esercitazione di correzione d'errore).
Introduce il concetto di **sindrome** nel caso più semplice e leggibile.

## Cos'è e a cosa serve

Il codice a ripetizione codifica 1 qubit logico in 3 qubit fisici. Due varianti duali:
- **bit-flip** (`--basis Z`): protegge |0⟩,|1⟩ dagli errori X; stabilizzatori Z₀Z₁, Z₁Z₂.
- **phase-flip** (`--basis X`): protegge |+⟩,|−⟩ dagli errori Z; stabilizzatori X₀X₁, X₁X₂.

Serve a mostrare, nel modo più trasparente, che **misurare la sindrome con qubit ancilla rivela
l'errore senza distruggere l'informazione logica**, e che la codifica rende il qubit logico più
affidabile del fisico sotto una soglia. È il gradino didattico che precede lo Steane (M6).

## File

| File | Cos'è |
|---|---|
| `qec_repetition.py` | Script unico: costruisce il codice, verifica la sindrome, traccia la curva errore |
| `results_M5_repetition_Z_*.json` | Risultati bit-flip (verifica + curva) |
| `results_M5_repetition_X_*.json` | Risultati phase-flip (verifica + curva) |

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python qec_repetition.py --mode both --basis Z    # bit-flip: verifica + curva
python qec_repetition.py --mode both --basis X    # phase-flip
# opzioni: --mode {verify,curve,both}  --shots N (default 20000)  --seed S (default 42)
```
La figura per la tesi si rigenera con `../../../figure_src/gen_qec_repetition.py`
(legge i JSON di questa cartella → `file_latex/figure/qec_repetition_curve.pdf`).

## Cosa aspettarsi (i due esperimenti)

### 1. Verifica della sindrome (`--mode verify`)
Si inietta un errore su ciascun qubit e si legge la sindrome (2 bit).

| Errore su | Sindrome (a₀,a₁) attesa | Qubit dedotto |
|---|---|---|
| nessuno | (0,0) | — |
| q₀ | (1,0) | q₀ |
| q₁ | (1,1) | q₁ |
| q₂ | (0,1) | q₂ |

🟢 **VERDE** se tutte e 4 le sindromi coincidono con l'attesa (per entrambe le basi).
🔴 **ROSSO** se una sindrome non identifica il qubit giusto → errore nella syndrome extraction.

### 2. Curva errore fisico → errore logico (`--mode curve`)
Si applica a ogni qubit un errore con probabilità p e si misura l'errore logico p_L dopo correzione.

- **Atteso**: p_L segue la previsione analitica del voto di maggioranza **p_L = 3p² − 2p³**
  (il codice fallisce quando ≥2 qubit su 3 sbagliano).
- 🟢 **VERDE** se i punti Monte Carlo coincidono con 3p²−2p³ entro l'errore statistico (±σ),
  e p_L < p per p < 0.5 (il qubit logico batte il fisico).
- **Break-even a p = 0.5**: sopra, la ridondanza amplifica l'errore invece di sopprimerlo.

## Come leggere i JSON

```
{
  "verify": {"rows": [{"inject": 0, "syndrome": [1,0], "deduced": 0, "ok": true}, ...],
             "all_ok": true},
  "curve":  {"shots": 20000,
             "points": [{"p": 0.1, "p_L": 0.0288, "p_L_se": 0.0012, "p_L_theory": 0.0280}, ...]}
}
```
- `all_ok: true` → flag verifica VERDE.
- Per ogni punto curva confrontare `p_L` con `p_L_theory`: la differenza deve stare entro
  ~2·`p_L_se`. Se sì, la curva è validata.

## Limite strutturale (da ricordare)

Il repetition code protegge da **un solo tipo** di errore per volta: un errore Z sul codice
bit-flip è invisibile (nessuna sindrome). È la ragione per cui il passo successivo è lo Steane
(M6), che corregge un errore **arbitrario** (X, Z o Y).
