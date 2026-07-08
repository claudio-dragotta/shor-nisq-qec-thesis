"""
run_top4_baseline.py — Testa la variante TOP-4 senza classificatore (M_TOP4).

Scopo: isolare il contributo del classificatore ML da quello della ricerca
multi-candidato. Confronta tre varianti sullo stesso circuito, stessi seed:
  M1      = TOP-1, nessun filtro
  M_TOP4  = TOP-4, nessun filtro  ← NEW
  M2      = CLF + TOP-4

Se M_TOP4 ≈ M2 → il miglioramento è tutto della ricerca TOP-4, il classificatore
               non aggiunge valore.
Se M_TOP4 > M2 → il classificatore contribuisce filtrando iterazioni inutili.

Eseguire da WSL:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python run_top4_baseline.py
"""

import joblib
import numpy as np
from scipy.stats import mannwhitneyu
from shor_core import build_noise_model, shor_circuit, extract_factors, run_method1, run_method2
from qiskit import transpile
from qiskit_aer import AerSimulator

NOISE_REALISTIC     = dict(eps_1q=1e-3,  eps_2q=1e-2,  t1_ns=100_000, t2_ns=80_000,  p_ro=0.02)
NOISE_DEGRADED      = dict(eps_1q=5e-3,  eps_2q=5e-2,  t1_ns=50_000,  t2_ns=30_000,  p_ro=0.05)
NOISE_NEARFUTURE_HARD = dict(eps_1q=1e-4, eps_2q=1e-3,  t1_ns=500_000, t2_ns=400_000, p_ro=0.005)
NOISE_NEARFUTURE_EASY = dict(eps_1q=5e-5, eps_2q=5e-4,  t1_ns=800_000, t2_ns=600_000, p_ro=0.002)

K        = 30
SHOTS    = 1024
MAX_ITER = 50


def run_method_top4(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42):
    """TOP-4 senza classificatore: tenta i 4 candidati più frequenti ogni iterazione."""
    base_qc = shor_circuit(N, a, n_count)
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = transpile(base_qc, sim, optimization_level=2)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=seed * 10000 + iteration).result().get_counts()
        sorted_meas = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        for meas_str, _ in sorted_meas[:4]:
            p, q = extract_factors(int(meas_str, 2), n_count, N, a)
            if p is not None:
                return {'iterations': iteration, 'success': True, 'factors': (p, q)}
    return {'iterations': max_iter, 'success': False, 'factors': (None, None)}


def run_uc(uc_name, N, a, n_count, noise_params, with_m2=True):
    nm  = build_noise_model(**noise_params)

    clf = None
    if with_m2:
        try:
            clf = joblib.load(f'clf_{uc_name}.joblib')['clf']
        except FileNotFoundError:
            print(f'  Nessun classificatore per {uc_name} — solo M1 e M_TOP4')
            with_m2 = False

    m1, mt4, m2 = [], [], []
    for rep in range(K):
        print(f'  {uc_name} rep {rep+1}/{K}', end='\r', flush=True)
        m1.append( run_method1(N, a, n_count, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
        mt4.append(run_method_top4(N, a, n_count, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
        if with_m2:
            m2.append(run_method2(N, a, n_count, nm, clf, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
    print()
    return np.array(m1), np.array(mt4), (np.array(m2) if m2 else None)


def report(uc_name, m1, mt4, m2=None):
    print(f'\n{"="*60}')
    print(f'  {uc_name}')
    print(f'{"="*60}')

    variants = [('M1  (TOP-1)    ', m1), ('M_TOP4 (TOP-4) ', mt4)]
    if m2 is not None:
        variants.append(('M2  (CLF+TOP-4)', m2))

    for label, arr in variants:
        ok = arr[arr < MAX_ITER]
        med = np.median(ok) if len(ok) > 0 else float('nan')
        print(f'  {label}  n_succ={len(ok)}/{K}  M̄={ok.mean() if len(ok) else float("nan"):.2f}'
              f'  σ={ok.std() if len(ok) else float("nan"):.2f}  med={med:.1f}')

    # Mann-Whitney: M1 > M_TOP4
    u1, p1 = mannwhitneyu(m1, mt4, alternative='greater')
    print(f'\n  Mann-Whitney M1 > M_TOP4 : U={u1:.0f}  p={p1:.4f}',
          '→ sign.' if p1 < 0.05 else '→ n.s.')

    if m2 is not None:
        u2, p2 = mannwhitneyu(mt4, m2, alternative='greater')
        u3, p3 = mannwhitneyu(m1,  m2, alternative='greater')
        print(f'  Mann-Whitney M_TOP4 > M2 : U={u2:.0f}  p={p2:.4f}',
              '→ sign.' if p2 < 0.05 else '→ n.s.')
        print(f'  Mann-Whitney M1 > M2     : U={u3:.0f}  p={p3:.4f}',
              '→ sign.' if p3 < 0.05 else '→ n.s.')

    # Fattori di riduzione
    m1_ok  = m1[m1   < MAX_ITER]
    mt4_ok = mt4[mt4 < MAX_ITER]
    rho_top4 = m1_ok.mean() / mt4_ok.mean() if len(mt4_ok) and len(m1_ok) else float('nan')

    print(f'\n  rho(M1/M_TOP4) = {rho_top4:.3f}')
    if m2 is not None:
        m2_ok = m2[m2 < MAX_ITER]
        rho_m2 = m1_ok.mean() / m2_ok.mean() if len(m2_ok) and len(m1_ok) else float('nan')
        print(f'  rho(M1/M2)     = {rho_m2:.3f}')

    # Valori pronti per LaTeX
    mt4_psucc = 100 * len(mt4_ok) / K
    mt4_mean  = mt4_ok.mean() if len(mt4_ok) else float('nan')
    mt4_std   = mt4_ok.std()  if len(mt4_ok) else float('nan')
    mt4_med   = np.median(mt4_ok) if len(mt4_ok) else float('nan')
    print(f'\n  LaTeX row M_TOP4:')
    print(f'  M_TOP4 & {mt4_psucc:.1f}\\% & {mt4_mean:.2f} & {mt4_std:.2f} & {mt4_med:.0f} & {rho_top4:.3f} \\\\')
    print(f'  U(M1>M_TOP4)={u1:.0f}  p={p1:.4f}')


if __name__ == '__main__':
    print('UC1 — N=15 NISQ-realistico')
    m1_uc1, mt4_uc1, m2_uc1 = run_uc('UC1', 15, 7, 8, NOISE_REALISTIC, with_m2=True)

    print('UC2 — N=15 NISQ-degradato')
    m1_uc2, mt4_uc2, m2_uc2 = run_uc('UC2', 15, 7, 8, NOISE_DEGRADED, with_m2=True)

    print('UC3 — N=21 Beauregard, near-future NISQ (eps_2q=0.001)')
    m1_uc3, mt4_uc3, _ = run_uc('UC3', 21, 2, 8, NOISE_NEARFUTURE_HARD, with_m2=False)

    print('UC4 — N=21 Beauregard, near-future NISQ ottimistico (eps_2q=0.0005)')
    m1_uc4, mt4_uc4, _ = run_uc('UC4', 21, 2, 8, NOISE_NEARFUTURE_EASY, with_m2=False)

    report('UC1 — N=15 NISQ-realistico',   m1_uc1, mt4_uc1, m2_uc1)
    report('UC2 — N=15 NISQ-degradato',    m1_uc2, mt4_uc2, m2_uc2)
    report('UC3 — N=21 eps_2q=0.001',      m1_uc3, mt4_uc3, None)
    report('UC4 — N=21 eps_2q=0.0005',     m1_uc4, mt4_uc4, None)

    print('\nCopia i valori "LaTeX row" nei capitoli Risultati e Conclusioni.')
