# M6 — Codice di Steane [[7,1,3]]

**Blocco M6** del documento di indirizzo (§9). È il **codice QEC centrale della tesi**: primo
codice capace di correggere un errore **arbitrario** (X, Z o Y) su un singolo qubit.

## Cos'è e a cosa serve

Lo Steane codifica 1 qubit logico in 7 qubit fisici, ha distanza d=3 (corregge 1 errore) ed è
un codice **CSS** costruito dal codice classico di Hamming [7,4,3]: la stessa matrice di parità
genera gli stabilizzatori di tipo X e di tipo Z, così le due famiglie di errori si trattano
separatamente. Rispetto al repetition (M5) paga più qubit (7 vs 3) ma protegge da X **e** Z
**e** Y insieme — non da un solo tipo.

Stabilizzatori (qubit 0..6):
```
tipo X (rilevano Z):  X{3,4,5,6}   X{1,2,5,6}   X{0,2,4,6}
tipo Z (rilevano X):  Z{3,4,5,6}   Z{1,2,5,6}   Z{0,2,4,6}
```

## File

| File | Cos'è |
|---|---|
| `qec_steane.py` | Script unico: encoding, verifica syndrome table, curva errore logico |
| `results_M6_steane_*_155420.json` | Check encoding (code space) |
| `results_M6_steane_*_155432.json` | Verify syndrome table (X/Z/Y) |
| `results_M6_steane_*_155832.json` | Curva p vs p_L (Monte Carlo) |

## Come si esegue

```bash
source ~/quantum-env/bin/activate
python qec_steane.py --mode check      # 1. l'encoding è nel code space?
python qec_steane.py --mode verify     # 2. la syndrome table è biiettiva? (flag decisivo)
python qec_steane.py --mode curve --shots 200000   # 3. curva p vs p_L
# --mode both = check + verify (non la curva); --seed S (default 42)
```
La figura per la tesi: `../../../figure_src/gen_qec_steane.py`
(legge i JSON di questa cartella → `file_latex/figure/qec_steane_curve.pdf`).

## Cosa aspettarsi (tre controlli in ordine)

### 1. Encoding nel code space (`--mode check`)
Si prepara |0_L⟩ e si misurano i 6 stabilizzatori.
- 🟢 **VERDE** se la sindrome è **000000** su tutti gli shot (lo stato è nel code space).
- 🔴 **ROSSO** se compare una sindrome non nulla → encoding o misura sbagliati: **fermarsi qui**.

### 2. Syndrome table biiettiva — FLAG DECISIVO (`--mode verify`)
Si inietta X, poi Z, poi Y su ciascuno dei 7 qubit (21 casi).
- **Atteso**: le 7 sindromi sono distinte e non nulle, e coincidono con la posizione in binario:

| Qubit | Sindrome | Valore |
|---|---|---|
| q₀ | 001 | 1 |
| q₁ | 010 | 2 |
| q₂ | 011 | 3 |
| q₃ | 100 | 4 |
| q₄ | 101 | 5 |
| q₅ | 110 | 6 |
| q₆ | 111 | 7 |

- Errori **X** → solo sindrome Z; errori **Z** → solo sindrome X (dualità CSS); errori **Y** →
  **entrambe** accese.
- 🟢 **VERDE** se le 7 sindromi sono distinte per X, Z e Y (nessuna collisione).
- 🔴 **ROSSO** se due qubit danno la stessa sindrome → il decoder non può distinguerli.

### 3. Curva errore logico (`--mode curve`)
Monte Carlo Pauli-frame sotto rumore depolarizing p per qubit (200k campioni/punto).
- **Atteso**: p_L ∝ p² (pendenza log-log ≈ 2), firma di un codice di distanza 3.
- 🟢 **VERDE** se la pendenza a p piccolo è ≈ 2 (lo script la calcola e la etichetta) e p_L < p
  sotto la pseudo-soglia (**≈ 0.08**).
- Valori di riferimento: p=0.01 → p_L≈0.0017; p=0.05 → p_L≈0.034 (<p); p=0.10 → p_L≈0.116 (>p).

## Come leggere i JSON

- `check`: `{"check": {"all_zero": true, "counts": {"000000": 2000}}}` → `all_zero: true` = VERDE.
- `verify`: `{"verify": {"X": true, "Z": true, "Y": true}}` → tutte `true` = syndrome table biiettiva.
- `curve`: `{"curve": {"points": [{"p":0.01,"p_L":0.00167,"p_L_se":...,"ratio_p2":16.6}, ...]}}`.
  `ratio_p2` = p_L/p² deve tendere a una costante per p→0 (conferma lo scaling quadratico).

## Assunzione dichiarata (no overclaiming)

L'estrazione di sindrome qui **non è fault-tolerant**: il Monte Carlo inietta errori solo sui
qubit dati e assume lettura di sindrome ideale. Un errore sulle ancilla potrebbe corrompere la
sindrome. La gestione fault-tolerant (cicli ripetuti di misura) è il terreno del surface code (M7).
