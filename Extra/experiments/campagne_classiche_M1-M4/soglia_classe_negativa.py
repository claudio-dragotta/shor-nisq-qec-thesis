"""A quale livello di rumore comincia a esistere la classe negativa?

Con la regola di etichettatura documentata (TOP_K = 16) il dataset di UC1 risulta
interamente positivo, e lo resta fino a eps_2q = 5e-2, cioe' il livello di rumore di
UC2. Questo script estende la ricerca verso l'alto per individuare la soglia oltre la
quale esistono istogrammi da scartare — l'unico regime in cui il filtro ML del Metodo 2
avrebbe qualcosa da apprendere.

Il valore di riferimento NISQ-realistico e' eps_2q = 1e-2.
"""
import warnings

warnings.filterwarnings('ignore')

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model, extract_factors

N, A, N_COUNT, SHOTS, N_SAMPLES = 15, 7, 8, 1024, 200
TOP_K = 16
BASE = {'eps_1q': 1e-3, 't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}
EPS_RIFERIMENTO = 1e-2

sim_tp = AerSimulator(noise_model=build_noise_model(eps_2q=1e-2, **BASE),
                      method='statevector')
qc = transpile(shor_circuit(N, A, N_COUNT), sim_tp, optimization_level=2)
ops = dict(qc.count_ops())
k_2q = sum(ops.get(g, 0) for g in ('cx', 'swap', 'cp'))
print(f'circuito: k_2q = {k_2q} porte a due qubit, profondita {qc.depth()}\n', flush=True)

sim = AerSimulator(method='statevector')
for eps_base in (0.05, 0.08, 0.10, 0.15, 0.20, 0.30):
    rng = np.random.default_rng(42)
    neg = 0
    for i in range(N_SAMPLES):
        f = 1.0 + rng.uniform(-0.5, 0.5)
        eps_2q = np.clip(eps_base * f, 1e-3, 0.3)
        t1 = np.clip(BASE['t1_ns'] * f, 10_000, 500_000)
        t2 = np.clip(BASE['t2_ns'] * f, 5_000, t1)
        nm = build_noise_model(np.clip(BASE['eps_1q'] * f, 1e-4, 0.1), eps_2q,
                               t1, t2, p_ro=BASE['p_ro'])
        counts = sim.run(qc, noise_model=nm, shots=SHOTS,
                         seed_simulator=42 * 1_000_000 + i * 10_000).result().get_counts()
        ordinati = sorted(counts.items(), key=lambda kv: -kv[1])
        if not any(extract_factors(int(ms, 2), N_COUNT, N, A)[0] is not None
                   for ms, _ in ordinati[:TOP_K]):
            neg += 1
    print(f'eps_2q {eps_base:.2f}  ({eps_base / EPS_RIFERIMENTO:4.0f}x il valore NISQ-realistico)  '
          f'P_surv {(1 - eps_base) ** k_2q:8.2g}  ->  '
          f'{neg:3d}/{N_SAMPLES} negativi ({100 * neg / N_SAMPLES:5.1f}%)', flush=True)
