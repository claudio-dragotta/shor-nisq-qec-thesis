"""Pilot test: 5 ripetizioni M1 su UC3 e UC4 con MPS simulator."""
import sys, time
sys.path.insert(0, '.')
from shor_core import build_noise_model, run_method1

nm_uc3 = build_noise_model(eps_1q=1e-4,  eps_2q=1e-3,  t1_ns=500_000, t2_ns=400_000, p_ro=0.005)
nm_uc4 = build_noise_model(eps_1q=5e-5,  eps_2q=5e-4,  t1_ns=800_000, t2_ns=600_000, p_ro=0.002)

print('=== UC3 (N=21, eps_2q=0.001) — 5 prove M1 ===', flush=True)
t0 = time.time()
for rep in range(5):
    r = run_method1(21, 2, 8, nm_uc3, shots=256, max_iter=50, seed=rep)
    status = f'SUCCESSO (fattori={r["factors"]}, iter={r["iterations"]})' if r['success'] else f'FALLITO (iter={r["iterations"]})'
    print(f'  rep={rep}: {status}  [{time.time()-t0:.1f}s]', flush=True)

print(flush=True)
print('=== UC4 (N=21, eps_2q=0.0005) — 5 prove M1 ===', flush=True)
for rep in range(5):
    r = run_method1(21, 2, 8, nm_uc4, shots=256, max_iter=50, seed=rep)
    status = f'SUCCESSO (fattori={r["factors"]}, iter={r["iterations"]})' if r['success'] else f'FALLITO (iter={r["iterations"]})'
    print(f'  rep={rep}: {status}  [{time.time()-t0:.1f}s]', flush=True)

print('\nDone.', flush=True)
