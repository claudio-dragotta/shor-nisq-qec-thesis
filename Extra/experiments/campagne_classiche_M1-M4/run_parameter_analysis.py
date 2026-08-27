"""
run_parameter_analysis.py — Analisi sperimentale sistematica dei parametri di mitigazione.

Esegue 8 sweep per la strategia M_TOPK (TOP-K senza classificatore):
  1. Variazione di K              : K = 1, 2, 3, 4, 6, 8
  2. Variazione di eps_2q         : 0.001, 0.005, 0.01, 0.02, 0.05, 0.10
  3. Variazione di shots          : 128, 256, 512, 1024, 2048
  4. Analisi congiunta K x eps_2q : griglia 4x4
  5. Variazione di T1/T2          : 20, 50, 100, 200, 500 us
  6. Variazione di eps_1q         : 1e-4 ... 2e-2
  7. Variazione di p_ro           : 0%, 1%, 2%, 5%, 10%, 20%
  8. Livello di ottimizzazione    : 0, 1, 2, 3

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
import argparse
import os
import numpy as np
from datetime import datetime
from pathlib import Path
from numbers import Integral
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
DEFAULT_SHOTS = 1024
PARAMETER_ANALYSIS_REVISION = 'parameter-analysis-shared-hist-v4'

# Questi valori vengono ricalcolati all'avvio sul circuito/modello correnti. Non usare
# piu' la vecchia approssimazione [1]*23+[50]*7: oltre a provenire dal circuito errato,
# confondeva il fallimento con un successo alla cinquantesima iterazione.
M1_UC1_ITERS = None
M1_UC1_MBAR = None


def _atomic_json(path, payload):
    """Checkpoint JSON atomico, così un'interruzione conserva l'ultima famiglia completa."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, default=str, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _restore_m1_reference(summary):
    global M1_UC1_ITERS, M1_UC1_MBAR
    if not isinstance(summary, dict):
        raise ValueError('Checkpoint privo di baseline_m1 valida.')
    values = summary.get('all_iters')
    if not isinstance(values, list) or len(values) != K_REPS:
        raise ValueError('Checkpoint con baseline_m1 incompatibile con K_REPS.')
    if not all(isinstance(value, int) and value >= 1 for value in values):
        raise ValueError('Checkpoint con iterazioni baseline non valide.')
    m_bar = summary.get('M_bar')
    if m_bar is not None and (not np.isfinite(float(m_bar)) or float(m_bar) <= 0):
        raise ValueError('Checkpoint con M_bar baseline non valido.')
    M1_UC1_ITERS = list(values)
    M1_UC1_MBAR = None if m_bar is None else float(m_bar)


# ─────────────────────────────────────────────
# Funzione core: TOP-K senza classificatore
# ─────────────────────────────────────────────
def run_topk(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42,
             top_k=4, compiled_circuit=None):
    """Compatibilita': esegue una sola strategia tramite ``run_topks``."""
    return run_topks(
        N, a, n_count, noise_model, shots=shots, max_iter=max_iter,
        seed=seed, top_ks=(top_k,), compiled_circuit=compiled_circuit,
    )[int(top_k)]


def run_topks(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42,
              top_ks=(1, 4), compiled_circuit=None):
    """Valuta piu' valori di K sugli stessi istogrammi di ciascuna replica.

    Il confronto TOP-1/TOP-K e' cosi' appaiato per costruzione e una griglia di K
    non rilancia Aer per dati identici.
    """
    if isinstance(n_count, bool) or not isinstance(n_count, Integral) or n_count < 1:
        raise ValueError('n_count deve essere un intero positivo.')
    raw_top_ks = tuple(top_ks)
    if not raw_top_ks or any(
        isinstance(value, bool) or not isinstance(value, Integral)
        for value in raw_top_ks
    ):
        raise ValueError('top_ks deve contenere soltanto interi positivi.')
    requested = tuple(sorted(set(int(value) for value in raw_top_ks)))
    if requested[0] < 1 or requested[-1] > 2 ** int(n_count):
        raise ValueError(f'top_ks deve appartenere a [1, {2 ** int(n_count)}].')
    if isinstance(shots, bool) or not isinstance(shots, Integral) or shots < 1:
        raise ValueError('shots deve essere un intero positivo.')
    if isinstance(max_iter, bool) or not isinstance(max_iter, Integral) or max_iter < 1:
        raise ValueError('max_iter deve essere un intero positivo.')
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError('seed deve essere un intero non negativo.')
    maximum_simulator_seed = int(seed) * 1_000_000 + int(max_iter) * 10_000
    if maximum_simulator_seed > 2 ** 31 - 1:
        raise ValueError('seed/max_iter generano un seed_simulator oltre 2**31-1.')
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    transpiled = (
        compiled_circuit
        if compiled_circuit is not None
        else compile_shor_circuit(N, a, n_count)
    )
    found = {value: None for value in requested}
    for iteration in range(1, max_iter + 1):
        simulation_seed = seed * 1_000_000 + iteration * 10_000
        counts = sim.run(
            transpiled, shots=shots,
            seed_simulator=simulation_seed
        ).result().get_counts()
        sorted_meas = rank_measurements(counts, simulation_seed)
        valid = [
            extract_factors(int(meas_str, 2), n_count, N, a)[0] is not None
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
            'failure_sentinel': int(max_iter) + 1,
            'pair_id': int(seed),
        }
        for top_k, value in found.items()
    }


# ─────────────────────────────────────────────
# Utilità statistica
# ─────────────────────────────────────────────
def summarize(results_list):
    if not results_list:
        raise ValueError('results_list non puo essere vuoto.')
    sentinels = {
        int(result.get('failure_sentinel', MAX_ITER + 1))
        for result in results_list
    }
    if len(sentinels) != 1:
        raise ValueError('Tutte le repliche devono condividere lo stesso failure_sentinel.')
    failure_sentinel = sentinels.pop()
    if failure_sentinel < 2:
        raise ValueError('failure_sentinel deve essere almeno 2.')
    for result in results_list:
        if not isinstance(result.get('success'), (bool, np.bool_)):
            raise ValueError('Ogni replica deve contenere un booleano success.')
        iteration = result.get('iterations')
        if isinstance(iteration, bool) or not isinstance(iteration, Integral):
            raise ValueError('Ogni replica deve contenere iterations intero.')
        if not 1 <= int(iteration) < failure_sentinel:
            raise ValueError('iterations deve essere nel budget [1, failure_sentinel).')
    pair_id_presence = ['pair_id' in result for result in results_list]
    if any(pair_id_presence) and not all(pair_id_presence):
        raise ValueError('pair_id deve essere presente in tutte le repliche oppure in nessuna.')
    pair_ids = [result['pair_id'] for result in results_list] if all(pair_id_presence) else None
    if pair_ids is not None and len(set(pair_ids)) != len(pair_ids):
        raise ValueError('pair_id deve essere univoco entro ciascuna condizione.')
    iters_all = [
        int(r['iterations']) if r['success'] else failure_sentinel
        for r in results_list
    ]
    iters_ok  = [int(r['iterations']) for r in results_list if r['success']]
    successes = len(iters_ok)
    total = len(results_list)
    z = 1.959963984540054
    p_hat = successes / total
    denominator = 1 + z * z / total
    center = (p_hat + z * z / (2 * total)) / denominator
    half = z * np.sqrt(
        p_hat * (1 - p_hat) / total + z * z / (4 * total * total)
    ) / denominator
    return {
        'M_bar':        float(np.mean(iters_ok))   if iters_ok else None,
        'std':          float(np.std(iters_ok))    if iters_ok else None,
        'median':       float(np.median(iters_ok)) if iters_ok else None,
        'success_rate': successes / total,
        'success_rate_wilson95': [
            float(max(0, center - half)), float(min(1, center + half))
        ],
        'n_success':    successes,
        'n_runs':       total,
        'mean_budget_used': float(np.mean([
            r['iterations'] for r in results_list
        ])),
        'median_budget_used': float(np.median([
            r['iterations'] for r in results_list
        ])),
        'all_iters':    iters_all,
        'all_success':  [bool(r['success']) for r in results_list],
        'failure_sentinel': failure_sentinel,
        'pair_ids': pair_ids,
    }


def paired_vs_m1(topk_iters, m1_iters=None):
    """Wilcoxon appaiato unilaterale (M1 > TOP-K), ritorna (W, p)."""
    ref = m1_iters if m1_iters is not None else M1_UC1_ITERS
    if ref is None:
        raise RuntimeError('Baseline M1 non inizializzata.')
    ref = np.asarray(ref, dtype=float)
    topk_iters = np.asarray(topk_iters, dtype=float)
    if ref.ndim != 1 or topk_iters.ndim != 1 or len(ref) == 0:
        raise ValueError('Wilcoxon richiede due vettori monodimensionali non vuoti.')
    if len(ref) != len(topk_iters):
        raise ValueError('Wilcoxon appaiato richiede vettori della stessa lunghezza.')
    if not np.isfinite(ref).all() or not np.isfinite(topk_iters).all():
        raise ValueError('I vettori Wilcoxon devono contenere valori finiti.')
    if np.array_equal(ref, topk_iters):
        return 0.0, 1.0
    result = wilcoxon(
        ref, topk_iters, alternative='greater',
        zero_method='pratt', method='auto',
    )
    return float(result.statistic), float(result.pvalue)


def summarize_pair(m1_runs, topk_runs):
    """Contratto comune per un confronto TOP-1/TOP-K sulla stessa condizione."""
    if len(m1_runs) != len(topk_runs) or not m1_runs:
        raise ValueError('Una coppia M1/TOP-K richiede lo stesso numero di repliche non vuote.')
    m1 = summarize(m1_runs)
    topk = summarize(topk_runs)
    if m1['failure_sentinel'] != topk['failure_sentinel']:
        raise ValueError('M1 e TOP-K devono condividere lo stesso failure_sentinel.')
    if m1['pair_ids'] is None or m1['pair_ids'] != topk['pair_ids']:
        raise ValueError('M1 e TOP-K devono condividere gli stessi pair_id nello stesso ordine.')
    statistic, p_value = paired_vs_m1(topk['all_iters'], m1['all_iters'])
    return {
        'm1': m1,
        'topk': topk,
        'rho': rho(topk['M_bar'], m1['M_bar']) if m1['M_bar'] else None,
        'pairing': {
            'paired': True,
            'unit': 'replicate_seed_and_condition',
            'same_histograms_within_replica': True,
            'n_pairs': len(m1_runs),
            'failure_sentinel': m1['failure_sentinel'],
            'pair_ids': m1['pair_ids'],
        },
        'wilcoxon_M1_gt_TOPK': {
            'W': statistic,
            'p': p_value,
            'alternative': 'greater',
            'zero_method': 'pratt',
        },
    }


def rho(m_bar_topk, m_bar_m1=None):
    if m_bar_m1 is None:
        m_bar_m1 = M1_UC1_MBAR
    if m_bar_topk and m_bar_topk > 0:
        return round(m_bar_m1 / m_bar_topk, 3)
    return None


def prepare_m1_reference():
    """Ricalcola la baseline che alimenta rho e Wilcoxon degli sweep."""
    global M1_UC1_ITERS, M1_UC1_MBAR
    print('\nCalibrazione baseline M1 sul contratto sperimentale corrente ...')
    nm = build_noise_model(**BASE_NOISE)
    runs = [
        run_topks(
            N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
            max_iter=MAX_ITER, seed=rep, top_ks=(1,),
        )[1]
        for rep in range(K_REPS)
    ]
    summary = summarize(runs)
    M1_UC1_ITERS = summary['all_iters']
    M1_UC1_MBAR = summary['M_bar']
    print(f"  M1: successo={summary['success_rate']:.1%}, "
          f"M_bar={summary['M_bar']}")
    return summary


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
    runs = {k: [] for k in k_values}
    for rep in range(K_REPS):
        print(f'  griglia K  rep {rep+1}/{K_REPS}', end='\r', flush=True)
        outcomes = run_topks(
            N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
            max_iter=MAX_ITER, seed=rep, top_ks=k_values,
        )
        for k in k_values:
            runs[k].append(outcomes[k])

    # K=1 e tutti gli altri K sono stati valutati sugli stessi istogrammi.
    # Conserviamo quindi il contratto appaiato invece di confrontare ogni K con
    # la baseline separata calcolata da ``prepare_m1_reference``.
    results = {
        k: summarize_pair(runs[1], runs[k])
        for k in k_values
    }
    for k in k_values:
        pair = results[k]
        s = pair['topk']
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        r_val = pair['rho']
        mbar_str = f'{s["M_bar"]:.2f}' if s['M_bar'] is not None else 'N/A'
        print(f'  K={k}:  M_bar={mbar_str}  '
              f'sr={s["success_rate"]:.1%}  rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_k) ---')
    for k in k_values:
        pair = results[k]
        s = pair['topk']
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        r_val = pair['rho']
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

    # Tutte le operazioni 2Q vengono decomposte in CX prima della simulazione;
    # non esistono quindi CP/SWAP opache che possano sfuggire a eps_2q.
    _ops = dict(compile_shor_circuit(N, A, N_COUNT).count_ops())
    k_2q = _ops.get('cx', 0)
    print(f'  porte soggette a errore 2q: k={k_2q}  ({_ops})')

    for eps in eps_values:
        noise  = {**BASE_NOISE, 'eps_2q': eps}
        nm     = build_noise_model(**noise)
        # In Qiskit ``eps`` e' lambda nella mappa
        # E(rho)=(1-lambda)rho+lambda I/4. Nella rappresentazione Pauli 2Q,
        # l'identita' ha quindi peso 1-15*lambda/16. Questa e' soltanto la
        # probabilita' proxy di nessun Pauli non-identita' sui CX, non la
        # probabilita' di successo del circuito (termico/readout restano attivi).
        p_surv = (1 - 15 * eps / 16) ** k_2q

        # M1 con questo livello di rumore
        m1_runs = []
        topk_runs = []
        for rep in range(K_REPS):
            print(f'  eps={eps:.0e}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=(1, 4),
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])

        pair = summarize_pair(m1_runs, topk_runs)
        s1, stk = pair['m1'], pair['topk']
        m1_iters = s1['all_iters']
        topk_iters = stk['all_iters']
        U, p = paired_vs_m1(topk_iters, m1_iters)
        r_val = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None

        results[eps] = {
            **pair,
            'p_no_nonidentity_2q_proxy': p_surv,
        }
        mbar1_str = f'{s1["M_bar"]:.2f}' if s1['M_bar'] is not None else 'N/A'
        mbartk_str = f'{stk["M_bar"]:.2f}' if stk['M_bar'] is not None else 'N/A'
        print(f'  eps={eps:.0e}  P_no-Pauli-2q={p_surv:.2e}  '
              f'M1={mbar1_str}  '
              f'TOP4={mbartk_str}  '
              f'rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_eps) ---')
    for eps in eps_values:
        r = results[eps]
        s1  = r['m1']
        stk = r['topk']
        p_surv = r['p_no_nonidentity_2q_proxy']
        m1_iters   = s1['all_iters']
        topk_iters = stk['all_iters']
        U, p = paired_vs_m1(topk_iters, m1_iters)
        r_val = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None
        mbar1 = f"{s1['M_bar']:.2f}"  if s1['M_bar']  else 'N/A'
        mbartk= f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        rval  = f"{r_val:.3f}"        if r_val         else '---'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
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
        m1_runs, topk_runs = [], []
        for rep in range(K_REPS):
            print(f'  shots={shots}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=shots, max_iter=MAX_ITER,
                seed=rep, top_ks=(1, 4),
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])
        pair = summarize_pair(m1_runs, topk_runs)
        results[shots] = pair
        s1, stk = pair['m1'], pair['topk']
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        print(f'  shots={shots}: M1={s1["M_bar"]}  TOP4={stk["M_bar"]}  '
              f'sr4={stk["success_rate"]:.1%}  rho={pair["rho"]}  '
              f'p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_shots) ---')
    for shots in shots_values:
        pair = results[shots]
        s1, stk = pair['m1'], pair['topk']
        mbar1 = f"{s1['M_bar']:.2f}" if s1['M_bar'] else 'N/A'
        mbartk = f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
        rval = f"{pair['rho']:.3f}" if pair['rho'] else '---'
        print(f'  {shots} & {mbar1} & {mbartk} & {psucc} & {rval} \\\\')

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
    runs = {k: {eps: [] for eps in eps_values} for k in k_values}
    for eps in eps_values:
        noise = {**BASE_NOISE, 'eps_2q': eps}
        nm = build_noise_model(**noise)
        for rep in range(K_REPS):
            print(f'  griglia K eps={eps:.0e}  rep {rep+1}/{K_REPS}',
                  end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=k_values,
            )
            for k in k_values:
                runs[k][eps].append(outcomes[k])

    results = {
        k: {eps: summarize(values) for eps, values in by_eps.items()}
        for k, by_eps in runs.items()
    }
    for k in k_values:
        for eps in eps_values:
            summary = results[k][eps]
            print(f'  K={k} eps={eps:.0e}: M_bar={summary["M_bar"]} '
                  f'sr={summary["success_rate"]:.1%}')

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
        m1_runs, topk_runs = [], []
        for rep in range(K_REPS):
            print(f'  T1={t1//1000}us  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=(1, 4),
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])
        pair = summarize_pair(m1_runs, topk_runs)
        pair['t2_ns'] = t2
        results[t1] = pair
        s1, stk = pair['m1'], pair['topk']
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        print(f'  T1={t1//1000}us T2={t2//1000}us:  '
              f'M1={s1["M_bar"]} TOP4={stk["M_bar"]} '
              f'sr4={stk["success_rate"]:.1%} rho={pair["rho"]} '
              f'p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_t1) ---')
    for t1 in t1_values:
        pair = results[t1]
        s1, stk = pair['m1'], pair['topk']
        t2 = pair['t2_ns']
        mbar1 = f"{s1['M_bar']:.2f}" if s1['M_bar'] else 'N/A'
        mbartk = f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
        rval = f"{pair['rho']:.3f}" if pair['rho'] else '---'
        print(f'  {t1//1000} & {t2//1000} & {mbar1} & {mbartk} & '
              f'{psucc} & {rval} \\\\')

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
        m1_runs, topk_runs = [], []
        for rep in range(K_REPS):
            print(f'  eps_1q={eps1q:.0e}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=(1, 4),
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])
        pair = summarize_pair(m1_runs, topk_runs)
        results[eps1q] = pair
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        print(f'  eps_1q={eps1q:.0e}: M1={pair["m1"]["M_bar"]} '
              f'TOP4={pair["topk"]["M_bar"]} '
              f'sr4={pair["topk"]["success_rate"]:.1%} '
              f'rho={pair["rho"]} p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_eps1q) ---')
    for eps1q in eps1q_values:
        pair = results[eps1q]
        s1, stk = pair['m1'], pair['topk']
        mbar1 = f"{s1['M_bar']:.2f}" if s1['M_bar'] else 'N/A'
        mbartk = f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
        rval = f"{pair['rho']:.3f}" if pair['rho'] else '---'
        print(f'  {eps1q:.0e} & {mbar1} & {mbartk} & {psucc} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# 7. Sweep optimization_level
# ─────────────────────────────────────────────
def sweep_opt_level():
    print('\n' + '='*60)
    print('SWEEP 8: Variazione di optimization_level (transpilazione)')
    print('='*60)

    opt_levels = [0, 1, 2, 3]
    nm = build_noise_model(**BASE_NOISE)
    results = {}

    for opt in opt_levels:
        transpiled = compile_shor_circuit(
            N, A, N_COUNT, optimization_level=opt
        )
        cx_count = transpiled.count_ops().get('cx', 0)
        depth    = transpiled.depth()

        m1_runs   = []
        topk_runs = []
        for rep in range(K_REPS):
            print(f'  opt_level={opt}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=(1, 4),
                compiled_circuit=transpiled,
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])

        pair = summarize_pair(m1_runs, topk_runs)
        s1, stk = pair['m1'], pair['topk']
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        r_val = pair['rho']

        results[opt] = {
            **pair,
            'cx_count': cx_count, 'depth': depth
        }
        mbar1 = f'{s1["M_bar"]:.2f}' if s1['M_bar'] is not None else 'N/A'
        mbartk = f'{stk["M_bar"]:.2f}' if stk['M_bar'] is not None else 'N/A'
        print(f'  opt={opt}  CX={cx_count}  depth={depth}  '
              f'M1={mbar1} ({s1["success_rate"]:.0%})  '
              f'TOP4={mbartk} ({stk["success_rate"]:.0%})  '
              f'rho={r_val}  p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_opt_level) ---')
    print(r'  Livello & Gate CX & Profondità & $\bar{M}_1$ & SR$_1$ & $\bar{M}_\text{TOP4}$ & SR$_4$ & $\rho$ \\')
    for opt in opt_levels:
        r = results[opt]
        s1  = r['m1']
        stk = r['topk']
        rv  = rho(stk['M_bar'], s1['M_bar']) if s1['M_bar'] else None
        mbar1  = f"{s1['M_bar']:.2f}"   if s1['M_bar']  else 'N/A'
        mbartk = f"{stk['M_bar']:.2f}"  if stk['M_bar'] else 'N/A'
        sr1    = f"{s1['success_rate']*100:.1f}\\%"
        srtk   = f"{stk['success_rate']*100:.1f}\\%"
        rval   = f"{rv:.3f}"            if rv           else '---'
        print(f'  {opt} & {r["cx_count"]} & {r["depth"]} & {mbar1} & {sr1} & {mbartk} & {srtk} & {rval} \\\\')

    return results


# ─────────────────────────────────────────────
# 8. Sweep p_ro
# ─────────────────────────────────────────────
def sweep_pro():
    print('\n' + '='*60)
    print('SWEEP 7: Variazione di p_ro (readout error)')
    print('='*60)

    pro_values = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20]
    results    = {}

    for p_ro in pro_values:
        noise = {**BASE_NOISE, 'p_ro': p_ro}
        nm    = build_noise_model(**noise)
        m1_runs, topk_runs = [], []
        for rep in range(K_REPS):
            print(f'  p_ro={p_ro:.0%}  rep {rep+1}/{K_REPS}', end='\r', flush=True)
            outcomes = run_topks(
                N, A, N_COUNT, nm, shots=DEFAULT_SHOTS,
                max_iter=MAX_ITER, seed=rep, top_ks=(1, 4),
            )
            m1_runs.append(outcomes[1])
            topk_runs.append(outcomes[4])
        pair = summarize_pair(m1_runs, topk_runs)
        results[p_ro] = pair
        p = pair['wilcoxon_M1_gt_TOPK']['p']
        print(f'  p_ro={p_ro:.0%}: M1={pair["m1"]["M_bar"]} '
              f'TOP4={pair["topk"]["M_bar"]} '
              f'sr4={pair["topk"]["success_rate"]:.1%} '
              f'rho={pair["rho"]} p={p:.4f} {sig(p)}      ')

    print('\n--- LaTeX rows (tabella sweep_pro) ---')
    for p_ro in pro_values:
        pair = results[p_ro]
        s1, stk = pair['m1'], pair['topk']
        mbar1 = f"{s1['M_bar']:.2f}" if s1['M_bar'] else 'N/A'
        mbartk = f"{stk['M_bar']:.2f}" if stk['M_bar'] else 'N/A'
        psucc = f"{stk['success_rate']*100:.1f}\\%"
        rval = f"{pair['rho']:.3f}" if pair['rho'] else '---'
        print(f'  {p_ro*100:.0f}\\% & {mbar1} & {mbartk} & {psucc} & '
              f'{rval} \\\\')

    return results


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    global K_REPS, MAX_ITER, DEFAULT_SHOTS
    parser = argparse.ArgumentParser()
    parser.add_argument('--sweep', default='all',
                        choices=['all', 'k', 'eps', 'shots', 'joint', 't1t2', 'eps1q', 'pro', 'optlevel'],
                        help='Quale sweep eseguire (default: all)')
    parser.add_argument('--k-reps', type=int, default=K_REPS)
    parser.add_argument('--max-iter', type=int, default=MAX_ITER)
    parser.add_argument('--shots', type=int, default=DEFAULT_SHOTS,
                        help='Shot per punto, eccetto lo sweep shots')
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    parser.add_argument(
        '--no-resume', action='store_true',
        help='Ignora il checkpoint delle famiglie e riesegue lo sweep richiesto da zero.',
    )
    args = parser.parse_args()
    if args.k_reps < 1 or args.max_iter < 1 or args.shots < 1:
        raise ValueError('k-reps, max-iter e shots devono essere positivi.')
    K_REPS = args.k_reps
    MAX_ITER = args.max_iter
    DEFAULT_SHOTS = args.shots

    config = {
        'K_REPS': K_REPS,
        'MAX_ITER': MAX_ITER,
        'shots': DEFAULT_SHOTS,
        'sweep': args.sweep,
        'pairing_unit': 'same histogram for TOP-1 and TOP-K per replicate/iteration',
        'inferential_scope': (
            'sweep comparisons are exploratory; raw Wilcoxon p-values are reported '
            'without a global correction across the eight sweep families'
        ),
    }
    manifest = experiment_manifest()
    checkpoint_path = (
        args.output_dir / f'parameter_analysis_checkpoint_{args.sweep}_v4.json'
    )
    all_results = None
    if not args.no_resume and checkpoint_path.is_file():
        candidate = json.loads(checkpoint_path.read_text(encoding='utf-8'))
        if (candidate.get('schema_version') != '2.0'
                or candidate.get('analysis_revision') != PARAMETER_ANALYSIS_REVISION
                or candidate.get('config') != config
                or candidate.get('manifest') != manifest):
            raise ValueError(
                f'Checkpoint incompatibile: {checkpoint_path}. Usare --no-resume.'
            )
        _restore_m1_reference(candidate.get('baseline_m1'))
        if not isinstance(candidate.get('sweeps'), dict):
            raise ValueError('Checkpoint privo dell’oggetto sweeps.')
        all_results = candidate
        print(f'Ripresa da checkpoint: {checkpoint_path}')

    if all_results is None:
        all_results = {
        'schema_version': '2.0',
        'analysis_revision': PARAMETER_ANALYSIS_REVISION,
        'timestamp': datetime.now().isoformat(),
        'config': config,
        'manifest': manifest,
        'baseline_m1': prepare_m1_reference(),
        'sweeps': {},
        }
        _atomic_json(checkpoint_path, all_results)

    sweep_map = {
        'k':        ('sweep_k',         sweep_k),
        'eps':      ('sweep_eps2q',     sweep_eps2q),
        'shots':    ('sweep_shots',     sweep_shots),
        'joint':    ('sweep_joint',     sweep_joint),
        't1t2':     ('sweep_t1t2',      sweep_t1t2),
        'eps1q':    ('sweep_eps1q',     sweep_eps1q),
        'pro':      ('sweep_pro',       sweep_pro),
        'optlevel': ('sweep_opt_level', sweep_opt_level),
    }

    to_run = list(sweep_map.keys()) if args.sweep == 'all' else [args.sweep]

    for key in to_run:
        name, fn = sweep_map[key]
        if name in all_results['sweeps']:
            print(f'Checkpoint: {name} già completo, salto.')
            continue
        all_results['sweeps'][name] = fn()
        _atomic_json(checkpoint_path, all_results)

    # Salva JSON
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fname = args.output_dir / f'results_parameter_analysis_v2_{ts}.json'
    _atomic_json(fname, all_results)
    print(f'\nRisultati salvati in: {fname}')
    print('Copia le righe LaTeX nelle tabelle di ConclusioniMetodo2.tex')


if __name__ == '__main__':
    main()
