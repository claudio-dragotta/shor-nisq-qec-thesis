"""Di quanto P_surv sottostima la sopravvivenza effettiva del segnale QPE?

La tesi osserva che P_surv = (1-eps_2q)^k e' un pessimo predittore di fattibilita':
a eps_2q = 0.1 vale 2.5e-8, eppure la strategia TOP-4 converge ancora al primo
tentativo. Questo script quantifica lo scarto invece di limitarsi a constatarlo.

Modello: sotto rumore depolarizzante l'istogramma osservato si descrive bene come
miscela fra la distribuzione ideale (massa equipartita sui quattro picchi QPE, che
per N=15, a=7 sono k = j*2^8/4) e la distribuzione uniforme sulle 256 celle:

    P_oss(y) = f * P_ideale(y) + (1 - f) / 256

La frazione coerente efficace f si stima dalla massa osservata sui picchi:

    massa_picchi = f + (1 - f) * 4/256   =>   f = (massa_picchi - 4/256) / (1 - 4/256)

Il confronto fra f e P_surv dice quanti ordini di grandezza separano la stima
analitica dalla sopravvivenza effettiva del segnale.
"""
import warnings

warnings.filterwarnings('ignore')

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model

N, A, N_COUNT, SHOTS, N_RUN = 15, 7, 8, 1024, 20
PICCHI = [0, 64, 128, 192]
N_CELLE = 2 ** N_COUNT
BASE = {'eps_1q': 1e-3, 't1_ns': 100_000, 't2_ns': 80_000, 'p_ro': 0.02}

sim_tp = AerSimulator(noise_model=build_noise_model(eps_2q=1e-2, **BASE),
                      method='statevector')
qc = transpile(shor_circuit(N, A, N_COUNT), sim_tp, optimization_level=2)
ops = dict(qc.count_ops())
k_2q = sum(ops.get(g, 0) for g in ('cx', 'swap', 'cp'))
print(f'circuito: k_2q = {k_2q} porte a due qubit\n', flush=True)

print(f'{"eps_2q":>8} {"P_surv":>10} {"massa picchi":>13} {"f efficace":>11} '
      f'{"f / P_surv":>12}')
sim = AerSimulator(method='statevector')
for eps in (1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 3e-1):
    nm = build_noise_model(eps_2q=eps, **BASE)
    masse = []
    for i in range(N_RUN):
        counts = sim.run(qc, noise_model=nm, shots=SHOTS,
                         seed_simulator=11 * 1_000_000 + i * 10_000).result().get_counts()
        tot = sum(counts.values())
        masse.append(sum(counts.get(format(p, f'0{N_COUNT}b'), 0) for p in PICCHI) / tot)
    massa = float(np.mean(masse))
    base_unif = len(PICCHI) / N_CELLE
    f = max((massa - base_unif) / (1 - base_unif), 0.0)
    p_surv = (1 - eps) ** k_2q
    rapporto = f / p_surv if p_surv > 0 else float('inf')
    print(f'{eps:8.3g} {p_surv:10.2e} {massa:13.4f} {f:11.4f} {rapporto:12.3g}',
          flush=True)
