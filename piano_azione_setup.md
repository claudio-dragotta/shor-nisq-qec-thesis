# Piano d'Azione — Setup Ambiente & Sperimentazione
> Aggiornato: 2026-04-10 | Riunione con Ing. Floriano Caprio

---

## Fase 1 — Abilitare WSL2 con supporto GPU (RTX 4070)

### 1.1 Installare WSL2
Aprire PowerShell come amministratore:
```powershell
wsl --install
wsl --set-default-version 2
```
Riavviare il PC, poi aprire Ubuntu dal menu Start per completare la configurazione (creare utente e password).

### 1.2 Installare i driver NVIDIA per WSL
- Andare su `developer.nvidia.com/cuda-downloads`
- Selezionare: **Linux → x86_64 → WSL-Ubuntu → 2.0 → runfile**
- Seguire le istruzioni di installazione mostrate sul sito

### 1.3 Verificare che la GPU sia visibile da WSL
```bash
nvidia-smi
```
Deve apparire la RTX 4070 con la versione driver e la versione CUDA.

---

## Fase 2 — Setup Python e Qiskit in WSL

### 2.1 Aggiornare il sistema e installare Python
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl
```

### 2.2 Creare un virtual environment dedicato
```bash
python3 -m venv ~/quantum-env
source ~/quantum-env/bin/activate
```
> Aggiungere questa riga al `~/.bashrc` per attivarlo automaticamente:
> `source ~/quantum-env/bin/activate`

### 2.3 Installare Qiskit e le librerie necessarie
```bash
# Qiskit core + simulatore + IBM Runtime
pip install qiskit qiskit-aer qiskit-ibm-runtime

# Strumenti scientifici e visualizzazione
pip install matplotlib numpy scipy jupyter

# ML per il Metodo 2 (classificatore)
pip install scikit-learn

# Qiskit Aer con supporto GPU (CUDA) — per accelerare le simulazioni
pip install qiskit-aer-gpu
```

### 2.4 Verificare l'installazione
```bash
python -c "import qiskit; print('Qiskit:', qiskit.__version__)"
python -c "from qiskit_aer import AerSimulator; print('Aer: OK')"
python -c "from qiskit_aer import AerSimulator; s = AerSimulator(method='statevector', device='GPU'); print('GPU sim: OK')"
```

---

## Fase 3 — Scaricare il Repo di Shor

```bash
cd ~
git clone https://github.com/Graychii/Shor-Algorithm-Implementation
cd Shor-Algorithm-Implementation
```

Studiare il codice: capire come è strutturato il circuito, quali parametri accetta, come viene eseguito.

> Il file `shors-algorithm.ipynb` già presente in `tesi_magistrale_quantum/` potrebbe venire dallo stesso repo — confrontarli.

---

## Fase 4 — Aprire il Progetto da VS Code su Windows

Installare l'estensione **Remote - WSL** su VS Code, poi da dentro WSL:
```bash
cd ~/Shor-Algorithm-Implementation
code .
```
VS Code si aprirà su Windows con accesso diretto ai file WSL.

Oppure navigare manualmente in Windows: `\\wsl$\Ubuntu\home\<tuonome>\`

---

## Fase 5 — Primi Esperimenti (in ordine)

### Step 1 — Shor "pulito" (senza rumore)
Eseguire l'algoritmo di Shor dal repo su **N=15** senza noise model.
Verificare che trova i fattori 3 e 5 correttamente.

### Step 2 — Aggiungere il noise model base
```python
from qiskit_aer.noise import NoiseModel, depolarizing_error

noise_model = NoiseModel()
error_1q = depolarizing_error(0.001, 1)   # errore su gate a 1 qubit
error_2q = depolarizing_error(0.01, 2)    # errore su gate a 2 qubit
noise_model.add_all_qubit_quantum_error(error_1q, ['h', 'x', 'rz'])
noise_model.add_all_qubit_quantum_error(error_2q, ['cx'])
```
Eseguire Shor su N=15 con questo noise model, **1024 shots**.
Osservare come cambia la distribuzione degli output.

### Step 3 — Costruire la baseline del Metodo 1
Raccogliere gli output su molte iterazioni → costruire l'istogramma → identificare il picco (gaussiana).
Misurare quante iterazioni servono per trovare il risultato corretto con alta probabilità.

### Step 4 — Variare l'intensità del rumore
Provare diversi valori del parametro di depolarizing error (es. 0.001, 0.005, 0.01, 0.05).
Osservare a che soglia il risultato diventa inaffidabile.

### Step 5 — Scegliere i 4 Use Case
Selezionare 4 combinazioni (N, livello di rumore) che saranno usate per la validazione finale.
> Servono 4 use case per i requisiti di validazione accademica (eventuale pubblicazione).

---

## Stato Capitoli della Tesi

| Capitolo | Stato | Dipende da |
|---|---|---|
| Introduzione | Completato | — |
| Fondamenti | Completato | — |
| Grover | Completato | — |
| Shor | Completato | — |
| Rumore | Completato | — |
| Strategie Anti-Rumore (Cap 6) | Completato | — |
| **Metodologia e Architettura** | Scheletro — scrivibile ora | — |
| **Specifiche Funzionali** | Scheletro — scrivibile ora | — |
| **Sviluppo / Implementazione** | Scheletro — dopo il codice | Codice scritto |
| **Risultati Metodo 1** | Scheletro — aspetta test | 4 use case eseguiti |
| **Risultati Metodo 2** | Scheletro — aspetta test | Test + ML trainato |
| **Conclusioni Metodo 1** | Scheletro — aspetta test | Risultati Metodo 1 |
| **Conclusioni Metodo 2** | Scheletro — aspetta test | Risultati Metodo 2 |
| **Sviluppi Futuri** | Scheletro — abbozzabile ora | Meglio dopo test |

---

## Checklist

- [ ] WSL2 installato e funzionante
- [ ] Driver NVIDIA installati, `nvidia-smi` funziona da WSL
- [ ] Python + virtual environment creato
- [ ] Qiskit installato e verificato
- [ ] `qiskit-aer-gpu` funzionante con RTX 4070
- [ ] Repo Shor clonato e studiato
- [ ] VS Code configurato con Remote - WSL
- [ ] Shor "pulito" su N=15 funzionante
- [ ] Noise model base configurato
- [ ] Prima distribuzione output raccolta (1024 shots)
- [ ] 4 use case scelti
