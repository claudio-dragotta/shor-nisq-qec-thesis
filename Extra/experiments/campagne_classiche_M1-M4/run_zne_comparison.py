"""
run_zne_comparison.py — Confronto M1 vs ZNE-2 vs ZNE-3 vs M_TOP4 su UC1.

Zero-Noise Extrapolation applicata all'algoritmo di Shor (N=15, UC1):
  - ZNE-2: estrapolazione lineare con lambda = [1, 2]
  - ZNE-3: Richardson quadratica con lambda = [1, 2, 3]

Metrica principale: M_bar (iterazioni medie a convergenza) e shot totali.

Eseguire da WSL:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python run_zne_comparison.py
"""

import json
import numpy as np
from datetime import datetime
from scipy.stats import mannwhitneyu
from qiskit import transpile
from qiskit_aer import AerSimulator

from shor_core import build_noise_model, shor_circuit, extract_factors, run_method1

# ─────────────────────────────────────────────
# Configurazione (UC1)
# ─────────────────────────────────────────────
BASE_NOISE = {
    'eps_1q': 1e-3,
    'eps_2q': 1e-2,
    't1_ns':  100_000,
    't2_ns':  80_000,
    'p_ro':   0.02,
}

N        = 15
A        = 7
N_COUNT  = 8
K_REPS   = 30
SHOTS    = 1024
MAX_ITER = 50


# ─────────────────────────────────────────────
# M_TOP4 (riferimento)
# ─────────────────────────────────────────────
def run_topk(noise_model, shots=1024, max_iter=50, seed=42, top_k=4):
    base_qc    = shor_circuit(N, A, N_COUNT)
    sim        = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = transpile(base_qc, sim, optimization_level=2)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=seed * 1_000_000 + iteration * 10_000).result().get_counts()
        sorted_meas = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        for meas_str, _ in sorted_meas[:top_k]:
            p, q = extract_factors(int(meas_str, 2), N_COUNT, N, A)
            if p is not None:
                return {'iterations': iteration, 'success': True,
                        'shots_used': iteration * shots}
    return {'iterations': max_iter, 'success': False,
            'shots_used': max_iter * shots}


# ─────────────────────────────────────────────
# ZNE: esecuzione a più livelli di rumore e extrapolazione
# ─────────────────────────────────────────────
def _run_at_lambda(lam, shots, seed, iteration):
    """Esegue il circuito con rumore scalato di lam e ritorna l'istogramma normalizzato."""
    scaled = {
        'eps_1q': BASE_NOISE['eps_1q'] * lam,
        'eps_2q': min(BASE_NOISE['eps_2q'] * lam, 0.999),  # clamp a <1
        't1_ns':  BASE_NOISE['t1_ns'],
        't2_ns':  BASE_NOISE['t2_ns'],
        'p_ro':   BASE_NOISE['p_ro'],
    }
    nm         = build_noise_model(**scaled)
    base_qc    = shor_circuit(N, A, N_COUNT)
    sim        = AerSimulator(noise_model=nm, method='statevector')
    transpiled = transpile(base_qc, sim, optimization_level=2)
    counts     = sim.run(transpiled, shots=shots,
                         seed_simulator=seed * 1_000_000 + iteration * 10_000).result().get_counts()
    hist = np.zeros(2 ** N_COUNT)
    for k, v in counts.items():
        hist[int(k, 2)] = v / shots
    return hist


def _extrapolate(hists_by_lambda, lambdas):
    """
    Richardson extrapolation verso lambda=0.
    lambdas: lista di valori (es. [1,2] o [1,2,3])
    hists:   lista di istogrammi corrispondenti
    """
    n  = len(lambdas)
    L  = np.array(lambdas, dtype=float)
    H  = np.array(hists_by_lambda)  # shape (n, 2^N_COUNT)

    if n == 2:
        # Lineare: P0 = 2*P(1) - P(2)
        coeffs = np.array([2.0, -1.0])
    elif n == 3:
        # Quadratica (Richardson 3 punti verso 0):
        # P0 = 3*P(1) - 3*P(2) + P(3)
        coeffs = np.array([3.0, -3.0, 1.0])
    else:
        raise ValueError(f"Supportati solo 2 o 3 livelli di rumore, ricevuto {n}")

    extrap = np.einsum('i,ij->j', coeffs, H)

    # Clippa valori negativi e rinormalizza
    extrap = np.clip(extrap, 0, None)
    total  = extrap.sum()
    if total > 0:
        extrap /= total
    return extrap


def run_zne(noise_model, shots=1024, max_iter=50, seed=42, lambdas=(1, 2), top_k=1):
    """
    ZNE applicata a Shor:
      1. Per ogni iterazione, esegue il circuito a ciascun lambda
      2. Estrapola l'istogramma a lambda=0
      3. Tenta top_k candidati dall'istogramma estrapolato
    """
    n_levels   = len(lambdas)
    shots_iter = shots * n_levels  # shot totali per iterazione ZNE

    for iteration in range(1, max_iter + 1):
        hists = [_run_at_lambda(lam, shots, seed, iteration) for lam in lambdas]
        extrap = _extrapolate(hists, lambdas)

        # Top-K candidati dall'istogramma estrapolato
        top_indices = np.argsort(extrap)[::-1][:top_k]
        for idx in top_indices:
            p, q = extract_factors(int(idx), N_COUNT, N, A)
            if p is not None:
                return {'iterations': iteration, 'success': True,
                        'shots_used': iteration * shots_iter}

    return {'iterations': max_iter, 'success': False,
            'shots_used': max_iter * shots_iter}


# ─────────────────────────────────────────────
# Utilità
# ─────────────────────────────────────────────
def summarize(results):
    ok       = [r for r in results if r['success']]
    iters_ok = [r['iterations'] for r in ok]
    shots_ok = [r['shots_used'] for r in ok]
    return {
        'M_bar':        float(np.mean(iters_ok))   if ok else None,
        'std':          float(np.std(iters_ok))    if ok else None,
        'success_rate': len(ok) / len(results),
        'shots_mean':   float(np.mean(shots_ok))   if ok else None,
        'n_success':    len(ok),
        'all_iters':    [r['iterations'] for r in results],
        'all_shots':    [r['shots_used'] for r in results],
    }


def mw_test(iters_a, iters_b):
    """Mann-Whitney U: a > b (a ha più iterazioni di b)."""
    u, p = mannwhitneyu(iters_a, iters_b, alternative='greater')
    return float(u), float(p)


def sig(p):
    return '(sign.)' if p < 0.05 else '(n.s.)'


def fmt_p(p):
    return '${<}0.001$' if p < 0.001 else f'${p:.3f}$'


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    nm = build_noise_model(**BASE_NOISE)

    strategies = {
        'M1':     [],
        'ZNE-2':  [],
        'ZNE-3':  [],
        'TOP4':   [],
    }

    for rep in range(K_REPS):
        print(f'Rep {rep+1}/{K_REPS}', end='\r', flush=True)

        # M1
        r = run_method1(N, A, N_COUNT, nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep)
        strategies['M1'].append({
            'iterations': r['iterations'],
            'success':    r['success'],
            'shots_used': r['iterations'] * SHOTS,
        })

        # ZNE-2 (lambda = 1, 2)
        strategies['ZNE-2'].append(
            run_zne(nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep,
                    lambdas=(1, 2), top_k=1))

        # ZNE-3 (lambda = 1, 2, 3)
        strategies['ZNE-3'].append(
            run_zne(nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep,
                    lambdas=(1, 2, 3), top_k=1))

        # M_TOP4
        strategies['TOP4'].append(
            run_topk(nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep, top_k=4))

    print()

    summaries = {k: summarize(v) for k, v in strategies.items()}

    # ── Stampa risultati ──────────────────────
    print(f'\n{"="*70}')
    print('CONFRONTO M1 vs ZNE-2 vs ZNE-3 vs M_TOP4')
    print(f'{"="*70}')
    for name, s in summaries.items():
        shots_iter = {'M1': SHOTS, 'ZNE-2': SHOTS*2, 'ZNE-3': SHOTS*3, 'TOP4': SHOTS}[name]
        mbar  = f"{s['M_bar']:.2f}"   if s['M_bar']      else 'N/A'
        shots = f"{s['shots_mean']:.0f}" if s['shots_mean'] else 'N/A'
        print(f"  {name:<10} sr={s['success_rate']:.1%}  M_bar={mbar}  "
              f"shot/iter={shots_iter}  tot_shots={shots}")

    # ── Test statistici vs M1 ─────────────────
    m1_iters = summaries['M1']['all_iters']
    print(f'\n  Mann-Whitney (M1 > strategia):')
    for name in ['ZNE-2', 'ZNE-3', 'TOP4']:
        U, p = mw_test(m1_iters, summaries[name]['all_iters'])
        print(f'    M1 > {name:<8}: U={U:.0f}  p={p:.4f}  {sig(p)}')

    # ── Righe LaTeX ───────────────────────────
    print(f'\n--- LaTeX rows (tabella confronto_zne) ---')
    m1_iters  = summaries['M1']['all_iters']
    m1_mbar   = summaries['M1']['M_bar']

    rows = [
        ('M1 (baseline)',          'M1',    SHOTS),
        ('ZNE-2 (lineare)',        'ZNE-2', SHOTS*2),
        ('ZNE-3 (Richardson)',     'ZNE-3', SHOTS*3),
        ('$M_{\\text{TOP4}}$',     'TOP4',  SHOTS),
    ]

    for label, key, shots_iter in rows:
        s     = summaries[key]
        iters = s['all_iters']
        U, p  = mw_test(m1_iters, iters) if key != 'M1' else (0, 1.0)
        rho   = round(m1_mbar / s['M_bar'], 3) if s['M_bar'] and key != 'M1' else None
        mbar  = f"{s['M_bar']:.2f}"    if s['M_bar'] else 'N/A'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        tot   = f"{s['shots_mean']:.0f}" if s['shots_mean'] else 'N/A'
        rval  = f"{rho:.3f}" if rho else '---'
        pval  = fmt_p(p) + f' {sig(p)}' if key != 'M1' else '---'
        print(f'  {label} & {psucc} & {mbar} & {shots_iter} & {tot} & {rval} & {pval} \\\\')

    # ── Salva JSON ────────────────────────────
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f'results_zne_comparison_{ts}.json'
    with open(fname, 'w') as f:
        json.dump({k: {**v, 'all_iters': v['all_iters'], 'all_shots': v['all_shots']}
                   for k, v in summaries.items()}, f, indent=2)
    print(f'\nRisultati salvati in: {fname}')
    print('Copia le righe LaTeX nella tabella confronto_zne in ConclusioniMetodo2.tex')


if __name__ == '__main__':
    main()
