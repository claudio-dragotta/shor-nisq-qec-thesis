"""
run_experiments.py — K ripetizioni di M1 e M2 su tutti i use case.
Richiede: shor_core.py + clf_UC1.joblib, clf_UC2.joblib (da train_classifier.py).

UC1/UC2 (N=15): confronto completo M1 vs M2, calcolo ρ.
UC3/UC4 (N=21/35): solo M1 + analisi circuit depth (scalabilità NISQ).
"""
import json, joblib, numpy as np
from datetime import datetime
from math import ceil, log2
from qiskit import transpile
from qiskit_aer import AerSimulator
from shor_core import build_noise_model, run_method1, run_method2, shor_circuit

NOISE_REALISTIC = {'eps_1q': 1e-3,  'eps_2q': 1e-2,
                   't1_ns': 100_000, 't2_ns':  80_000, 'p_ro': 0.02}
NOISE_DEGRADED  = {'eps_1q': 5e-3,  'eps_2q': 5e-2,
                   't1_ns':  50_000, 't2_ns':  30_000, 'p_ro': 0.05}
# Near-future NISQ (IBM roadmap 2026-2028): eps_2q=0.001, T1~500us
# Beauregard per N=21: 2594 CX, P_surv~7.5% a eps_2q=0.001
NOISE_NEARFUTURE_HARD = {'eps_1q': 1e-4,  'eps_2q': 1e-3,
                          't1_ns': 500_000, 't2_ns': 400_000, 'p_ro': 0.005}
# Near-future NISQ ottimistico: eps_2q=0.0005, P_surv~27%
NOISE_NEARFUTURE_EASY = {'eps_1q': 5e-5,  'eps_2q': 5e-4,
                          't1_ns': 800_000, 't2_ns': 600_000, 'p_ro': 0.002}

USE_CASES = [
    {'name': 'UC1', 'N': 15, 'a': 7, 'n_count': 8, 'noise': NOISE_REALISTIC,
     'has_m2': True},
    {'name': 'UC2', 'N': 15, 'a': 7, 'n_count': 8, 'noise': NOISE_DEGRADED,
     'has_m2': True},
    # UC3/UC4: N=21 con decomposizione Beauregard (O(n^3) CX)
    # eps_2q=0.001 -> P_surv~7.5% (NISQ near-future "difficile")
    {'name': 'UC3', 'N': 21, 'a': 2, 'n_count': 8, 'noise': NOISE_NEARFUTURE_HARD,
     'has_m2': True},
    # eps_2q=0.0005 -> P_surv~27% (NISQ near-future "ottimistico")
    {'name': 'UC4', 'N': 21, 'a': 2, 'n_count': 8, 'noise': NOISE_NEARFUTURE_EASY,
     'has_m2': True},
]

K_REPETITIONS = 30   # ripetizioni per stima statistica (UC1/UC2)
K_SCALABILITY = 10   # ripetizioni per analisi scalabilità (UC3/UC4)
SHOTS         = 1024
MAX_ITER      = 50


def summarize(results_list):
    iters = [r['iterations'] for r in results_list if r['success']]
    return {
        'M_bar':        float(np.mean(iters))   if iters else None,
        'std':          float(np.std(iters))    if iters else None,
        'median':       float(np.median(iters)) if iters else None,
        'success_rate': len(iters) / len(results_list),
        'n_runs':       len(results_list),
        'all_iterations': [r['iterations'] for r in results_list],
        'all_success':    [r['success']    for r in results_list],
    }


def circuit_depth_analysis(N, a, n_count):
    """Ritorna statistiche di profondità del circuito traspilato.
    Usa optimization_level=2 + NM nel costruttore per decomporre CCX→CX
    (necessario per ottenere il conteggio CX corretto per N=15).
    """
    from qiskit_aer import AerSimulator
    try:
        nm  = build_noise_model(**NOISE_REALISTIC)
        sim = AerSimulator(noise_model=nm, method='statevector')
        qc  = transpile(shor_circuit(N, a, n_count), sim, optimization_level=2)
        ops = qc.count_ops()
        cx  = ops.get('cx', 0)
        return {
            'depth':      qc.depth(),
            'total_ops':  sum(ops.values()),
            'cx_gates':   cx,
            'eps_2q':     NOISE_REALISTIC['eps_2q'],
            'p_survival': float((1 - NOISE_REALISTIC['eps_2q']) ** cx),
        }
    except Exception as e:
        return {'error': str(e)}


def run_all():
    all_results = {}

    for uc in USE_CASES:
        name   = uc['name']
        K      = K_REPETITIONS if uc['has_m2'] else K_SCALABILITY
        print(f"\n{'='*60}")
        print(f"Use Case: {name}  N={uc['N']} a={uc['a']} n_count={uc['n_count']}")
        print(f"{'='*60}")

        nm = build_noise_model(**uc['noise'])

        # Analisi profondità circuito
        print(f"  Analisi circuito per {name}...", flush=True)
        depth_info = circuit_depth_analysis(uc['N'], uc['a'], uc['n_count'])
        print(f"  depth={depth_info.get('depth','?')} "
              f"cx={depth_info.get('cx_gates','?')} "
              f"P_survival={depth_info.get('p_survival', 0):.4f}")

        # Classificatore per M2
        clf = None
        clf_meta = {}
        if uc['has_m2']:
            try:
                data = joblib.load(f"clf_{name}.joblib")
                clf  = data['clf']
                clf_meta = {'name': data['name'], 'metrics': data['metrics']}
                print(f"  Classificatore: {data['name']}")
            except FileNotFoundError:
                # Dataset training 100% positivo → classificatore banale (sempre 1)
                # M2 = TOP-K puro senza filtraggio
                class _AlwaysOne:
                    def predict(self, X): return [1] * len(X)
                clf = _AlwaysOne()
                clf_meta = {'name': 'AlwaysOne (degenerate)', 'metrics': {}}
                print(f"  Classificatore: DEGENERE (100% pos nel training set) — TOP-K puro")

        m1_results, m2_results = [], []

        for rep in range(K):
            print(f"  Rep {rep+1}/{K}", end='\r', flush=True)
            r1 = run_method1(uc['N'], uc['a'], uc['n_count'], nm,
                             shots=SHOTS, max_iter=MAX_ITER, seed=rep)
            m1_results.append(r1)

            if clf is not None:
                r2 = run_method2(uc['N'], uc['a'], uc['n_count'], nm, clf,
                                 shots=SHOTS, max_iter=MAX_ITER, seed=rep)
                m2_results.append(r2)

        print()  # newline dopo \r

        s1  = summarize(m1_results)
        s2  = summarize(m2_results) if m2_results else {}
        rho = (s1['M_bar'] / s2['M_bar']
               if s1.get('M_bar') and s2.get('M_bar') else None)

        mbar1_str = f"{s1['M_bar']:.2f} ± {s1['std']:.2f}" if s1['M_bar'] else "N/A"
        print(f"  M̅₁ = {mbar1_str}  (sr={s1['success_rate']:.1%})")
        if s2:
            mbar2_str = f"{s2['M_bar']:.2f} ± {s2['std']:.2f}" if s2.get('M_bar') else "N/A"
            print(f"  M̅₂ = {mbar2_str}  (sr={s2['success_rate']:.1%})")
            rho_str = f"{rho:.3f}" if rho else "N/A"
            print(f"  ρ  = {rho_str}")

        all_results[name] = {
            'use_case':     {k: v for k, v in uc.items() if k != 'noise'},
            'noise_params': uc['noise'],
            'circuit':      depth_info,
            'classifier':   clf_meta,
            'M1':           s1,
            'M2':           s2,
            'rho':          rho,
            'timestamp':    datetime.now().isoformat(),
        }

    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"results_full_{ts}.json"
    with open(fname, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nRisultati salvati in: {fname}")

    # Riepilogo finale
    print(f"\n{'='*60}")
    print("RIEPILOGO FINALE")
    print(f"{'='*60}")
    for name, res in all_results.items():
        m1 = res['M1']
        m2 = res['M2']
        rho = res['rho']
        m1_str  = f"{m1['M_bar']:.2f}" if m1.get('M_bar') else "N/A"
        m2_str  = f"{m2['M_bar']:.2f}" if m2.get('M_bar') else "N/A"
        rho_str = f"{rho:.3f}" if rho else "N/A"
        print(f"  {name}: M̅₁={m1_str} M̅₂={m2_str} ρ={rho_str} "
              f"sr1={m1['success_rate']:.1%}")

    return all_results


if __name__ == '__main__':
    run_all()
