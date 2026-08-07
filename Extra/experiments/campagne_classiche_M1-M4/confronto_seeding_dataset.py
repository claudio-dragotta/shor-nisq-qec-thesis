"""Il bilanciamento delle classi del dataset dipende dallo schema di seeding?

Il dataset originale di UC1 conteneva il 25.8% di campioni negativi (istogrammi
senza segnale QPE recuperabile nei TOP-16). Rigenerato con il seeding corretto,
risulta interamente positivo. Questo script isola la causa: genera due dataset
identici in tutto tranne che nello schema di seme, e ne confronta le etichette.

  vecchio schema:  seed_simulator = seed + i          (passo 1, con 1024 shot)
  nuovo schema:    seed_simulator = seed*1e6 + i*1e4  (passo 10_000 > shots)

Se la frazione di negativi cambia solo fra i due schemi, la causa e' il seeding.
"""
import warnings

warnings.filterwarnings('ignore')

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model, extract_factors

N, A, N_COUNT, SHOTS, N_SAMPLES = 15, 7, 8, 1024, 300
NOISE_BASE = {'eps_1q': 1e-3, 'eps_2q': 1e-2,
              't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
TOP_K = 16


def genera(schema, seed=42):
    """schema: 'vecchio' oppure 'nuovo'. Tutto il resto e' identico."""
    rng = np.random.default_rng(seed)
    nm_ref = build_noise_model(**NOISE_BASE)
    sim_tp = AerSimulator(noise_model=nm_ref, method='statevector')
    qc = transpile(shor_circuit(N, A, N_COUNT), sim_tp, optimization_level=2)
    sim = AerSimulator(method='statevector')

    etichette = []
    for i in range(N_SAMPLES):
        # La sequenza di rumore e' identica nei due schemi: stesso seed, stesso rng.
        fattore = 1.0 + rng.uniform(-0.5, 0.5)
        eps_1q = np.clip(NOISE_BASE['eps_1q'] * fattore, 1e-4, 0.1)
        eps_2q = np.clip(NOISE_BASE['eps_2q'] * fattore, 1e-3, 0.3)
        t1 = np.clip(NOISE_BASE['t1_ns'] * fattore, 10_000, 500_000)
        t2 = np.clip(NOISE_BASE['t2_ns'] * fattore, 5_000, t1)
        nm = build_noise_model(eps_1q, eps_2q, t1, t2, p_ro=NOISE_BASE['p_ro'])

        s = seed + i if schema == 'vecchio' else seed * 1_000_000 + i * 10_000
        counts = sim.run(qc, noise_model=nm, shots=SHOTS,
                         seed_simulator=s).result().get_counts()
        ordinati = sorted(counts.items(), key=lambda kv: -kv[1])
        pos = any(extract_factors(int(ms, 2), N_COUNT, N, A)[0] is not None
                  for ms, _ in ordinati[:TOP_K])
        etichette.append(1 if pos else 0)
    return np.array(etichette)


for schema in ('vecchio', 'nuovo'):
    y = genera(schema)
    neg = int(len(y) - y.sum())
    print(f'seeding {schema:8s}: {len(y)} campioni  '
          f'positivi {int(y.sum()):4d}  negativi {neg:4d}  '
          f'({100 * neg / len(y):.1f}% negativi)', flush=True)
