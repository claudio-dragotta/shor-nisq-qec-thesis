"""Costo di simulazione per shot di UC3 e UC4, per quantificare la barriera computazionale.

In presenza di un modello di rumore AerSimulator non puo' evolvere lo stato una volta
sola e ricampionarlo: ogni shot e' una traiettoria indipendente. Il costo di una
iterazione da 1024 shot e' quindi 1024x il costo di un singolo shot. Questo script
misura il costo per shot ed estrapola il costo dell'intero protocollo (30 ripetizioni
x fino a 50 iterazioni x 1024 shot).
"""
import time
import warnings

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model

CASI = [
    ('UC1', 15, 7, 8, dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)),
    ('UC3', 21, 2, 10, dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)),
    ('UC4', 35, 6, 12, dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)),
]
N_SHOT_PROVA = 4

for nome, N, a, n_count, noise in CASI:
    nm = build_noise_model(**noise)
    sim = AerSimulator(noise_model=nm, method='statevector')
    t = transpile(shor_circuit(N, a, n_count), sim, optimization_level=2)
    n_cx = t.count_ops().get('cx', 0)
    p_surv = (1 - noise['eps_2q']) ** n_cx

    t0 = time.time()
    sim.run(t, shots=N_SHOT_PROVA, seed_simulator=1).result()
    per_shot = (time.time() - t0) / N_SHOT_PROVA

    iter_h = per_shot * 1024 / 3600            # una iterazione da 1024 shot
    protocollo_h = iter_h * 50 * 30            # 30 ripetizioni x fino a 50 iterazioni
    print(f'{nome}: {t.num_qubits:2d} qubit  CX {n_cx:5d}  depth {t.depth():5d}  '
          f'P_surv {p_surv:.3g}  |  {per_shot:7.3f} s/shot  '
          f'-> {iter_h:8.2f} h/iterazione  -> {protocollo_h:10.1f} h protocollo', flush=True)
