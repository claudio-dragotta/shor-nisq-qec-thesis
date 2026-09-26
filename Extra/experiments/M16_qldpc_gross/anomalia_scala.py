"""M16 / test 3 (secondo elenco) — perche' il fattore di scala del min-sum parallelo
agisce in modo erratico sul Gross code?

Nel test 1 il min-sum con schedulazione parallela era ottimo con fattore 0,5 e 0,875,
pessimo con 0,55, 0,625 e 0,75; con la schedulazione serial il comportamento era stabile.
Due meccanismi possibili, distinguibili con gli attributi che ldpc espone dopo ogni
decodifica (converge, iter, bp_decoding, osd0_decoding, osdw_decoding):

  M1  BP converge a una soluzione SBAGLIATA che soddisfa la sindrome: l'OSD non viene
      chiamato e l'errore logico passa;
  M2  BP non converge (oscilla) e l'OSD, alimentato da informazione soft degradata,
      sceglie male.

Per ogni variante e ogni fallimento si registra quale dei due casi e' avvenuto, oltre
al tasso di non convergenza e alle iterazioni medie. Tutte le varianti decodificano gli
stessi shot. Criteri in REGISTRO_M16, sez. 16.

Uso:
    $PY anomalia_scala.py --seed 42 --output-dir artifacts/v2_20260926
    $PY anomalia_scala.py --quick
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

from gross_code_capacity import (Q_LIST, SCHEMA_VERSION, gf2_nullspace, gross_code,
                                 manifest, verifica_css, wilson)
from sweep_decoder import _v, crea_decoder


def griglia_varianti():
    var = {}
    for f in np.round(np.arange(0.40, 1.0001, 0.025), 3):
        var[f"parallel_ms{f:.3f}"] = _v(ms_scaling_factor=float(f))
    for f in np.round(np.arange(0.40, 1.0001, 0.1), 3):
        var[f"serial_ms{f:.3f}"] = _v(schedule='serial', ms_scaling_factor=float(f))
    var["serial_ms0.625"] = _v(schedule='serial')          # il decoder definitivo
    for it in (10, 30, 300, 1000):
        var[f"parallel_ms0.625_iter{it}"] = _v(max_iter=it)
    return var


VARIANTI = griglia_varianti()


def blocco(task):
    Hz, K, q, shots, seed_words, nomi = task
    rng = np.random.default_rng(np.random.SeedSequence(seed_words))
    n = Hz.shape[1]
    err = (rng.random((shots, n)) < q).astype(np.uint8)
    Hz32, K32 = Hz.astype(np.int32), K.astype(np.int32)
    synd = ((err.astype(np.int32) @ Hz32.T) % 2).astype(np.uint8)
    out = {}
    for nome in nomi:
        dec = crea_decoder(Hz, q, VARIANTI[nome])
        c = dict(fail=0, fail_bp_converge=0, fail_osd=0, non_converge=0, iter_tot=0,
                 osd0_avrebbe_fallito=0, osd0_avrebbe_salvato=0)
        for i in range(shots):
            corr = dec.decode(synd[i])
            conv = bool(dec.converge)
            c['iter_tot'] += int(dec.iter)
            if not conv:
                c['non_converge'] += 1
            res = (err[i] ^ corr).astype(np.int32)
            fail = bool(((K32 @ res) % 2).any())
            if not conv:
                # la decisione OSD di ordine 0 avrebbe fatto meglio o peggio di OSD-CS?
                r0 = (err[i] ^ np.asarray(dec.osd0_decoding, dtype=np.uint8)).astype(np.int32)
                f0 = bool(((K32 @ r0) % 2).any())
                c['osd0_avrebbe_fallito'] += int(f0)
                c['osd0_avrebbe_salvato'] += int(fail and not f0)
            if fail:
                c['fail'] += 1
                c['fail_bp_converge' if conv else 'fail_osd'] += 1
        out[nome] = c
    return shots, out


def main():
    ap = argparse.ArgumentParser(description="M16 — anomalia del fattore di scala")
    ap.add_argument('--q-list', type=float, nargs='+', default=[0.02, 0.03])
    ap.add_argument('--shots', type=int, default=500_000)
    ap.add_argument('--chunk', type=int, default=5_000)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    nomi = list(VARIANTI)
    if args.quick:
        args.q_list, args.shots, args.chunk = [0.03], 2000, 500
        nomi = ['parallel_ms0.500', 'parallel_ms0.625', 'serial_ms0.600']
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    Hx, Hz = gross_code()
    verifica = verifica_css(Hx, Hz, 12, 'Gross code')
    K = gf2_nullspace(Hx)
    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for q in args.q_list:
            idx_q = Q_LIST.index(q)
            tasks, fatti, b = [], 0, 0
            while fatti < args.shots:
                s = min(args.chunk, args.shots - fatti)
                # seme diverso dai test precedenti: 6000 come indice di configurazione
                tasks.append((Hz, K, q, s, [args.seed, 6000, idx_q, b], nomi))
                fatti += s
                b += 1
            tot = {v: dict(fail=0, fail_bp_converge=0, fail_osd=0, non_converge=0,
                           iter_tot=0, osd0_avrebbe_fallito=0, osd0_avrebbe_salvato=0)
                   for v in nomi}
            n_shots = 0
            for s, out in pool.map(blocco, tasks):
                n_shots += s
                for v in nomi:
                    for k2, val in out[v].items():
                        tot[v][k2] += val
            print(f"\nq = {q}   shots = {n_shots}")
            print(f"  {'variante':<26}{'p_L':>11}{'fall.':>7}{'BP conv.':>9}{'OSD':>7}"
                  f"{'non conv.':>11}{'iter med.':>10}")
            for v in nomi:
                c = tot[v]
                p = c['fail'] / n_shots
                quota_conv = c['fail_bp_converge'] / c['fail'] if c['fail'] else float('nan')
                risultati.append({
                    'q': q, 'variante': v, 'spec': VARIANTI[v], 'shots': n_shots,
                    'fallimenti': c['fail'], 'p_fallimento': p,
                    'ic95_wilson': list(wilson(c['fail'], n_shots)),
                    'fallimenti_bp_converge': c['fail_bp_converge'],
                    'fallimenti_osd': c['fail_osd'],
                    'quota_fallimenti_bp_converge': quota_conv,
                    'tasso_non_convergenza': c['non_converge'] / n_shots,
                    'iterazioni_medie': c['iter_tot'] / n_shots,
                    'osd0_avrebbe_fallito': c['osd0_avrebbe_fallito'],
                    'osd0_avrebbe_salvato': c['osd0_avrebbe_salvato'],
                })
                print(f"  {v:<26}{p:>11.2e}{c['fail']:>7}{c['fail_bp_converge']:>9}"
                      f"{c['fail_osd']:>7}{c['non_converge'] / n_shots:>11.2%}"
                      f"{c['iter_tot'] / n_shots:>10.1f}", flush=True)
    print(f"\nTempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_anomalia_fattore_scala',
        'stato': 'esplorativo',
        'meccanismi': {
            'M1': "BP converge a una soluzione sbagliata; l'OSD non interviene",
            'M2': "BP non converge; l'OSD sceglie male con informazione soft degradata",
        },
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'q_list': args.q_list, 'shots': args.shots, 'chunk': args.chunk,
                      'varianti': {v: VARIANTI[v] for v in nomi},
                      'seed_words': "[seed, 6000, indice di q in Q_LIST, blocco]"},
        'verifica_codice': verifica,
        'risultati': risultati,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_anomalia_scala_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
