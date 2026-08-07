"""Quante volte la moda dell'istogramma di UC1 cade sull'esito banale y=0?

Serve a sostanziare l'affermazione del Cap. 10 sul motivo strutturale per cui
TOP-1 richiede piu' di un tentativo. Usa lo stesso schema di seeding corretto
delle campagne (passo 10_000 > shots, per flussi di shot disgiunti).
"""
import warnings
from collections import Counter

warnings.filterwarnings('ignore')

from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import shor_circuit, build_noise_model, extract_factors

N, A, N_COUNT, SHOTS, N_RUN = 15, 7, 8, 1024, 60

nm = build_noise_model(1e-3, 1e-2, 100_000, 80_000, 50, 0.02)
sim = AerSimulator(noise_model=nm, method='statevector')
qc = transpile(shor_circuit(N, A, N_COUNT), sim, optimization_level=2)

mode_zero = 0
mode_valid = 0
top4_valid = 0
modes = Counter()

for i in range(N_RUN):
    counts = sim.run(qc, shots=SHOTS, seed_simulator=7 * 1_000_000 + i * 10_000
                     ).result().get_counts()
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    top = int(ordered[0][0], 2)
    modes[top] += 1
    if top == 0:
        mode_zero += 1
    if extract_factors(top, N_COUNT, N, A)[0] is not None:
        mode_valid += 1
    if any(extract_factors(int(s, 2), N_COUNT, N, A)[0] is not None
           for s, _ in ordered[:4]):
        top4_valid += 1

print(f'run={N_RUN}')
print(f'moda == y=0            : {mode_zero:3d}  ({100 * mode_zero / N_RUN:.1f}%)')
print(f'moda porta ai fattori  : {mode_valid:3d}  ({100 * mode_valid / N_RUN:.1f}%)')
print(f'TOP-4 porta ai fattori : {top4_valid:3d}  ({100 * top4_valid / N_RUN:.1f}%)')
print('distribuzione delle mode:', dict(modes.most_common(8)))
