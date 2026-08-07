"""Quante sono davvero le porte soggette all'errore a due qubit?

P_surv = (1 - eps_2q)^k richiede che k sia il numero di porte a cui il modello di rumore
applica l'errore depolarizzante a due qubit. `build_noise_model` lo applica a
['cx', 'swap', 'cp'] — non alle sole 'cx'. Contare le sole 'cx' sottostima k ogni volta
che il circuito traspilato conserva porte 'cp', come accade per la QFT inversa.

Questo script riporta, per ciascun use case, il conteggio completo e i due valori di
P_surv: quello (errato) sulle sole 'cx' e quello corretto su tutte le porte rumorose.
"""
import warnings

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model

# Le porte a cui build_noise_model applica depolarizing_error(eps_2q, 2)
PORTE_2Q = ('cx', 'swap', 'cp')

CASI = [
    ('UC1', 15, 7, 8, 1e-2),
    ('UC2', 15, 7, 8, 5e-2),
    ('UC3', 21, 2, 10, 1e-2),
    ('UC4', 35, 6, 12, 1e-2),
]

print(f'{"UC":5} {"qubit":>5} {"prof.":>6} {"cx":>6} {"cp":>5} {"swap":>5} '
      f'{"k_2q":>6} {"P_surv(cx)":>12} {"P_surv(k_2q)":>14}')
for nome, N, a, n_count, eps_2q in CASI:
    nm = build_noise_model(eps_1q=1e-3, eps_2q=eps_2q,
                           t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
    sim = AerSimulator(noise_model=nm, method='statevector')
    t = transpile(shor_circuit(N, a, n_count), sim, optimization_level=2)
    ops = dict(t.count_ops())
    n_cx = ops.get('cx', 0)
    k = sum(ops.get(g, 0) for g in PORTE_2Q)
    print(f'{nome:5} {t.num_qubits:5d} {t.depth():6d} {n_cx:6d} '
          f'{ops.get("cp", 0):5d} {ops.get("swap", 0):5d} {k:6d} '
          f'{(1 - eps_2q) ** n_cx:12.4g} {(1 - eps_2q) ** k:14.4g}')
    print(f'      composizione completa: {ops}')
