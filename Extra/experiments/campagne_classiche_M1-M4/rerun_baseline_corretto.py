"""
rerun_baseline_corretto.py — riesecuzione della campagna base con SEEDING CORRETTO.

MOTIVO. Aer deriva il seme di ogni shot da (seed_simulator + indice_shot). Con 1024 shot,
lo schema originario (seed*10_000 + iterazione) faceva condividere alle iterazioni
consecutive 1023 campioni su 1024: le iterazioni di una ripetizione non erano indipendenti.
Una ripetizione la cui prima moda non produceva i fattori esauriva tutte le 50 iterazioni,
gonfiando M_bar e deprimendo il tasso di successo. Lo schema e' ora
seed*1_000_000 + iterazione*10_000 (cfr. il commento in shor_core.py).

DIFFERENZA RISPETTO A run_top4_baseline.py: si eseguono i soli UC1 e UC2. Gli UC3/UC4 di quel
file usano N=21, che a livello di rumore utile costa ~50 s per shot (misura riportata nel
Cap. 10): non sono eseguibili e facevano stallare la campagna.

Uso: ~/quantum-env/bin/python rerun_baseline_corretto.py
"""
import json
from datetime import datetime

import numpy as np
from scipy.stats import mannwhitneyu

from run_top4_baseline import (NOISE_REALISTIC, NOISE_DEGRADED, K, SHOTS, MAX_ITER, run_uc)


def statistiche(nome, m1, mt4, m2):
    def ok(a):
        return a[a < MAX_ITER]

    r = {'use_case': nome, 'K': int(K), 'shots': int(SHOTS), 'max_iter': int(MAX_ITER)}
    for et, arr in (('M1', m1), ('M_TOP4', mt4), ('M2', m2)):
        if arr is None:
            continue
        o = ok(arr)
        r[et] = {'n_succ': int(len(o)), 'P_succ': float(len(o) / K),
                 'M_bar': float(o.mean()) if len(o) else None,
                 'sigma': float(o.std(ddof=0)) if len(o) else None,
                 'mediana': float(np.median(o)) if len(o) else None}
    m1o, mt4o = ok(m1), ok(mt4)
    r['rho_TOP4'] = float(m1o.mean() / mt4o.mean()) if len(m1o) and len(mt4o) else None
    u1, p1 = mannwhitneyu(m1, mt4, alternative='greater')
    r['mwu_M1_gt_TOP4'] = {'U': float(u1), 'p': float(p1)}
    if m2 is not None:
        m2o = ok(m2)
        r['rho_M2'] = float(m1o.mean() / m2o.mean()) if len(m2o) and len(m1o) else None
        u2, p2 = mannwhitneyu(mt4, m2, alternative='greater')
        u3, p3 = mannwhitneyu(m1, m2, alternative='greater')
        r['mwu_TOP4_gt_M2'] = {'U': float(u2), 'p': float(p2)}
        r['mwu_M1_gt_M2'] = {'U': float(u3), 'p': float(p3)}
    return r


def stampa(r):
    print(f"\n{'='*66}\n  {r['use_case']}\n{'='*66}")
    for et in ('M1', 'M_TOP4', 'M2'):
        if et not in r:
            continue
        v = r[et]
        print(f"  {et:<8} successo {v['n_succ']}/{r['K']} = {v['P_succ']:.1%}"
              f" | M_bar {v['M_bar']:.2f} | sigma {v['sigma']:.2f}"
              f" | mediana {v['mediana']:.1f}")
    print(f"  rho(M1/M_TOP4) = {r['rho_TOP4']:.3f}"
          f"   [Mann-Whitney p={r['mwu_M1_gt_TOP4']['p']:.4f}]")
    if 'rho_M2' in r:
        print(f"  rho(M1/M2)     = {r['rho_M2']:.3f}"
              f"   [p={r['mwu_M1_gt_M2']['p']:.4f}]")
        print(f"  ABLAZIONE M_TOP4 vs M2: p={r['mwu_TOP4_gt_M2']['p']:.4f}")


def main():
    print('=' * 66)
    print('  CAMPAGNA BASE RIESEGUITA — seeding corretto')
    print(f'  K={K} ripetizioni, {SHOTS} shot, max {MAX_ITER} iterazioni')
    print('=' * 66)

    out = []
    for nome, noise in (('UC1', NOISE_REALISTIC), ('UC2', NOISE_DEGRADED)):
        m1, mt4, m2 = run_uc(nome, 15, 7, 8, noise, with_m2=True)
        r = statistiche(nome, m1, mt4, m2)
        r['_iterazioni'] = {'M1': m1.tolist(), 'M_TOP4': mt4.tolist(),
                            'M2': m2.tolist() if m2 is not None else None}
        stampa(r)
        out.append(r)

    fn = f"results_baseline_corretto_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump({'nota': 'seeding corretto: seed*1e6 + iterazione*1e4',
               'timestamp': datetime.now().isoformat(), 'use_case': out},
              open(fn, 'w'), indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
