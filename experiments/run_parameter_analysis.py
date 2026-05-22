"""
run_parameter_analysis.py — Analisi sperimentale sistematica dei parametri di mitigazione.

Esegue 6 sweep per la strategia M_TOP4 (TOP-K senza classificatore):
  1. Variazione di K              : K = 1, 2, 3, 4, 6, 8
  2. Variazione di eps_2q         : 0.001, 0.005, 0.01, 0.02, 0.05, 0.10
  3. Variazione di shots          : 128, 256, 512, 1024, 2048
  4. Analisi congiunta K x eps_2q : griglia 4x4
  5. Variazione di T1/T2          : 20, 50, 100, 200, 500 us
  6. Variazione di p_ro           : 0%, 1%, 2%, 5%, 10%, 20%

Produce:
  - results_parameter_analysis_<timestamp>.json  (dati completi)
  - Stampa righe LaTeX pronte da copiare nelle tabelle della tesi

Eseguire da WSL:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python run_parameter_analysis.py

Per eseguire solo uno sweep specifico:
  python run_parameter_analysis.py --sweep k
  python run_parameter_analysis.py --sweep eps
  python run_parameter_analysis.py --sweep shots
  python run_parameter_analysis.py --sweep joint
  python run_parameter_analysis.py --sweep t1t2
  python run_parameter_analysis.py --sweep eps1q
  python run_parameter_analysis.py --sweep pro
"""

import json
import sys
import argparse
import numpy as np
from datetime import datetime
from math import gcd
from scipy.stats import mannwhitneyu
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import build_noise_model, shor_circuit, extract_factors, run_method1

# ─────────────────────────────────────────────
# Configurazione di riferimento (UC1)
# ─────────────────────────────────────────────
BASE_NOISE = {
    'eps_1q':    1e-3,
    'eps_2q':    1e-2,
    't1_ns':     100_000,
    't2_ns':     80_000,
    'p_ro':      0.02,
}

N        = 15
A        = 7
N_COUNT  = 8
K_REPS   = 30
MAX_ITER = 50

# Risultati noti di M1 su UC1 (baseline, K=30)
M1_UC1_ITERS = [1]*23 + [50]*7   # approssimazione: 23 successi, 7 fallimenti
M1_UC1_MBAR  = 6.43


# ─────────────────────────────────────────────
# Funzione core: TOP-K senza classificatore
# ─────────────────────────────────────────────
def run_topk(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42, top_k=4):
    """Esegue M_TOP4: tenta i top_k candidati più frequenti per ogni iterazione."""
    base_qc = shor_circuit(N, a, n_count)
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = transpile(base_qc, sim, optimization_level=2)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(
            transpiled, shots=shots,
            seed_simulator=seed * 10000 + iteration
        ).result().get_counts()
        sorted_meas = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        for meas_str, _ in sorted_meas[:top_k]:
            p, q = extract_factors(int(meas_str, 2), n_count, N, a)
            if p is not None:
                return {'iterations': iteration, 'success': True}
    return {'iterations': max_iter, 'success': False}


# ─────────────────────────────────────────────
# Utilità statistica
# ─────────────────────────────────────────────
def summarize(results_list):
    iters_all = [r['iterations'] for r in results_list]
    iters_ok  = [r['iterations'] for r in results_list if r['success']]
    return {
        'M_bar':        float(np.mean(iters_ok))   if iters_ok else None,
        'std':          float(np.std(iters_ok))    if iters_ok else None,
        'median':       float(np.median(iters_ok)) if iters_ok else None,
        'success_rate': len(iters_ok) / len(results_list),
        'n_success':    len(iters_ok),
        'n_runs':       len(results_list),
        'all_iters':    iters_all,
    }


def mw_vs_m1(topk_iters, m1_iters=None):
    """Mann-Whitney U (unilaterale: M1 > TOP-K), ritorna (U, p)."""
    ref = m1_iters if m1_iters is not None else M1_UC1_ITERS
    u, p = mannwhitneyu(ref, topk_iters, alternative='greater')
    return float(u), float(p)


def rho(m_bar_topk, m_bar_m1=M1_UC1_MBAR):
    if m_bar_topk and m_bar_topk > 0:
        return round(m_bar_m1 / m_bar_topk, 3)
    return None


def fmt_p(p):
    if p < 0.001:
        return '${<}0.001$'
    return f'${p:.3f}$'


def sig(p):
    return '(sign.)' if p < 0.05 else '(n.s.)'


# ─────────────────────────────────────────────
# 1. Sweep K
# ─────────────────────────────────────────────
def sweep_k():
    print('\n' + '='*60)
    print('SWEEP 1: Variazione di K')
    print('='*60)

    k_values = [1, 2, 3, 4, 6, 8]
    nm = build_noise_model(**BASE_NOISE)
    results = {}

    for k in k_values:
        runs = []
        for rep in range(K_REPS):
            print(f'  K={k}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            r = run_topk(N, A, N_COUNT, nm,
                         shots=1024, max_iter=MAX_ITER, seed=rep, top_k=k)
            runs.append(r)
        s = summarize(runs)
        results[k] = s
        U, p = mw_vs_m1([r['iterations'] for r in runs])
        r_val = rho(s['M_bar'])
        print(f'  K={k}:  M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_k) ---')
    for k in k_values:
        s = results[k]
        iters = s['all_iters']
        U, p  = mw_vs_m1(iters)
        r_val = rho(s['M_bar'])
        mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
        std   = f"{s['std']:.2f}"   if s['std']   else '---'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        rval  = f"{r_val:.3f}"      if r_val      else '---'
        print(f'  {k} & {psucc} & {mbar} & {std} & {rval} & {fmt_p(p)} {sig(p)} \\\\')

    return results


# ─────────────────────────────────────────────
# 2. Sweep eps_2q
# ─────────────────────────────────────────────
def sweep_eps2q():
    print('\n' + '='*60)
    print('SWEEP 2: Variazione di eps_2q')
    print('='*60)

    eps_values = [1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1]
    results = {}

    for eps in eps_values:
        noise  = {**BASE_NOISE, 'eps_2q': eps}
        nm     = build_noise_model(**noise)
        p_surv = (1 - eps) ** 162

        # M1 con questo livello di rumore
        m1_runs = []
        topk_runs = []
        for rep in range(K_REPS):
            print(f'  eps={eps:.0e}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            m1_runs.append(
                run_method1(N, A, N_COUNT, nm,
                            shots=1024, max_iter=MAX_ITER, seed=rep))
            topk_runs.append(
                run_topk(N, A, N_COUNT, nm,
                         shots=1024, max_iter=MAX_ITER, seed=rep, top_k=4))

        s1  = summarize(m1_runs)
        stk = summarize(topk_runs)
        m1_iters  = [r['iterations'] for r in m1_runs]
        topk_iters = [r['iterations'] for r in topk_runs]
        U, p = mw_vs_m1(topk_iters, m1_iters)
        r_val = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None

        results[eps] = {'m1': s1, 'topk': stk, 'p_surv': p_surv}
        print(f'  eps={eps:.0e}  P_surv={p_surv:.2e}  '
              f'M1={s1["M_bar"]:.2f if s1["M_bar"] else "N/A"}  '
              f'TOP4={stk["M_bar"]:.2f if stk["M_bar"] else "N/A"}  '
              f'rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_eps) ---')
    for eps in eps_values:
        r = results[eps]
        s1  = r['m1']
        stk = r['topk']
        p_surv = r['p_surv']
        m1_iters   = s1['all_iters']
        topk_iters = stk['all_iters']
        U, p = mw_vs_m1(topk_iters, m1_iters)
        r_val = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None
        mbar1 = f"{s1['M_bar']:.2f}"  if s1['M_bar']  else 'N/A'
        mbartk= f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        rval  = f"{r_val:.3f}"        if r_val         else '---'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
        eps_str = f"$10^{{-{int(-np.log10(eps))}}}$" if eps in [1e-3,1e-2,1e-1] else \
                  f"${eps:.0e}$".replace('e-0', r'\times10^{-').replace('e-', r'\times10^{-') + '}'
        print(f'  {eps:.0e} & ${p_surv:.2e}$ & {mbar1} & {mbartk} & {rval} & {fmt_p(p)} {sig(p)} & {psucc} \\\\')

    return results


# ─────────────────────────────────────────────
# 3. Sweep shots
# ─────────────────────────────────────────────
def sweep_shots():
    print('\n' + '='*60)
    print('SWEEP 3: Variazione di shots')
    print('='*60)

    shots_values = [128, 256, 512, 1024, 2048]
    nm = build_noise_model(**BASE_NOISE)
    results = {}

    for shots in shots_values:
        runs = []
        for rep in range(K_REPS):
            print(f'  shots={shots}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            r = run_topk(N, A, N_COUNT, nm,
                         shots=shots, max_iter=MAX_ITER, seed=rep, top_k=4)
            runs.append(r)
        s = summarize(runs)
        results[shots] = s
        U, p = mw_vs_m1([r['iterations'] for r in runs])
        r_val = rho(s['M_bar'])
        print(f'  shots={shots}:  M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_shots) ---')
    for shots in shots_values:
        s = results[shots]
        U, p  = mw_vs_m1(s['all_iters'])
        r_val = rho(s['M_bar'])
        mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
        std   = f"{s['std']:.2f}"   if s['std']   else '---'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        rval  = f"{r_val:.3f}"      if r_val      else '---'
        print(f'  {shots} & {psucc} & {mbar} & {std} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# 4. Analisi congiunta K x eps_2q
# ─────────────────────────────────────────────
def sweep_joint():
    print('\n' + '='*60)
    print('SWEEP 4: Analisi congiunta K x eps_2q')
    print('='*60)

    k_values   = [2, 4, 6, 8]
    eps_values = [5e-3, 1e-2, 2e-2, 5e-2]
    results    = {}

    for k in k_values:
        results[k] = {}
        for eps in eps_values:
            noise = {**BASE_NOISE, 'eps_2q': eps}
            nm    = build_noise_model(**noise)
            runs  = []
            for rep in range(K_REPS):
                print(f'  K={k} eps={eps:.0e}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
                r = run_topk(N, A, N_COUNT, nm,
                             shots=1024, max_iter=MAX_ITER, seed=rep, top_k=k)
                runs.append(r)
            s = summarize(runs)
            results[k][eps] = s
            print(f'  K={k} eps={eps:.0e}:  '
                  f'M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
                  f'sr={s["success_rate"]:.1%}      ')

    print('\n--- LaTeX rows (tabella sweep_joint, M_bar) ---')
    header = ' & '.join([f'$\\varepsilon_{{2q}}={eps:.0e}$' for eps in eps_values])
    print(f'$K$ & {header} \\\\')
    for k in k_values:
        row_vals = []
        for eps in eps_values:
            s = results[k][eps]
            if s['M_bar'] is not None:
                val = f'{s["M_bar"]:.2f}'
                if s['M_bar'] <= 1.5:
                    val = f'\\textbf{{{val}}}'
            else:
                val = 'N/A'
            row_vals.append(val)
        print(f'  {k} & ' + ' & '.join(row_vals) + ' \\\\')

    return results


# ─────────────────────────────────────────────
# 5. Sweep T1/T2
# ─────────────────────────────────────────────
def sweep_t1t2():
    print('\n' + '='*60)
    print('SWEEP 5: Variazione di T1/T2')
    print('='*60)

    t1_values = [20_000, 50_000, 100_000, 200_000, 500_000]  # nanosecondi
    results   = {}

    for t1 in t1_values:
        t2    = int(t1 * 0.8)
        noise = {**BASE_NOISE, 't1_ns': t1, 't2_ns': t2}
        nm    = build_noise_model(**noise)
        runs  = []
        for rep in range(K_REPS):
            print(f'  T1={t1//1000}us  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            r = run_topk(N, A, N_COUNT, nm,
                         shots=1024, max_iter=MAX_ITER, seed=rep, top_k=4)
            runs.append(r)
        s = summarize(runs)
        results[t1] = s
        U, p  = mw_vs_m1([r['iterations'] for r in runs])
        r_val = rho(s['M_bar'])
        print(f'  T1={t1//1000}us T2={t2//1000}us:  '
              f'M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_t1) ---')
    for t1 in t1_values:
        s     = results[t1]
        t2    = int(t1 * 0.8)
        U, p  = mw_vs_m1(s['all_iters'])
        r_val = rho(s['M_bar'])
        mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
        std   = f"{s['std']:.2f}"   if s['std']   else '---'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        rval  = f"{r_val:.3f}"      if r_val      else '---'
        print(f'  {t1//1000} & {t2//1000} & {psucc} & {mbar} & {std} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# 6. Sweep eps_1q
# ─────────────────────────────────────────────
def sweep_eps1q():
    print('\n' + '='*60)
    print('SWEEP 6: Variazione di eps_1q (errore a singolo qubit)')
    print('='*60)

    eps1q_values = [1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 2e-2]
    results = {}

    for eps1q in eps1q_values:
        noise = {**BASE_NOISE, 'eps_1q': eps1q}
        nm    = build_noise_model(**noise)
        runs  = []
        for rep in range(K_REPS):
            print(f'  eps_1q={eps1q:.0e}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            r = run_topk(N, A, N_COUNT, nm,
                         shots=1024, max_iter=MAX_ITER, seed=rep, top_k=4)
            runs.append(r)
        s = summarize(runs)
        results[eps1q] = s
        U, p  = mw_vs_m1([r['iterations'] for r in runs])
        r_val = rho(s['M_bar'])
        print(f'  eps_1q={eps1q:.0e}:  M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_eps1q) ---')
    for eps1q in eps1q_values:
        s     = results[eps1q]
        U, p  = mw_vs_m1(s['all_iters'])
        r_val = rho(s['M_bar'])
        mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
        std   = f"{s['std']:.2f}"   if s['std']   else '---'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        rval  = f"{r_val:.3f}"      if r_val      else '---'
        print(f'  {eps1q:.0e} & {psucc} & {mbar} & {std} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# 7. Sweep p_ro
# ─────────────────────────────────────────────
def sweep_pro():
    print('\n' + '='*60)
    print('SWEEP 6: Variazione di p_ro (readout error)')
    print('='*60)

    pro_values = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20]
    nm_list    = {}
    results    = {}

    for p_ro in pro_values:
        noise = {**BASE_NOISE, 'p_ro': p_ro}
        nm    = build_noise_model(**noise)
        runs  = []
        for rep in range(K_REPS):
            print(f'  p_ro={p_ro:.0%}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            r = run_topk(N, A, N_COUNT, nm,
                         shots=1024, max_iter=MAX_ITER, seed=rep, top_k=4)
            runs.append(r)
        s = summarize(runs)
        results[p_ro] = s
        U, p  = mw_vs_m1([r['iterations'] for r in runs])
        r_val = rho(s['M_bar'])
        print(f'  p_ro={p_ro:.0%}:  M_bar={s["M_bar"]:.2f if s["M_bar"] else "N/A"}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_pro) ---')
    for p_ro in pro_values:
        s     = results[p_ro]
        U, p  = mw_vs_m1(s['all_iters'])
        r_val = rho(s['M_bar'])
        mbar  = f"{s['M_bar']:.2f}" if s['M_bar'] else 'N/A'
        std   = f"{s['std']:.2f}"   if s['std']   else '---'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        rval  = f"{r_val:.3f}"      if r_val      else '---'
        print(f'  {p_ro*100:.0f}\\% & {psucc} & {mbar} & {std} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sweep', default='all',
                        choices=['all', 'k', 'eps', 'shots', 'joint', 't1t2', 'pro'],
                        help='Quale sweep eseguire (default: all)')
    args = parser.parse_args()

    all_results = {}

    sweep_map = {
        'k':     ('sweep_k',      sweep_k),
        'eps':   ('sweep_eps2q',  sweep_eps2q),
        'shots': ('sweep_shots',  sweep_shots),
        'joint': ('sweep_joint',  sweep_joint),
        't1t2':  ('sweep_t1t2',   sweep_t1t2),
        'eps1q': ('sweep_eps1q',  sweep_eps1q),
        'pro':   ('sweep_pro',    sweep_pro),
    }

    to_run = list(sweep_map.keys()) if args.sweep == 'all' else [args.sweep]

    for key in to_run:
        name, fn = sweep_map[key]
        all_results[name] = fn()

    # Salva JSON
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f'results_parameter_analysis_{ts}.json'
    with open(fname, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f'\nRisultati salvati in: {fname}')
    print('Copia le righe LaTeX nelle tabelle di ConclusioniMetodo2.tex')


if __name__ == '__main__':
    main()
