"""Perche' il dataset di UC1 e' passato dal 25.8% di negativi a nessun negativo?

Il dataset originale (maggio 2026) conteneva il 25.8% di campioni negativi. Rigenerato
oggi con lo stesso codice risulta interamente positivo, e il confronto fra schemi di
seeding ha escluso che la causa sia il seme (entrambi gli schemi danno 0% negativi).

L'altra variabile cambiata nel frattempo e' il transpiler: lo stesso circuito produceva
162 porte CX con la versione precedente di Qiskit e ne produce 114 con la 2.x, cioe'
P_surv da 0.196 a 0.318. Se la causa e' questa, riportando il rumore al livello che
rende P_surv equivalente a quello di 162 porte i negativi devono ricomparire.

  (1 - eps')^114 = (1 - eps)^162   =>   eps' ~ eps * 162/114 = 1.42 * eps

Lo script campiona la frazione di negativi in funzione di eps_2q, cosi' da localizzare
la soglia oltre la quale la classe negativa esiste.
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

nm_ref = build_noise_model(eps_2q=1e-2, **BASE)
sim_tp = AerSimulator(noise_model=nm_ref, method='statevector')
qc = transpile(shor_circuit(N, A, N_COUNT), sim_tp, optimization_level=2)
n_cx = qc.count_ops().get('cx', 0)
print(f'circuito: {n_cx} CX, profondita {qc.depth()}', flush=True)
print(f'composizione: {dict(qc.count_ops())}\n', flush=True)

for eps_base in (1e-2, 1.42e-2, 2e-2, 3e-2, 5e-2):
    rng = np.random.default_rng(42)
    sim = AerSimulator(method='statevector')
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
    p_surv = (1 - eps_base) ** n_cx
    print(f'eps_2q base {eps_base:.3g}  (P_surv {p_surv:.3g})  ->  '
          f'{neg:3d}/{N_SAMPLES} negativi ({100 * neg / N_SAMPLES:.1f}%)', flush=True)
