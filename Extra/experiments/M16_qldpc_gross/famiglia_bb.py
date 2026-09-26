"""M16 / test 4 — il vantaggio del Gross code vale per tutta la famiglia bivariate bicycle?

Simula in code-capacity i codici BB della tabella di Bravyi et al. (2024) con il decoder
di riferimento (min-sum 0,625) e, per ciascuno, confronta il blocco da k qubit logici con
k patch di surface code indipendenti, usando i dati del surface passati esplicitamente
(corse MWPM gia' salvate).

Il Gross code e' incluso con semi nuovi: fa da replica indipendente delle corse
precedenti.

Uso:
    $PY famiglia_bb.py --seed 42 --output-dir artifacts/v2_20260926 \
        --surface-json <file MWPM espliciti>
    $PY famiglia_bb.py --quick
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

from analisi_consolidata import migliori_punti
from codici_bb import CODICI_BB, costruisci
from gross_code_capacity import (SCHEMA_VERSION, gf2_nullspace, manifest,
                                 pendenza_loglog, verifica_css, wilson)
from sweep_decoder import RIFERIMENTO, VARIANTI, blocco

Q_FAMIGLIA = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08]


def esegui_punto_variante(pool, Hz, K, q, variante, args, idx_cfg, idx_q):
    """Come esegui_punto di gross_code_capacity, ma con qualsiasi variante di
    sweep_decoder (anche schedulazione serial o BP+LSD)."""
    shots = fall = viol = b = 0
    t0 = time.time()
    while shots < args.shots_max and fall < args.min_failures:
        tasks = []
        for _ in range(args.workers):
            s = min(args.chunk, args.shots_max - shots - sum(t[3] for t in tasks))
            if s <= 0:
                break
            tasks.append((Hz, K, q, s, [args.seed, idx_cfg, idx_q, b], [variante]))
            b += 1
        for n_s, esiti, violate, _ in pool.map(blocco, tasks):
            fall += int(np.unpackbits(esiti[variante])[:n_s].sum())
            viol += violate[variante]
        shots += sum(t[3] for t in tasks)
    lo, hi = wilson(fall, shots)
    return {'q': q, 'shots': shots, 'fallimenti': fall,
            'p_fallimento': fall / shots if shots else float('nan'),
            'ic95_wilson': [lo, hi], 'sindromi_violate': viol,
            'secondi': round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser(description="M16 test 4 — famiglia bivariate bicycle")
    ap.add_argument('--codici', nargs='+', default=list(CODICI_BB))
    ap.add_argument('--q-list', type=float, nargs='+', default=Q_FAMIGLIA)
    ap.add_argument('--shots-max', type=int, default=10_000_000)
    ap.add_argument('--min-failures', type=int, default=300)
    ap.add_argument('--chunk', type=int, default=10_000)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--variante', default=RIFERIMENTO,
                    help="decoder del Gross e della famiglia (nome in sweep_decoder)")
    ap.add_argument('--surface-json', nargs='*', default=[])
    ap.add_argument('--indice-base', type=int, default=5000,
                    help="indice di configurazione dei semi; cambiarlo da' campioni nuovi")
    ap.add_argument('--etichetta', default='', help="suffisso del file di output")
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    if args.quick:
        args.codici, args.q_list = ['bb_72_12_6', 'bb_90_8_10'], [0.02, 0.05]
        args.shots_max, args.min_failures, args.chunk = 4000, 10**9, 500
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    spec = VARIANTI[args.variante]

    surface = {}
    if args.surface_json:
        sorgenti = [(p, json.load(open(p, encoding='utf-8'))) for p in args.surface_json]
        distanze = sorted({r['d'] for _, d in sorgenti for r in d['risultati']
                           if r.get('decoder') == 'mwpm'})
        surface = {d: migliori_punti(sorgenti, lambda r, d=d: r.get('d') == d and
                                     r['decoder'] == 'mwpm') for d in distanze}

    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i_c, nome in enumerate(args.codici):
            Hx, Hz, k, d_pub = costruisci(nome)
            verifica = verifica_css(Hx, Hz, k, nome)
            K = gf2_nullspace(Hx)
            n = Hz.shape[1]
            print(f"\n{nome}: n={n} k={k} d pubblicata={d_pub}  rank Hx={verifica['rank_Hx']}",
                  flush=True)
            punti = []
            for i_q, q in enumerate(args.q_list):
                pt = esegui_punto_variante(pool, Hz, K, q, args.variante, args,
                                           args.indice_base + i_c, i_q)
                # confronto con k patch di surface (IC 95% non sovrapposti)
                eq = {'peggiori': [], 'migliori': []}
                for d, pts in surface.items():
                    if q not in pts:
                        continue
                    ps = pts[q][0]
                    blocco = lambda p: 1 - (1 - p) ** k
                    if ps['fallimenti'] == 0:
                        lo_s, hi_s = 0.0, blocco(3.0 / ps['shots'])
                    else:
                        lo_s, hi_s = (blocco(ps['ic95_wilson'][0]),
                                      blocco(ps['ic95_wilson'][1]))
                    lo_g, hi_g = pt['ic95_wilson']
                    if hi_s < lo_g:
                        eq['migliori'].append(d)
                    elif lo_s > hi_g:
                        eq['peggiori'].append(d)
                pt['surface_k_patch'] = eq
                punti.append(pt)
                print(f"  q={q:<6} P_blocco={pt['p_fallimento']:.3e} "
                      f"({pt['fallimenti']}/{pt['shots']})  surface peggiori {eq['peggiori']}"
                      f" / migliori {eq['migliori']}"
                      + (f"  VIOLATE={pt['sindromi_violate']}" if pt['sindromi_violate']
                         else ""), flush=True)
            risultati.append({'codice': nome, 'n': n, 'k': k, 'distanza_pubblicata': d_pub,
                              'rapporto_k_su_n': k / n, 'verifica': verifica,
                              'punti': punti, 'fit_loglog': pendenza_loglog(punti)})
    print(f"\nTempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_test4_famiglia_bb',
        'stato': 'esplorativo',
        'modello_rumore': "code-capacity, errori X indipendenti, sindromi perfette",
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'codici': {c: CODICI_BB[c] for c in args.codici},
                      'q_list': args.q_list, 'shots_max': args.shots_max,
                      'min_failures': args.min_failures, 'chunk': args.chunk,
                      'decoder': {args.variante: spec},
                      'surface_json': [os.path.basename(p) for p in args.surface_json],
                      'seed_words': f"[seed, {args.indice_base} + indice codice, "
                                    f"indice q, blocco]",
                      'regola_confronto': ("k patch indipendenti, 1-(1-p_L)^k; migliore o "
                                           "peggiore solo con IC 95% non sovrapposti; "
                                           "0 fallimenti -> limite 3/N")},
        'risultati': risultati,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_test4_famiglia_bb{'_' + args.etichetta if args.etichetta else ''}"
                        f"_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
