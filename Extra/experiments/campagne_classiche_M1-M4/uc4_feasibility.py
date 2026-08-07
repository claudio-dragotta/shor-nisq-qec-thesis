"""Verifica di fattibilita' di UC4 (N=35, a=6, n_count=12) sul simulatore statevector.

UC3 (N=21) e UC4 (N=35) erano stati dichiarati fuori portata nella prima campagna
sulla base della decomposizione UnitaryGate densa. Per N=35 con a=6 il periodo e'
r=2 (6^2 = 36 = 1 mod 35): la moltiplicazione modulare si riduce a una permutazione
di costo molto inferiore, quindi la barriera va rimisurata invece che assunta.
"""
import time
import warnings

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model, extract_factors

N, A, N_COUNT, SHOTS = 35, 6, 12, 128

nm = build_noise_model(1e-3, 1e-2, 100_000, 80_000, 50, 0.02)
qc = shor_circuit(N, A, N_COUNT)
sim = AerSimulator(noise_model=nm, method='statevector')
t = transpile(qc, sim, optimization_level=2)
ops = dict(t.count_ops())
# vedi nota in uc3_feasibility.py: k_2q = cx + swap + cp, non le sole cx
k_2q = sum(ops.get(g, 0) for g in ('cx', 'swap', 'cp'))
print(f'qubit {t.num_qubits}  cx {ops.get("cx", 0)}  cp {ops.get("cp", 0)}  '
      f'k_2q {k_2q}  depth {t.depth()}  P_surv {(1 - 1e-2) ** k_2q:.3g}', flush=True)

t0 = time.time()
counts = sim.run(t, shots=SHOTS, seed_simulator=1).result().get_counts()
dt = time.time() - t0

ok = sum(n for s, n in counts.items() if extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None)
print(f'statevector {SHOTS} shot in {dt:.1f}s | frazione shot corretti {ok / SHOTS:.4f}', flush=True)

top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
print('TOP-8 (valore k, conteggio, fattori estratti):', flush=True)
for s, n in top:
    k = int(s, 2)
    f = extract_factors(k, N_COUNT, N, A)
    print(f'  k={k:5d}  n={n:4d}  -> {f}', flush=True)
