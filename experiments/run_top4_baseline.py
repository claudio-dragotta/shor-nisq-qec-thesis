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

NOISE_REALISTIC = dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
NOISE_DEGRADED  = dict(eps_1q=5e-3, eps_2q=5e-2, t1_ns=50_000,  t2_ns=30_000,  p_ro=0.05)

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


def run_uc(uc_name, N, a, n_count, noise_params):
    nm  = build_noise_model(**noise_params)
    clf = joblib.load(f'clf_{uc_name}.joblib')['clf']

    m1, mt4, m2 = [], [], []
    for rep in range(K):
        print(f'  {uc_name} rep {rep+1}/{K}', end='\r', flush=True)
        m1.append( run_method1(N, a, n_count, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
        mt4.append(run_method_top4(N, a, n_count, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
        m2.append( run_method2(N, a, n_count, nm, clf, shots=SHOTS, max_iter=MAX_ITER, seed=rep)['iterations'])
    print()
    return np.array(m1), np.array(mt4), np.array(m2)


def report(uc_name, m1, mt4, m2):
    print(f'\n{"="*60}')
    print(f'  {uc_name}')
    print(f'{"="*60}')

    for label, arr in [('M1  (TOP-1)    ', m1), ('M_TOP4 (TOP-4) ', mt4), ('M2  (CLF+TOP-4)', m2)]:
        ok = arr[arr < MAX_ITER]
        med = np.median(arr[arr < MAX_ITER]) if len(ok) > 0 else float('nan')
        print(f'  {label}  n_succ={len(ok)}/{K}  M̄={ok.mean() if len(ok) else float("nan"):.2f}'
              f'  σ={ok.std() if len(ok) else float("nan"):.2f}  med={med:.1f}')

    # Mann-Whitney: M1 > M_TOP4
    u1, p1 = mannwhitneyu(m1, mt4, alternative='greater')
    # Mann-Whitney: M_TOP4 > M2
    u2, p2 = mannwhitneyu(mt4, m2, alternative='greater')
    # Mann-Whitney: M1 > M2
    u3, p3 = mannwhitneyu(m1, m2, alternative='greater')

    print(f'\n  Mann-Whitney M1 > M_TOP4 : U={u1:.0f}  p={p1:.4f}',
          '→ sign.' if p1 < 0.05 else '→ n.s.')
    print(f'  Mann-Whitney M_TOP4 > M2 : U={u2:.0f}  p={p2:.4f}',
          '→ sign.' if p2 < 0.05 else '→ n.s.')
    print(f'  Mann-Whitney M1 > M2     : U={u3:.0f}  p={p3:.4f}',
          '→ sign.' if p3 < 0.05 else '→ n.s.')

    # Fattori di riduzione
    m1_ok  = m1[m1 < MAX_ITER]
    mt4_ok = mt4[mt4 < MAX_ITER]
    m2_ok  = m2[m2 < MAX_ITER]
    rho_top4 = m1_ok.mean() / mt4_ok.mean() if len(mt4_ok) else float('nan')
    rho_m2   = m1_ok.mean() / m2_ok.mean()  if len(m2_ok)  else float('nan')

    print(f'\n  rho(M1/M_TOP4) = {rho_top4:.3f}')
    print(f'  rho(M1/M2)     = {rho_m2:.3f}')

    # Valori pronti per LaTeX
    print(f'\n  LaTeX row M_TOP4:')
    mt4_succ = len(mt4_ok)
    mt4_psucc = 100 * mt4_succ / K
    mt4_mean = mt4_ok.mean() if len(mt4_ok) else float('nan')
    mt4_std  = mt4_ok.std()  if len(mt4_ok) else float('nan')
    mt4_med  = np.median(mt4_ok) if len(mt4_ok) else float('nan')
    print(f'  M_TOP4 (TOP-4) & {mt4_psucc:.1f}\\% & {mt4_mean:.2f} & {mt4_std:.2f} & {mt4_med:.0f} & {rho_top4:.3f} \\\\')
    print(f'  U(M1>M_TOP4)={u1:.0f}  p={p1:.4f}')
    print(f'  U(M_TOP4>M2)={u2:.0f}  p={p2:.4f}')


if __name__ == '__main__':
    print('UC1 — NISQ-realistico')
    m1_uc1, mt4_uc1, m2_uc1 = run_uc('UC1', 15, 7, 8, NOISE_REALISTIC)

    print('UC2 — NISQ-degradato')
    m1_uc2, mt4_uc2, m2_uc2 = run_uc('UC2', 15, 7, 8, NOISE_DEGRADED)

    report('UC1 — NISQ-realistico', m1_uc1, mt4_uc1, m2_uc1)
    report('UC2 — NISQ-degradato',  m1_uc2, mt4_uc2, m2_uc2)

    print('\nCopia i valori "LaTeX row" nei capitoli Risultati e Conclusioni.')
