"""
rerun_baseline_corretto.py — riesecuzione della campagna base con SEEDING CORRETTO.

MOTIVO. Aer deriva il seme di ogni shot da (seed_simulator + indice_shot). Con 1024 shot,
lo schema originario (seed*10_000 + iterazione) faceva condividere alle iterazioni
consecutive 1023 campioni su 1024: le iterazioni di una ripetizione non erano indipendenti.
Una ripetizione la cui prima moda non produceva i fattori esauriva tutte le 50 iterazioni,
gonfiando M_bar e deprimendo il tasso di successo. Lo schema e' ora
seed*1_000_000 + iterazione*10_000 (cfr. il commento in shor_core.py).

PERIMETRO: si eseguono i soli UC1 e UC2. L'aritmetica N=21/35 e' validata
separatamente; N=21 con n_count=8 compila in 21.036 CX nella base rz/sx/x/cx
ed e' quindi escluso da questa campagna rumorosa per costo computazionale.

Uso: ~/quantum-env/bin/python rerun_baseline_corretto.py
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from run_top4_baseline import (
    NOISE_REALISTIC,
    NOISE_DEGRADED,
    K,
    SHOTS,
    MAX_ITER,
    paired_greater,
    paired_wilcoxon,
    run_uc,
)
from shor_core import experiment_manifest


def wilson95(successes, total):
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [float(max(0, center - half)), float(min(1, center + half))]


def _holm_adjust(tests):
    """Aggiunge p_holm con controllo FWER ai confronti della stessa baseline."""
    ordered = sorted(tests, key=lambda item: item[1]['p'])
    running = 0.0
    total = len(ordered)
    for index, (_, test) in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * float(test['p'])))
        test['p_holm'] = running


def statistiche(nome, m1, mt4, m2, *, k=K, shots=SHOTS, max_iter=MAX_ITER):
    def ok(a):
        return a[a <= max_iter]

    r = {'use_case': nome, 'K': int(k), 'shots': int(shots),
         'max_iter': int(max_iter), 'failure_sentinel': int(max_iter + 1)}
    for et, arr in (('M1', m1), ('M_TOP4', mt4), ('M2', m2)):
        if arr is None:
            continue
        o = ok(arr)
        r[et] = {'n_succ': int(len(o)), 'P_succ': float(len(o) / k),
                 'P_succ_wilson95': wilson95(len(o), k),
                 'M_bar': float(o.mean()) if len(o) else None,
                 'sigma': float(o.std(ddof=0)) if len(o) else None,
                 'mediana': float(np.median(o)) if len(o) else None,
                 'mean_budget_used': float(np.minimum(arr, max_iter).mean()),
                 'median_budget_used': float(np.median(np.minimum(arr, max_iter)))}
    m1o, mt4o = ok(m1), ok(mt4)
    r['rho_TOP4'] = float(m1o.mean() / mt4o.mean()) if len(m1o) and len(mt4o) else None
    w1, p1 = paired_greater(m1, mt4)
    r['wilcoxon_M1_gt_TOP4'] = {
        'W': float(w1), 'p': float(p1), 'alternative': 'greater'
    }
    tests = [('wilcoxon_M1_gt_TOP4', r['wilcoxon_M1_gt_TOP4'])]
    if m2 is not None:
        m2o = ok(m2)
        r['rho_M2'] = float(m1o.mean() / m2o.mean()) if len(m2o) and len(m1o) else None
        w2, p2 = paired_wilcoxon(mt4, m2, alternative='two-sided')
        w3, p3 = paired_greater(m1, m2)
        r['wilcoxon_M2_vs_TOP4'] = {
            'W': float(w2), 'p': float(p2), 'alternative': 'two-sided'
        }
        r['wilcoxon_M1_gt_M2'] = {'W': float(w3), 'p': float(p3)}
        r['wilcoxon_M1_gt_M2']['alternative'] = 'greater'
        tests.extend([
            ('wilcoxon_M2_vs_TOP4', r['wilcoxon_M2_vs_TOP4']),
            ('wilcoxon_M1_gt_M2', r['wilcoxon_M1_gt_M2']),
        ])
    _holm_adjust(tests)
    r['multiplicity'] = {
        'method': 'Holm', 'family': [name for name, _ in tests],
        'alpha': 0.05,
    }
    return r


def stampa(r):
    print(f"\n{'='*66}\n  {r['use_case']}\n{'='*66}")
    for et in ('M1', 'M_TOP4', 'M2'):
        if et not in r:
            continue
        v = r[et]
        mean = f"{v['M_bar']:.2f}" if v['M_bar'] is not None else 'N/A'
        sigma = f"{v['sigma']:.2f}" if v['sigma'] is not None else 'N/A'
        median = f"{v['mediana']:.1f}" if v['mediana'] is not None else 'N/A'
        print(f"  {et:<8} successo {v['n_succ']}/{r['K']} = {v['P_succ']:.1%}"
              f" | M_bar(succ) {mean} | budget medio {v['mean_budget_used']:.2f}"
              f" | sigma {sigma} | mediana {median}")
    rho_top4 = f"{r['rho_TOP4']:.3f}" if r['rho_TOP4'] is not None else 'N/A'
    print(f"  rho(M1/M_TOP4) = {rho_top4}"
          f"   [Wilcoxon p_Holm={r['wilcoxon_M1_gt_TOP4']['p_holm']:.4f}]")
    if 'rho_M2' in r:
        rho_m2 = f"{r['rho_M2']:.3f}" if r['rho_M2'] is not None else 'N/A'
        print(f"  rho(M1/M2)     = {rho_m2}"
              f"   [p_Holm={r['wilcoxon_M1_gt_M2']['p_holm']:.4f}]")
        print(f"  ABLAZIONE M_TOP4 vs M2: "
              f"p_Holm={r['wilcoxon_M2_vs_TOP4']['p_holm']:.4f} (bilaterale)")


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--k', type=int, default=K)
    parser.add_argument('--shots', type=int, default=SHOTS)
    parser.add_argument('--max-iter', type=int, default=MAX_ITER)
    parser.add_argument('--model-dir', type=Path, default=Path('.'))
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    return parser.parse_args()


def main():
    args = _parse_args()
    if args.k < 1 or args.shots < 1 or args.max_iter < 1:
        raise ValueError('k, shots e max-iter devono essere positivi.')
    print('=' * 66)
    print('  CAMPAGNA BASE RIESEGUITA — seeding corretto')
    print(f'  K={args.k} ripetizioni, {args.shots} shot, '
          f'max {args.max_iter} iterazioni')
    print('=' * 66)

    out = []
    for nome, noise in (('UC1', NOISE_REALISTIC), ('UC2', NOISE_DEGRADED)):
        m1, mt4, m2 = run_uc(
            nome, 15, 7, 8, noise, with_m2=True,
            k=args.k, shots=args.shots, max_iter=args.max_iter,
            model_dir=args.model_dir,
        )
        r = statistiche(
            nome, m1, mt4, m2,
            k=args.k, shots=args.shots, max_iter=args.max_iter,
        )
        r['_iterazioni'] = {'M1': m1.tolist(), 'M_TOP4': mt4.tolist(),
                            'M2': m2.tolist() if m2 is not None else None}
        stampa(r)
        out.append(r)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fn = args.output_dir / f"results_baseline_v2_{datetime.now():%Y%m%d_%H%M%S}.json"
    payload = {
        'schema_version': '2.0',
        'analysis_revision': 'baseline-shared-hist-ties-holm-v3',
        'nota': ('circuito ×7 corretto; modello uniforme RZ-virtuale; '
                 'seeding seed*1e6 + iterazione*1e4; strategie sullo stesso '
                 'istogramma; tie-break SHA-256 seeded; Holm per famiglia UC'),
        'timestamp': datetime.now().isoformat(),
        'manifest': experiment_manifest(),
        'use_case': out,
    }
    with fn.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
