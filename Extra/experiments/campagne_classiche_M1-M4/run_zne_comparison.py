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

import argparse
import json
import os
import numpy as np
from datetime import datetime
from pathlib import Path
from scipy.stats import wilcoxon
from qiskit_aer import AerSimulator

from shor_core import (
    build_noise_model,
    compile_shor_circuit,
    experiment_manifest,
    extract_factors,
    rank_measurements,
)

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
ZNE_ANALYSIS_REVISION = 'zne-digital-shared-levels-holm-v3'


def _atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


# ─────────────────────────────────────────────
# M_TOP4 (riferimento)
# ─────────────────────────────────────────────
def run_topk(noise_model, shots=1024, max_iter=50, seed=42, top_k=4):
    return run_topks(
        noise_model, shots=shots, max_iter=max_iter, seed=seed,
        top_ks=(top_k,),
    )[int(top_k)]


def run_topks(noise_model, shots=1024, max_iter=50, seed=42,
               top_ks=(1, 4)):
    """Valuta TOP-1/TOP-K sul medesimo istogramma base di ogni iterazione."""
    requested = tuple(sorted(set(int(value) for value in top_ks)))
    if not requested or requested[0] < 1:
        raise ValueError('top_ks deve contenere interi positivi.')
    sim        = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = compile_shor_circuit(N, A, N_COUNT)
    found = {value: None for value in requested}
    for iteration in range(1, max_iter + 1):
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        counts = sim.run(transpiled, shots=shots,
                         seed_simulator=simulation_seed).result().get_counts()
        sorted_meas = rank_measurements(counts, simulation_seed)
        valid = [
            extract_factors(int(meas_str, 2), N_COUNT, N, A)[0] is not None
            for meas_str, _ in sorted_meas[:requested[-1]]
        ]
        for top_k in requested:
            if found[top_k] is None and any(valid[:top_k]):
                found[top_k] = iteration
        if all(value is not None for value in found.values()):
            break
    return {
        top_k: {
            'iterations': value if value is not None else max_iter,
            'success': value is not None,
            'shots_used': (value if value is not None else max_iter) * shots,
        }
        for top_k, value in found.items()
    }


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
    sim        = AerSimulator(noise_model=nm, method='statevector')
    transpiled = compile_shor_circuit(N, A, N_COUNT)
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
    n = len(lambdas)
    L = np.asarray(lambdas, dtype=float)
    H = np.asarray(hists_by_lambda, dtype=float)  # shape (n, 2^N_COUNT)

    if n not in (2, 3):
        raise ValueError(f"Supportati solo 2 o 3 livelli di rumore, ricevuto {n}")
    if H.ndim != 2 or H.shape[0] != n:
        raise ValueError('Il numero di istogrammi deve coincidere con i lambda.')
    if not np.isfinite(L).all() or np.any(L <= 0) or len(np.unique(L)) != n:
        raise ValueError('I lambda devono essere finiti, positivi e distinti.')

    # Interpolazione di Lagrange valutata in lambda=0. Per le griglie usate
    # dalla campagna produce [2,-1] su (1,2) e [3,-3,1] su (1,2,3), ma evita
    # coefficienti scientificamente errati se l'helper riceve livelli diversi.
    coeffs = np.asarray([
        np.prod([
            -L[j] / (L[i] - L[j])
            for j in range(n) if j != i
        ])
        for i in range(n)
    ])

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
    result = run_zne_strategies(
        shots=shots, max_iter=max_iter, seed=seed,
        strategies={'requested': tuple(lambdas)}, top_k=top_k,
    )
    return result['requested']


def run_zne_strategies(shots=1024, max_iter=50, seed=42,
                       strategies=None, top_k=1):
    """Condivide P(lambda) fra piu' ordini di estrapolazione ZNE."""
    strategies = strategies or {'ZNE-2': (1, 2), 'ZNE-3': (1, 2, 3)}
    normalized = {
        str(name): tuple(float(value) for value in lambdas)
        for name, lambdas in strategies.items()
    }
    if not normalized or any(len(values) not in (2, 3) for values in normalized.values()):
        raise ValueError('Ogni strategia ZNE deve avere due o tre lambda.')
    if any(
        not np.isfinite(values).all()
        or any(value <= 0 for value in values)
        or len(set(values)) != len(values)
        for values in (np.asarray(item, dtype=float) for item in normalized.values())
    ):
        raise ValueError('I lambda ZNE devono essere finiti, positivi e distinti.')
    if type(top_k) is not int or not 1 <= top_k <= 2 ** N_COUNT:
        raise ValueError(f'top_k deve essere un intero in [1, {2 ** N_COUNT}].')
    all_lambdas = tuple(sorted({value for values in normalized.values() for value in values}))
    found = {name: None for name in normalized}

    for iteration in range(1, max_iter + 1):
        histograms = {
            lam: _run_at_lambda(lam, shots, seed, iteration)
            for lam in all_lambdas
        }
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        for name, lambdas in normalized.items():
            if found[name] is not None:
                continue
            extrap = _extrapolate([histograms[lam] for lam in lambdas], lambdas)
            distribution = {
                format(idx, f'0{N_COUNT}b'): probability
                for idx, probability in enumerate(extrap)
            }
            candidates = rank_measurements(distribution, simulation_seed)[:top_k]
            if any(
                extract_factors(int(bits, 2), N_COUNT, N, A)[0] is not None
                for bits, _ in candidates
            ):
                found[name] = iteration
        if all(value is not None for value in found.values()):
            break

    return {
        name: {
            'iterations': value if value is not None else max_iter,
            'success': value is not None,
            'shots_used': (
                (value if value is not None else max_iter)
                * shots * len(normalized[name])
            ),
        }
        for name, value in found.items()
    }


# ─────────────────────────────────────────────
# Utilità
# ─────────────────────────────────────────────
def summarize(results):
    ok       = [r for r in results if r['success']]
    iters_ok = [r['iterations'] for r in ok]
    shots_ok = [r['shots_used'] for r in ok]
    successes = len(ok)
    total = len(results)
    z = 1.959963984540054
    p_hat = successes / total
    denominator = 1 + z * z / total
    center = (p_hat + z * z / (2 * total)) / denominator
    half = z * np.sqrt(
        p_hat * (1 - p_hat) / total + z * z / (4 * total * total)
    ) / denominator
    return {
        'M_bar':        float(np.mean(iters_ok))   if ok else None,
        'std':          float(np.std(iters_ok))    if ok else None,
        'success_rate': successes / total,
        'success_rate_wilson95': [
            float(max(0, center - half)), float(min(1, center + half))
        ],
        'shots_mean':   float(np.mean(shots_ok))   if ok else None,
        'n_success':    len(ok),
        'mean_budget_used': float(np.mean([
            r['iterations'] for r in results
        ])),
        'mean_shots_used_all': float(np.mean([
            r['shots_used'] for r in results
        ])),
        'all_iters':    [r['iterations'] if r['success'] else MAX_ITER + 1
                         for r in results],
        'all_success':  [bool(r['success']) for r in results],
        'failure_sentinel': MAX_ITER + 1,
        'all_shots':    [r['shots_used'] for r in results],
    }


def paired_test(iters_a, iters_b):
    """Wilcoxon appaiato: a > b (a ha più iterazioni di b)."""
    a, b = np.asarray(iters_a), np.asarray(iters_b)
    if np.array_equal(a, b):
        return 0.0, 1.0
    result = wilcoxon(
        a, b, alternative='greater', zero_method='pratt', method='auto'
    )
    return float(result.statistic), float(result.pvalue)


def holm_adjust(tests):
    ordered = sorted(tests.items(), key=lambda item: item[1]['p'])
    running = 0.0
    total = len(ordered)
    for index, (_, test) in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * float(test['p'])))
        test['p_holm'] = running
    return tests


def sig(p):
    return '(sign.)' if p < 0.05 else '(n.s.)'


def fmt_p(p):
    return '${<}0.001$' if p < 0.001 else f'${p:.3f}$'


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    global K_REPS, SHOTS, MAX_ITER
    parser = argparse.ArgumentParser()
    parser.add_argument('--k-reps', type=int, default=K_REPS)
    parser.add_argument('--shots', type=int, default=SHOTS)
    parser.add_argument('--max-iter', type=int, default=MAX_ITER)
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    parser.add_argument('--no-resume', action='store_true')
    args = parser.parse_args()
    if args.k_reps < 1 or args.shots < 1 or args.max_iter < 1:
        raise ValueError('k-reps, shots e max-iter devono essere positivi.')
    K_REPS, SHOTS, MAX_ITER = args.k_reps, args.shots, args.max_iter
    nm = build_noise_model(**BASE_NOISE)

    config = {
        'K_REPS': K_REPS,
        'SHOTS': SHOTS,
        'MAX_ITER': MAX_ITER,
        'zne_scaling': ('eps_1q/eps_2q scalati; T1/T2 e readout fissi; '
                        'non e gate-folding hardware'),
    }
    manifest = experiment_manifest()
    checkpoint_path = args.output_dir / 'zne_checkpoint_v3.json'
    strategies = {
        'M1':     [],
        'ZNE-2':  [],
        'ZNE-3':  [],
        'TOP4':   [],
    }
    if not args.no_resume and checkpoint_path.is_file():
        candidate = json.loads(checkpoint_path.read_text(encoding='utf-8'))
        if (candidate.get('schema_version') != '2.0'
                or candidate.get('analysis_revision') != ZNE_ANALYSIS_REVISION
                or candidate.get('config') != config
                or candidate.get('manifest') != manifest):
            raise ValueError(
                f'Checkpoint ZNE incompatibile: {checkpoint_path}. Usare --no-resume.'
            )
        raw_strategies = candidate.get('strategies_raw')
        if not isinstance(raw_strategies, dict) or set(raw_strategies) != set(strategies):
            raise ValueError('Checkpoint ZNE privo delle quattro strategie attese.')
        lengths = {len(raw_strategies[name]) for name in strategies}
        if len(lengths) != 1 or next(iter(lengths)) > K_REPS:
            raise ValueError('Checkpoint ZNE con numero di repliche incoerente.')
        strategies = {name: list(raw_strategies[name]) for name in strategies}
        print(f'Ripresa ZNE da {len(strategies["M1"])}/{K_REPS} repliche.')

    start_rep = len(strategies['M1'])
    for rep in range(start_rep, K_REPS):
        print(f'Rep {rep+1}/{K_REPS}', end='\r', flush=True)

        # M1 e TOP-4 condividono gli stessi istogrammi base.
        base = run_topks(
            nm, shots=SHOTS, max_iter=MAX_ITER, seed=rep, top_ks=(1, 4)
        )
        strategies['M1'].append(base[1])
        strategies['TOP4'].append(base[4])

        zne = run_zne_strategies(
            shots=SHOTS, max_iter=MAX_ITER, seed=rep,
            strategies={'ZNE-2': (1, 2), 'ZNE-3': (1, 2, 3)}, top_k=1,
        )
        strategies['ZNE-2'].append(zne['ZNE-2'])
        strategies['ZNE-3'].append(zne['ZNE-3'])
        _atomic_json(checkpoint_path, {
            'schema_version': '2.0',
            'analysis_revision': ZNE_ANALYSIS_REVISION,
            'config': config,
            'manifest': manifest,
            'completed_reps': rep + 1,
            'strategies_raw': strategies,
        })

    print()

    summaries = {k: summarize(v) for k, v in strategies.items()}
    m1_iters = summaries['M1']['all_iters']
    comparisons = {}
    for name in ['ZNE-2', 'ZNE-3', 'TOP4']:
        statistic, p_value = paired_test(
            m1_iters, summaries[name]['all_iters']
        )
        comparisons[name] = {
            'W': statistic, 'p': p_value,
            'alternative': 'greater',
        }
    holm_adjust(comparisons)

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
    print(f'\n  Wilcoxon appaiato (M1 > strategia):')
    for name in ['ZNE-2', 'ZNE-3', 'TOP4']:
        test = comparisons[name]
        print(f'    M1 > {name:<8}: W={test["W"]:.0f}  '
              f'p_Holm={test["p_holm"]:.4f}  {sig(test["p_holm"])}')

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
        p = comparisons[key]['p_holm'] if key != 'M1' else 1.0
        rho   = round(m1_mbar / s['M_bar'], 3) if s['M_bar'] and key != 'M1' else None
        mbar  = f"{s['M_bar']:.2f}"    if s['M_bar'] else 'N/A'
        psucc = f"{s['success_rate']*100:.1f}\\%"
        tot   = f"{s['shots_mean']:.0f}" if s['shots_mean'] else 'N/A'
        rval  = f"{rho:.3f}" if rho else '---'
        pval  = fmt_p(p) + f' {sig(p)}' if key != 'M1' else '---'
        print(f'  {label} & {psucc} & {mbar} & {shots_iter} & {tot} & {rval} & {pval} \\\\')

    # ── Salva JSON ────────────────────────────
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fname = args.output_dir / f'results_zne_comparison_v2_{ts}.json'
    payload = {
        'schema_version': '2.0',
        'analysis_revision': ZNE_ANALYSIS_REVISION,
        'timestamp': datetime.now().isoformat(),
        'config': config,
        'manifest': manifest,
        'strategies': summaries,
        'comparisons_vs_M1': comparisons,
        'multiplicity': {'method': 'Holm', 'alpha': 0.05},
    }
    _atomic_json(fname, payload)
    print(f'\nRisultati salvati in: {fname}')
    print('Copia le righe LaTeX nella tabella confronto_zne in ConclusioniMetodo2.tex')


if __name__ == '__main__':
    main()
