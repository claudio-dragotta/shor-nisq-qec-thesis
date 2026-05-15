# AVVIO_WSL.md — Briefing completo per Claude su WSL
## Tesi Magistrale: Algoritmo di Shor + QML | Claudio Dragotta
## Università Campus Bio-Medico di Roma | Relatore: Ing. Floriano Caprio
## Ultimo aggiornamento: 2026-05-15

> **Se sei Claude e hai appena aperto questo file su WSL:** leggi tutto dall'inizio
> alla fine prima di toccare qualsiasi file o eseguire qualsiasi comando.
> Questo file è l'unica fonte di verità per la fase sperimentale.

---

## 1. SITUAZIONE ATTUALE (cosa è già fatto)

La tesi ha **14 capitoli**. I primi 10 sono scritti e approvati dal relatore.
I capitoli 11–14 hanno uno skeleton dettagliato ma sono **privi di dati sperimentali**
perché gli esperimenti non sono ancora stati eseguiti.

### Parte teorica — COMPLETATA e approvata
| Cap | File LaTeX | Contenuto |
|-----|-----------|-----------|
| 1 | `Introduzione.tex` | Qubit, NISQ, Shor, crittografia |
| 2 | `Obiettivi.tex` | Domanda di ricerca e ipotesi |
| 3 | `Fondamenti.tex` | Formalismo matematico QC |
| 4 | `Shor.tex` | Algoritmo di Shor completo |
| 5 | `Rumore.tex` | Noise NISQ, canali quantistici |
| 6 | `StrategieAntiRumore.tex` | QML, QEC, ZNE, DD |

### Parte sperimentale — SCRITTA MA SENZA DATI
| Cap | File LaTeX | Stato |
|-----|-----------|-------|
| 7 | `Metodologia.tex` | ✅ Completo (architettura pipeline) |
| 8 | `SpecificheFunzionali.tex` | ✅ Completo (use case, metriche, parametri) |
| 9 | `Sviluppo.tex` | ✅ Completo (codice Python + implementazione) |
| 10 | `RisultatiMetodo1.tex` | 🔲 Skeleton — aspetta dati |
| 11 | `RisultatiMetodo2.tex` | 🔲 Skeleton — aspetta dati |
| 12 | `ConclusioniMetodo1.tex` | 🔲 Skeleton — aspetta dati |
| 13 | `ConclusioniMetodo2.tex` | 🔲 Skeleton — aspetta dati |
| 14 | `SviluppiFuturi.tex` | ✅ Completo |

**Il tuo compito su WSL**: eseguire gli esperimenti, raccogliere i dati, e
popolare i capitoli 10–13 con i risultati reali.

---

## 2. DI COSA PARLA LA TESI (riassunto rapido)

L'algoritmo di Shor fattorizza interi in tempo polinomiale, ma su hardware
NISQ il rumore degrada l'output: senza mitigazione servono **decine di
iterazioni** per ottenere il risultato corretto.

**Contributo originale**: confronto sperimentale tra due metodi:

- **Metodo 1 (M1)** — baseline classico:
  esegui il circuito M volte → raccogli la distribuzione degli output →
  cerca i picchi → stima il periodo r tramite frazioni continue → calcola
  fattori con GCD. Si ferma al primo risultato corretto.
  Metrica: `M̄₁` = iterazioni medie fino al primo successo.

- **Metodo 2 (M2)** — classificatore ML:
  addestra un classificatore binario (RF/SVM/MLP) su output rumorosi →
  dopo ogni esecuzione il classificatore decide se il risultato è corretto →
  si ferma al primo "sì". Ipotesi: bastano ~3 iterazioni.
  Metrica: `M̄₂` = iterazioni medie fino al primo successo.

**Risultato principale**: `ρ = M̄₁ / M̄₂` — il fattore di riduzione.
Ipotesi da verificare sperimentalmente: `ρ ≫ 1` (idealmente 10–15).

---

## 3. FASE 0 — PILOT RUN (DA FARE PRIMA DI TUTTO IL RESTO)

> **I quattro use case NON sono ancora fissati definitivamente.**
> I parametri in sezione 4 sono un punto di partenza derivato dalla letteratura
> (ibm_marrakesh + tutorial IBM), ma devono essere validati da te prima di
> essere scritti in tesi come definitivi. Questa sezione descrive esattamente
> cosa osservare e quando fermarti.

### Step 1 — Verifica che il circuito giri su N=15

```python
# Esegui senza rumore prima: il risultato deve essere sempre corretto
qc = shor_circuit(N=15, a=7, n_count=8)
sim_ideal = AerSimulator(method='statevector')
counts = sim_ideal.run(transpile(qc, sim_ideal), shots=1024).result().get_counts()
# Atteso: picchi netti a 0, 64, 128, 192 (multipli di 256/4)
# Se non vedi picchi netti → problema nel circuito, non nel rumore
```

**Cosa osservare:** la distribuzione ha picchi chiari a multipli di 2^n_count / r?
Se no, c'è un bug nell'implementazione del circuito — fermati qui e debug prima.

### Step 2 — Aggiungi il rumore NISQ-realistico e trova il regime "interessante"

```python
nm = build_noise_model(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
# Esegui ~200 shot singoli e conta quante volte M1 trova i fattori corretti
```

**Domanda chiave:** qual è il tasso di successo per singola esecuzione?

| Tasso successo singola exec | Interpretazione | Azione |
|---|---|---|
| > 60% | Rumore troppo basso — M1 triviale, M2 non serve | Alza eps_2q a 3e-2 o 5e-2 |
| 10% – 50% | **Regime interessante** — M1 richiede più run, M2 può distinguersi | Tieni questi parametri |
| < 5% | Rumore troppo alto — né M1 né M2 convergono mai | Abbassa eps_2q |

L'obiettivo è trovare parametri in cui M̄₁ sia nell'ordine delle **decine** di iterazioni,
non 2 (troppo facile) né 500 (impossibile). Solo tu puoi trovare questo punto
guardando i dati reali.

### Step 3 — Trova il livello "NISQ-degradato" per UC2

Il degradato deve essere abbastanza peggio del realistico da mostrare una differenza
misurabile in M̄₁, ma non così peggio da rendere il problema irrisolvibile.

```python
# Prova questi livelli in sequenza e osserva M̄₁:
livelli = [
    {'eps_2q': 2e-2},   # 2× realistico
    {'eps_2q': 5e-2},   # 5× realistico (punto di partenza corrente)
    {'eps_2q': 1e-1},   # 10× realistico
]
# Cerca il livello in cui M̄₁(degradato) / M̄₁(realistico) ≈ 3–10×
# Quello è il tuo UC2
```

### Step 4 — Verifica che N=21 e N=35 girino

```python
# Testa che il circuito si costruisca e produca output sensati
for N, a in [(21, 2), (35, 6)]:
    qc = shor_circuit(N=N, a=a, n_count=...)  # n_count da determinare
    # Controlla: il circuito si transpila senza errori?
    # I picchi della distribuzione ideale sono dove atteso?
    # La profondità del circuito è gestibile (< 500 gate dopo transpile)?
```

**Domande da rispondere per N=21 (a=2, r=6 atteso):**
- `2^6 = 64`, `64 mod 21 = 1` ✓ — il periodo è matematicamente r=6
- Con rumore NISQ-realistico il picco a 2^n_count / 6 emerge dalla distribuzione?
- Quanti qubit di lavoro servono davvero? (bit_length(21) = 5, ma potrebbe servirne di più)

**Domande da rispondere per N=35 (a=6, r=2 atteso):**
- `6^2 = 36`, `36 mod 35 = 1` ✓ — il periodo è matematicamente r=2
- Con r=2 il circuito è molto più corto → il rumore è meno impattante?
- Se il risultato è troppo facile anche con rumore alto, valuta N=35 con a diverso

**Se N=21 o N=35 non funzionano** (circuito non si costruisce, output degenere,
profondità esplosiva), cambia N. Candidati alternativi: N=33 (a=2, r=10),
N=21 con a=4 (r=3), N=55 (a=2). Aggiorna poi la tabella in Cap.2.

### Step 5 — Solo ora fissa i 4 use case definitivi

Dopo i pilot run hai i dati per compilare questa tabella con valori validati:

| Parametro | UC 1 | UC 2 | UC 3 | UC 4 |
|---|---|---|---|---|
| N | 15 | 15 | ? | ? |
| a | 7 | 7 | ? | ? |
| n_count | 8 | 8 | ? | ? |
| ε_2q scelto | ? | ? | ? | ? |
| M̄₁ osservato | ? | ? | ? | ? |

**Poi** aggiorna la tabella `tab:use_case_params` in
`file_latex/capitoli/ObiettiviPianoSperimentale.tex` con i valori reali,
sostituendo i valori di partenza attualmente scritti.

---

## 4. I QUATTRO USE CASE (punto di partenza — da validare in Fase 0)

> Questi parametri sono derivati da ibm_marrakesh (letteratura) e usati come
> ipotesi di partenza. Potrebbero cambiare dopo i pilot run della Fase 0.

| UC | N  | a | r atteso | n_count | Noise level     | Scopo |
|----|----|----|----------|---------|-----------------|-------|
| 1  | 15 | 7  | 4        | 8       | NISQ-realistico | Baseline letteratura |
| 2  | 15 | 7  | 4        | 8       | NISQ-degradato  | Isola effetto rumore |
| 3  | 21 | 2  | 6        | 10      | NISQ-realistico | Scalabilità N crescente |
| 4  | 35 | 6  | 2        | 12      | NISQ-realistico | N ancora più grande, r corto |

### Parametri noise model di partenza

```python
# NISQ-realistico (basato su ibm_marrakesh)
NOISE_REALISTIC = {
    'eps_1q': 1e-3,
    'eps_2q': 1e-2,
    't1_ns':  100_000,  # 100 µs
    't2_ns':  80_000,   # 80 µs
    'p_ro':   0.02
}

# NISQ-degradato (punto di partenza: 5× errori — da calibrare in Fase 0 Step 3)
NOISE_DEGRADED = {
    'eps_1q': 5e-3,
    'eps_2q': 5e-2,
    't1_ns':  50_000,   # 50 µs
    't2_ns':  30_000,   # 30 µs
    'p_ro':   0.05
}
```

---

## 4. SETUP AMBIENTE (prima volta)

```bash
# Attiva il virtual environment (già creato)
source ~/quantum-env/bin/activate

# Se non esiste ancora, crealo:
python3 -m venv ~/quantum-env
source ~/quantum-env/bin/activate
pip install qiskit qiskit-aer qiskit-ibm-runtime
pip install qiskit-aer-gpu          # richiede CUDA + RTX 4070
pip install numpy scipy matplotlib scikit-learn joblib

# Verifica
python -c "import qiskit; print('Qiskit', qiskit.__version__)"
python -c "from qiskit_aer import AerSimulator; print('Aer OK')"
python -c "from sklearn.ensemble import RandomForestClassifier; print('sklearn OK')"

# Verifica GPU
python -c "
from qiskit_aer import AerSimulator
sim = AerSimulator(method='statevector', device='GPU')
print('GPU OK:', sim.configuration().gpu_name)
"
```

Clona il repo di riferimento se non è già presente:
```bash
cd ~/  # o dove preferisci
git clone https://github.com/Graychii/Shor-Algorithm-Implementation
```

---

## 5. CODICE COMPLETO — copia e incolla direttamente

Tutto il codice è già scritto nel capitolo `Sviluppo.tex`. Qui è estratto
e pronto per essere usato come script Python standalone.

### 5.1 — `shor_core.py` (circuito + noise model + post-processing)

```python
"""
shor_core.py — Funzioni core per la tesi di Claudio Dragotta.
Estratto da file_latex/capitoli/Sviluppo.tex.
"""
import numpy as np
from math import gcd
from fractions import Fraction
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel, depolarizing_error, thermal_relaxation_error, ReadoutError
)

# --- QFT ---
def qft_circuit(n_qubits):
    qc = QuantumCircuit(n_qubits, name='QFT')
    for j in range(n_qubits):
        qc.h(j)
        for k in range(j + 1, n_qubits):
            qc.cp(np.pi / (2 ** (k - j)), k, j)
    for i in range(n_qubits // 2):
        qc.swap(i, n_qubits - i - 1)
    return qc

def inverse_qft(n_qubits):
    return qft_circuit(n_qubits).inverse()

# --- Modular exponentiation per N=15, a=7 ---
def mod_exp_15_7(power):
    U = QuantumCircuit(4, name=f'U^{power}')
    if power % 4 == 1:
        U.swap(0, 1); U.swap(1, 2); U.swap(2, 3)
        U.x(0); U.x(2)
    elif power % 4 == 2:
        U.swap(1, 3); U.swap(0, 2)
    return U

# --- Shor circuit ---
def shor_circuit(N, a, n_count):
    """Costruisce il circuito di Shor. Per ora supporta N=15, a=7."""
    n_work = N.bit_length()
    qc = QuantumCircuit(n_count + n_work, n_count)
    for q in range(n_count):
        qc.h(q)
    qc.x(n_count)
    for j in range(n_count):
        ctrl_U = mod_exp_15_7(2 ** j).control(1)
        qc.append(ctrl_U, [j] + list(range(n_count, n_count + n_work)))
    qc.barrier()
    qc.append(inverse_qft(n_count), range(n_count))
    qc.measure(range(n_count), range(n_count))
    return qc

# --- Post-processing ---
def extract_factors(measured_value, n_count, N, a):
    if measured_value == 0:
        return None, None
    phase = measured_value / (2 ** n_count)
    frac = Fraction(phase).limit_denominator(N)
    r = frac.denominator
    if r % 2 != 0:
        return None, None
    p = gcd(a ** (r // 2) - 1, N)
    q = gcd(a ** (r // 2) + 1, N)
    if 1 < p < N:
        return p, N // p
    if 1 < q < N:
        return q, N // q
    return None, None

# --- Noise model ---
def build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns, gate_time_ns=50, p_ro=0.02):
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(eps_1q, 1), ['h', 'x', 'rz', 'cp'])
    nm.add_all_qubit_quantum_error(depolarizing_error(eps_2q, 2), ['cx', 'swap'])
    nm.add_all_qubit_quantum_error(
        thermal_relaxation_error(t1_ns, t2_ns, gate_time_ns), ['h', 'x'])
    nm.add_all_qubit_readout_error(
        ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]]))
    return nm

# --- Metodo 1 ---
def run_method1(N, a, n_count, noise_model, shots=1024,
                max_iter=200, threshold=0.3, seed=42):
    sim = AerSimulator(noise_model=noise_model, method='statevector', seed_simulator=seed)
    qc = transpile(shor_circuit(N, a, n_count), sim, optimization_level=3)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(qc, shots=shots).result().get_counts()
        max_count = max(counts.values())
        peaks = {k: v for k, v in counts.items() if v >= threshold * max_count}
        for bitstring in sorted(peaks, key=peaks.get, reverse=True):
            p, q = extract_factors(int(bitstring, 2), n_count, N, a)
            if p is not None:
                return {'factors': (p, q), 'iterations': iteration, 'success': True,
                        'counts': counts}
    return {'factors': (None, None), 'iterations': max_iter, 'success': False,
            'counts': {}}

# --- Metodo 2 — inferenza ---
def run_method2(N, a, n_count, noise_model, classifier,
                shots=1024, max_iter=50, seed=42):
    sim = AerSimulator(noise_model=noise_model, method='statevector', seed_simulator=seed)
    qc = transpile(shor_circuit(N, a, n_count), sim, optimization_level=3)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(qc, shots=shots).result().get_counts()
        meas = int(max(counts, key=counts.get), 2)
        feature = np.zeros(2 ** n_count)
        for k, v in counts.items():
            feature[int(k, 2)] = v / shots
        if classifier.predict([feature])[0] == 1:
            p, q = extract_factors(meas, n_count, N, a)
            if p is not None:
                return {'factors': (p, q), 'iterations': iteration, 'success': True}
    return {'factors': (None, None), 'iterations': max_iter, 'success': False}
```

### 5.2 — `train_classifier.py` (generazione dataset + training M2)

```python
"""
train_classifier.py — Genera il dataset e addestra il classificatore.
Da eseguire UNA VOLTA per use case prima di run_experiments.py.
"""
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score
from shor_core import build_noise_model, shor_circuit, extract_factors
from qiskit import transpile
from qiskit_aer import AerSimulator

def generate_dataset(N, a, n_count, noise_base, noise_factor=0.5,
                     n_samples=5000, shots=1024, seed=0):
    """
    Genera (feature, label) variando i parametri di rumore nell'intorno
    di noise_base entro ±noise_factor (es. 0.5 = ±50%).
    """
    rng = np.random.default_rng(seed)
    X, y = [], []
    for i in range(n_samples):
        factor = 1.0 + rng.uniform(-noise_factor, noise_factor)
        eps_1q = np.clip(noise_base['eps_1q'] * factor, 1e-4, 0.1)
        eps_2q = np.clip(noise_base['eps_2q'] * factor, 1e-3, 0.3)
        t1_ns  = np.clip(noise_base['t1_ns']  * factor, 10_000, 500_000)
        t2_ns  = np.clip(noise_base['t2_ns']  * factor, 5_000,  t1_ns)

        nm  = build_noise_model(eps_1q, eps_2q, t1_ns, t2_ns,
                                p_ro=noise_base['p_ro'])
        sim = AerSimulator(noise_model=nm, method='statevector',
                           seed_simulator=seed + i)
        qc  = transpile(shor_circuit(N, a, n_count), sim, optimization_level=3)

        counts = sim.run(qc, shots=shots).result().get_counts()
        meas   = int(max(counts, key=counts.get), 2)
        p, q   = extract_factors(meas, n_count, N, a)
        label  = 1 if p is not None else 0

        feature = np.zeros(2 ** n_count)
        for k, v in counts.items():
            feature[int(k, 2)] = v / shots
        X.append(feature); y.append(label)

    return np.array(X), np.array(y)


def train_and_save(uc_name, N, a, n_count, noise_base,
                   n_samples=5000, shots=1024, seed=42):
    print(f"\n=== Training per {uc_name} ===")
    X, y = generate_dataset(N, a, n_count, noise_base,
                             n_samples=n_samples, shots=shots, seed=seed)
    print(f"Dataset: {len(X)} campioni | pos={y.sum()} neg={(1-y).sum()}")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y)

    candidates = {
        'RandomForest': RandomForestClassifier(n_estimators=200, random_state=seed),
        'SVM':          SVC(kernel='rbf', probability=True, random_state=seed),
        'MLP':          MLPClassifier(hidden_layer_sizes=(256, 128),
                                      max_iter=500, random_state=seed),
    }
    best_name, best_clf, best_f1 = None, None, -1
    metrics = {}
    for name, clf in candidates.items():
        clf.fit(X_tr, y_tr)
        preds = clf.predict(X_te)
        f1  = f1_score(y_te, preds, zero_division=0)
        acc = accuracy_score(y_te, preds)
        try:
            auc = roc_auc_score(y_te, clf.predict_proba(X_te)[:, 1])
        except Exception:
            auc = float('nan')
        metrics[name] = {'f1': f1, 'acc': acc, 'auc': auc}
        print(f"  {name}: F1={f1:.3f} Acc={acc:.3f} AUC={auc:.3f}")
        if f1 > best_f1:
            best_name, best_clf, best_f1 = name, clf, f1

    print(f">> Selezionato: {best_name} con F1={best_f1:.3f}")
    fname = f"clf_{uc_name}.joblib"
    joblib.dump({'clf': best_clf, 'name': best_name, 'metrics': metrics,
                 'X_test': X_te, 'y_test': y_te}, fname)
    print(f"   Salvato in {fname}")
    return best_clf, metrics


if __name__ == '__main__':
    NOISE_REALISTIC = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
                       't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
    NOISE_DEGRADED  = {'eps_1q': 5e-3, 'eps_2q': 5e-2,
                       't1_ns': 50_000,  't2_ns': 30_000,  'p_ro': 0.05}

    train_and_save('UC1', N=15, a=7, n_count=8,  noise_base=NOISE_REALISTIC)
    train_and_save('UC2', N=15, a=7, n_count=8,  noise_base=NOISE_DEGRADED)
    train_and_save('UC3', N=21, a=2, n_count=10, noise_base=NOISE_REALISTIC)
    train_and_save('UC4', N=35, a=6, n_count=12, noise_base=NOISE_REALISTIC)
```

### 5.3 — `run_experiments.py` (esperimenti M1 + M2 sui 4 use case)

```python
"""
run_experiments.py — Esegue K ripetizioni di M1 e M2 su tutti i use case.
Richiede: shor_core.py + i file clf_UC*.joblib generati da train_classifier.py
"""
import json, joblib, numpy as np
from datetime import datetime
from shor_core import build_noise_model, run_method1, run_method2

NOISE_REALISTIC = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
                   't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
NOISE_DEGRADED  = {'eps_1q': 5e-3, 'eps_2q': 5e-2,
                   't1_ns': 50_000,  't2_ns': 30_000,  'p_ro': 0.05}

USE_CASES = [
    {'name': 'UC1', 'N': 15, 'a': 7, 'n_count': 8,  'noise': NOISE_REALISTIC},
    {'name': 'UC2', 'N': 15, 'a': 7, 'n_count': 8,  'noise': NOISE_DEGRADED},
    {'name': 'UC3', 'N': 21, 'a': 2, 'n_count': 10, 'noise': NOISE_REALISTIC},
    {'name': 'UC4', 'N': 35, 'a': 6, 'n_count': 12, 'noise': NOISE_REALISTIC},
]

K_REPETITIONS = 50   # ripetizioni per stima statistica
SHOTS = 1024

def summarize(results_list, method_key):
    iters = [r['iterations'] for r in results_list if r['success']]
    all_iters = [r['iterations'] for r in results_list]
    return {
        'M_bar': float(np.mean(iters)) if iters else None,
        'std':   float(np.std(iters))  if iters else None,
        'success_rate': len(iters) / len(results_list),
        'all_iterations': all_iters,
    }

def run_all():
    all_results = {}
    for uc in USE_CASES:
        name = uc['name']
        print(f"\n{'='*50}")
        print(f"Use Case: {name}  N={uc['N']} a={uc['a']}")
        print(f"{'='*50}")

        nm = build_noise_model(**uc['noise'])

        # Carica classificatore per M2
        try:
            data = joblib.load(f"clf_{name}.joblib")
            clf  = data['clf']
            print(f"  Classificatore: {data['name']}")
        except FileNotFoundError:
            print(f"  ATTENZIONE: clf_{name}.joblib non trovato."
                  f" Esegui prima train_classifier.py")
            clf = None

        m1_results, m2_results = [], []

        for rep in range(K_REPETITIONS):
            print(f"  Rep {rep+1}/{K_REPETITIONS}", end='\r')

            r1 = run_method1(uc['N'], uc['a'], uc['n_count'], nm,
                             shots=SHOTS, seed=rep)
            m1_results.append(r1)

            if clf is not None:
                r2 = run_method2(uc['N'], uc['a'], uc['n_count'], nm, clf,
                                 shots=SHOTS, seed=rep)
                m2_results.append(r2)

        s1 = summarize(m1_results, 'M1')
        s2 = summarize(m2_results, 'M2') if m2_results else {}
        rho = (s1['M_bar'] / s2['M_bar']
               if s1['M_bar'] and s2.get('M_bar') else None)

        print(f"\n  M̄₁ = {s1['M_bar']:.1f} ± {s1['std']:.1f}"
              f"  (success rate: {s1['success_rate']:.0%})")
        if s2:
            print(f"  M̄₂ = {s2['M_bar']:.1f} ± {s2['std']:.1f}"
                  f"  (success rate: {s2['success_rate']:.0%})")
            print(f"  ρ  = {rho:.2f}" if rho else "  ρ  = N/A")

        all_results[name] = {
            'use_case': uc, 'M1': s1, 'M2': s2, 'rho': rho,
            'raw_M1': m1_results, 'raw_M2': m2_results,
            'timestamp': datetime.now().isoformat()
        }

    # Salvataggio completo
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"results_full_{ts}.json"
    with open(fname, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nRisultati salvati in: {fname}")
    return all_results

if __name__ == '__main__':
    run_all()
```

---

## 6. ORDINE DI ESECUZIONE

```bash
# 1. Attiva ambiente
source ~/quantum-env/bin/activate

# 2. Naviga nella directory di lavoro
cd /percorso/agli/script  # oppure crea una cartella experiments/

# 3. Copia i file .py da qui o creali copiando il codice sopra
#    shor_core.py, train_classifier.py, run_experiments.py

# 4. TEST RAPIDO — verifica che N=15 funzioni prima di procedere
python -c "
from shor_core import shor_circuit, build_noise_model, run_method1
nm = build_noise_model(1e-3, 1e-2, 100_000, 80_000)
r  = run_method1(15, 7, 8, nm, shots=256, max_iter=10, seed=0)
print(r)
"

# 5. Genera dataset e addestra classificatori (lungo: ~1-2h con GPU)
python train_classifier.py

# 6. Esegui tutti gli esperimenti (lungo: ~2-4h con GPU)
python run_experiments.py
```

---

## 7. METRICHE DA RACCOGLIERE

Per ogni use case, i valori che devono finire nei capitoli 10-11:

| Metrica | Descrizione | Dove usarla |
|---------|-------------|-------------|
| `M̄₁` | Media iterazioni M1 per first success | Cap 10 — tabella UC |
| `σ_M1` | Deviazione standard iterazioni M1 | Cap 10 — stessa tabella |
| `M̄₂` | Media iterazioni M2 per first success | Cap 11 — tabella UC |
| `σ_M2` | Deviazione standard iterazioni M2 | Cap 11 — stessa tabella |
| `ρ = M̄₁/M̄₂` | Fattore di riduzione | Cap 11 — risultato principale |
| F1-score | Prestazioni classificatore M2 sul test set | Cap 11 — metriche ML |
| Accuracy | Accuracy classificatore M2 | Cap 11 — metriche ML |
| AUC-ROC | Curva ROC del classificatore | Cap 11 — figura da generare |
| `P_success` | Percentuale ripetizioni che trovano i fattori | Cap 10-11 |
| Matrice di confusione | TP/FP/TN/FN del classificatore | Cap 11 — figura |

### Verifica statistica richiesta dal relatore
- Esegui K=50 ripetizioni per use case (già impostato negli script)
- Mostra la curva di convergenza di `M̄₁` al crescere di K
- Applica il t-test di Welch per validare che `M̄₁ ≠ M̄₂` (p < 0.05)

---

## 8. COME POPOLARE I CAPITOLI SKELETON

I file [RisultatiMetodo1.tex](file_latex/capitoli/RisultatiMetodo1.tex) e
[RisultatiMetodo2.tex](file_latex/capitoli/RisultatiMetodo2.tex) contengono
già la struttura completa con le sezioni e le istruzioni in italiano su cosa
inserire. Aprili e segui le istruzioni sezione per sezione.

**Struttura attesa per ogni use case nei risultati:**
1. Tabella parametri setup (N, a, n_count, eps_1q, eps_2q, T1, T2, p_ro, shots)
2. Istogramma distribuzione output (matplotlib → salva come PDF in `file_latex/figure/`)
3. Picchi identificati e valore r stimato
4. Tabella `M̄₁` (o `M̄₂`) e σ su K=50 ripetizioni
5. Grafico distribuzione iterazioni (boxplot)

**Per le figure**: salva sempre in `file_latex/figure/` come PDF o PNG ad alta risoluzione, poi includile in LaTeX con `\includegraphics`.

---

## 9. STRUMENTI E RISORSE

| Strumento | Dettaglio |
|-----------|-----------|
| Framework | Qiskit + Qiskit Aer |
| Simulatore GPU | `AerSimulator(method='statevector', device='GPU')` |
| Virtual env | `source ~/quantum-env/activate` |
| Repo Shor GitHub | https://github.com/Graychii/Shor-Algorithm-Implementation |
| Tutorial IBM | https://quantum.cloud.ibm.com/docs/en/tutorials/shors-algorithm |
| Hardware riferimento | ibm_marrakesh (parametri realistici) |
| LaTeX | Overleaf (backend: biber + pdflatex) |
| Nuovo strumento (prof) | **[URL DA VERIFICARE — inserire qui quando confermato]** |

> **Nota strumento del professore**: il 2026-05-15 il prof ha comunicato
> che è possibile usare uno strumento aggiuntivo. L'URL non è ancora stato
> verificato — aggiornare questa riga una volta confermato.

---

## 10. DECISIONI ARCHITETTURALI CHIUSE (non riaprire)

Queste decisioni sono state prese col relatore e non vanno rimesse in discussione:

1. **Framework**: Qiskit (chiuso 2026-03-18)
2. **Approccio ML**: classificatore binario (chiuso 2026-03-14)
3. **QEC è sottocategoria di QML** (indicazione del relatore 2026-03-13)
4. **Focus su problemi fisici** del rumore, non matematici (2026-03-26)
5. **4 use case** obbligatori per validazione/pubblicazione (2026-04-10)
6. **Lingua**: italiano accademico formale per tutta la tesi

---

## 11. STILE LATEX (da rispettare nei capitoli da scrivere)

```latex
% Ogni capitolo usa:
\begin{onehalfspace}
...
\end{onehalfspace}

% Acronimi: sempre \ac{SIGLA} (prima occorrenza espande, poi abbrevia)
% Equazioni: numerate con \label{eq:...}, referenziate con \eqref{}
% Figure: sempre [H], caption descrittiva sotto, label con fig:
% Tabelle: sempre [H], caption descrittiva, label con tab:
% Codice Python: ambiente lstlisting con caption
% Termini tecnici inglesi: \textbf{termine} (\textit{english term})
% Ogni capitolo si aggancia esplicitamente alla fine del precedente
```

---

## 12. CHECKLIST FINALE

Prima di consegnare, verificare:

- [ ] UC1: dati M1 e M2 raccolti, skeleton popolato
- [ ] UC2: dati M1 e M2 raccolti, skeleton popolato
- [ ] UC3: dati M1 e M2 raccolti, skeleton popolato
- [ ] UC4: dati M1 e M2 raccolti, skeleton popolato
- [ ] Classificatore M2: F1 > 0.85, AUC > 0.90
- [ ] Fattore ρ calcolato per tutti i use case
- [ ] t-test Welch: p < 0.05 per H₀: M̄₁ = M̄₂
- [ ] Figure salvate in `file_latex/figure/` e incluse nel LaTeX
- [ ] Tabella `tab:use_case_params` aggiornata con valori effettivi
- [ ] `diario_relatore.md` aggiornato con risultati e data sessione
- [ ] Capitoli 10–13 completati con dati reali
- [ ] Tesi compilata su Overleaf senza errori (pdflatex + biber + pdflatex × 2)
- [ ] Lunghezza target: 120–150 pagine solo capitoli

---

*File creato il 2026-05-15. Aggiornare `diario_relatore.md` dopo ogni sessione.*
