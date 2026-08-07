"""Verifica di fattibilita' di UC3 (N=21, a=2, n_count=10) sul simulatore statevector.

UC3 e' il vero banco di prova della scalabilita': con a=2 e N=21 il periodo e' r=6,
quindi nessuno dei dieci controlled-U collassa nell'identita' (a differenza di UC4,
dove r=2 azzera tutti i j>=1). Il circuito usa la decomposizione di Beauregard.

La stima analitica P_surv = (1-eps_2q)^{#CX} da' ~1e-15, ma la campagna parametrica
su UC1 ha mostrato che P_surv sottostima gravemente la recuperabilita' del picco QPE:
la misura diretta e' quindi necessaria.
"""
import time
import warnings

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model, extract_factors

N, A, N_COUNT, SHOTS = 21, 2, 10, 1024

nm = build_noise_model(1e-3, 1e-2, 100_000, 80_000, 50, 0.02)
qc = shor_circuit(N, A, N_COUNT)
sim = AerSimulator(noise_model=nm, method='statevector')
t = transpile(qc, sim, optimization_level=2)
ops = dict(t.count_ops())
# P_surv va calcolata su TUTTE le porte a cui build_noise_model applica l'errore
# a due qubit — ['cx', 'swap', 'cp'] — non sulle sole 'cx'.
k_2q = sum(ops.get(g, 0) for g in ('cx', 'swap', 'cp'))
print(f'qubit {t.num_qubits}  cx {ops.get("cx", 0)}  cp {ops.get("cp", 0)}  '
      f'k_2q {k_2q}  depth {t.depth()}  P_surv {(1 - 1e-2) ** k_2q:.3g}', flush=True)

t0 = time.time()
counts = sim.run(t, shots=SHOTS, seed_simulator=1).result().get_counts()
dt = time.time() - t0

ok = sum(n for s, n in counts.items() if extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None)
print(f'statevector {SHOTS} shot in {dt:.1f}s | frazione shot corretti {ok / SHOTS:.4f}', flush=True)

ordered = sorted(counts.items(), key=lambda kv: -kv[1])
print(f'moda -> {extract_factors(int(ordered[0][0], 2), N_COUNT, N, A)}', flush=True)
top4_ok = any(extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None for s, _ in ordered[:4])
print(f'TOP-4 trova i fattori: {top4_ok}', flush=True)
print('TOP-8 (k, conteggio, fattori):', flush=True)
for s, n in ordered[:8]:
    k = int(s, 2)
    print(f'  k={k:5d}  n={n:4d}  -> {extract_factors(k, N_COUNT, N, A)}', flush=True)
