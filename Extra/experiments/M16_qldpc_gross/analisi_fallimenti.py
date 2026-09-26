"""M16 / test 2 — perche' a basso rumore il Gross code scende lentamente?

Campionamento a peso fissato: per ogni w si generano errori X con esattamente w qubit
colpiti, scelti uniformemente, e si misura f(w) = P(fallimento logico | peso w).

Proprieta' usata: con priore uniforme il min-sum e' invariante per riscalamento dei
rapporti di verosimiglianza, e l'OSD ordina le colonne con le stesse informazioni; anche
MWPM con pesi uniformi non dipende da q. Le decisioni del decoder dipendono quindi solo
dall'errore, non da q, e vale esattamente

    p_L(q) = sum_w  C(n, w) q^w (1 - q)^(n - w)  f(w).

La curva ricostruita si confronta con le simulazioni dirette: e' il controllo interno.

Si registra anche il peso minimo dei residui che causano fallimento: un residuo e' un
operatore logico non banale, quindi il suo peso e' un limite superiore alla distanza.

Uso:
    $PY analisi_fallimenti.py --seed 42 --output-dir artifacts/v2_20260926 \
        --diretti-json <file JSON delle corse dirette, espliciti>
    $PY analisi_fallimenti.py --quick
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np
import pymatching

from codici_bb import costruisci
from gross_code_capacity import SCHEMA_VERSION, gf2_nullspace, manifest, verifica_css, wilson
from sweep_decoder import RIFERIMENTO, VARIANTI, crea_decoder

PRIORE_FISSO = 0.01     # irrilevante per le decisioni (vedi docstring), serve solo a ldpc
Q_RICOSTRUZIONE = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06]


def blocco(task):
    Hz, K, w, shots, seed_words, decoder = task
    rng = np.random.default_rng(np.random.SeedSequence(seed_words))
    n = Hz.shape[1]
    err = np.zeros((shots, n), dtype=np.uint8)
    if w > 0:
        idx = np.argpartition(rng.random((shots, n)), w - 1, axis=1)[:, :w]
        np.put_along_axis(err, idx, 1, axis=1)
    Hz32, K32 = Hz.astype(np.int32), K.astype(np.int32)
    synd = ((err.astype(np.int32) @ Hz32.T) % 2).astype(np.uint8)
    if decoder == 'mwpm':
        m = pymatching.Matching.from_check_matrix(Hz, weights=np.ones(n))
        corr = m.decode_batch(synd).astype(np.uint8)
    else:
        dec = crea_decoder(Hz, PRIORE_FISSO, VARIANTI[decoder])
        corr = np.array([dec.decode(s) for s in synd], dtype=np.uint8)
    res = (err ^ corr).astype(np.int32)
    violate = int(((res @ Hz32.T) % 2).any(axis=1).sum())
    fail = ((res @ K32.T) % 2).any(axis=1)
    pesi_res = res[fail].sum(axis=1)
    return (int(fail.sum()), violate,
            int(pesi_res.min()) if pesi_res.size else None,
            np.bincount(pesi_res, minlength=n + 1).tolist() if pesi_res.size else None)


def log_binom_pmf(n, w, q):
    return (math.lgamma(n + 1) - math.lgamma(w + 1) - math.lgamma(n - w + 1)
            + w * math.log(q) + (n - w) * math.log1p(-q))


def ricostruisci(n, f_per_w, q):
    """p_L(q) con f(w) stimata; fuori dai pesi campionati: 0 (limite inferiore) o 1
    (limite superiore). Restituisce stima, e limiti da IC di f e dalla coda."""
    stima = basso = alto = 0.0
    for w in range(n + 1):
        b = math.exp(log_binom_pmf(n, w, q))
        if w in f_per_w:
            f, lo, hi = f_per_w[w]
            stima += b * f
            basso += b * lo
            alto += b * hi
        else:
            alto += b
    return stima, basso, alto


def main():
    ap = argparse.ArgumentParser(description="M16 test 2 — fallimenti a peso fissato")
    ap.add_argument('--codici', nargs='+',
                    default=['gross_144_12_12:' + RIFERIMENTO, 'surface_d9:mwpm',
                             'surface_d11:mwpm'],
                    help="voci codice:decoder; decoder = mwpm o una variante di sweep_decoder")
    ap.add_argument('--w-max', type=int, default=30)
    ap.add_argument('--shots-max', type=int, default=2_000_000)
    ap.add_argument('--min-failures', type=int, default=300)
    ap.add_argument('--chunk', type=int, default=10_000)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--diretti-json', nargs='*', default=[],
                    help="corse dirette da confrontare con la ricostruzione (espliciti)")
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    if args.quick:
        args.codici = ['gross_144_12_12:' + RIFERIMENTO, 'surface_d5:mwpm']
        args.w_max, args.shots_max, args.min_failures, args.chunk = 12, 2000, 50, 500
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    diretti = {}
    for p in args.diretti_json:
        d = json.load(open(p, encoding='utf-8'))
        for r in d['risultati']:
            chiave = ('gross_144_12_12' if r['nome'] == 'gross_bposd' else r['codice'],
                      r['decoder'], d['parametri']['bposd']['bp_method'],
                      d['parametri'].get('ms_scaling_factor'))
            for pt in r['punti']:
                vecchio = diretti.get(chiave + (pt['q'],))
                if vecchio is None or pt['fallimenti'] > vecchio['fallimenti']:
                    diretti[chiave + (pt['q'],)] = pt

    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i_c, voce in enumerate(args.codici):
            nome, decoder = voce.split(':')
            Hx, Hz, k_atteso, d_attesa = costruisci(nome)
            verifica = verifica_css(Hx, Hz, k_atteso, nome)
            K = gf2_nullspace(Hx)
            n = Hz.shape[1]
            print(f"\n{nome} ({decoder}), n={n}, distanza attesa {d_attesa}", flush=True)
            per_w, f_per_w, min_res = [], {}, None
            for w in range(0, min(args.w_max, n) + 1):
                shots = fall = viol = 0
                b = 0
                hist = np.zeros(n + 1, dtype=np.int64)
                min_w = None
                while shots < args.shots_max and fall < args.min_failures:
                    tasks = []
                    for _ in range(args.workers):
                        s = min(args.chunk, args.shots_max - shots - sum(t[3] for t in tasks))
                        if s <= 0:
                            break
                        tasks.append((Hz, K, w, s, [args.seed, 3000 + i_c, w, b], decoder))
                        b += 1
                    for f, v, mr, h in pool.map(blocco, tasks):
                        fall += f
                        viol += v
                        if mr is not None:
                            min_w = mr if min_w is None else min(min_w, mr)
                            hist += np.array(h, dtype=np.int64)
                    shots += sum(t[3] for t in tasks)
                lo, hi = wilson(fall, shots)
                f = fall / shots
                f_per_w[w] = (f, lo, hi)
                if min_w is not None:
                    min_res = min_w if min_res is None else min(min_res, min_w)
                per_w.append({'w': w, 'shots': shots, 'fallimenti': fall, 'f': f,
                              'ic95_wilson': [lo, hi], 'sindromi_violate': viol,
                              'peso_min_residuo': min_w,
                              'istogramma_pesi_residuo': {str(i): int(c) for i, c in
                                                          enumerate(hist) if c}})
                print(f"  w={w:<3} f={f:.3e} ({fall}/{shots})"
                      + (f"  residuo min {min_w}" if min_w is not None else "")
                      + (f"  VIOLATE={viol}" if viol else ""), flush=True)
                # oltre il punto in cui quasi tutto fallisce non serve continuare
                if f > 0.999 and w > d_attesa:
                    break

            ricostruzione = []
            for q in Q_RICOSTRUZIONE:
                st, lo, hi = ricostruisci(n, f_per_w, q)
                riga = {'q': q, 'p_L_ricostruita': st, 'limiti': [lo, hi]}
                bp = VARIANTI[decoder] if decoder != 'mwpm' else None
                chiave = (nome, 'bposd' if bp else 'mwpm',
                          bp['bp_method'] if bp else None,
                          bp.get('ms_scaling_factor') if bp else None, q)
                if not bp:
                    # per MWPM nelle corse dirette il bp_method registrato e' quello del
                    # file; si cerca per codice, decoder e q ignorando i campi di BP
                    cand = [v for kk, v in diretti.items()
                            if kk[0] == nome and kk[1] == 'mwpm' and kk[4] == q]
                    dir_pt = max(cand, key=lambda p: p['fallimenti']) if cand else None
                else:
                    # le corse dirette di gross_code_capacity usano sempre la
                    # schedulazione parallela: per altre schedulazioni non c'e' confronto
                    dir_pt = (diretti.get(chiave) if bp.get('schedule', 'parallel') ==
                              'parallel' else None)
                if dir_pt:
                    riga['diretta'] = {'p_L': dir_pt['p_fallimento'],
                                       'ic95': dir_pt['ic95_wilson'],
                                       'fallimenti': dir_pt['fallimenti']}
                ricostruzione.append(riga)
                print(f"  ricostruita q={q}: {st:.3e} [{lo:.2e}, {hi:.2e}]"
                      + (f"   diretta {dir_pt['p_fallimento']:.3e}" if dir_pt else ""))
            primo = next((r['w'] for r in per_w if r['fallimenti'] > 0), None)
            risultati.append({'codice': nome, 'decoder': decoder, 'n': n,
                              'distanza_attesa': d_attesa, 'verifica': verifica,
                              'peso_minimo_con_fallimenti': primo,
                              'peso_min_residuo_logico': min_res,
                              'per_peso': per_w, 'ricostruzione': ricostruzione})
            print(f"  primo peso con fallimenti: {primo};  residuo logico piu' leggero: "
                  f"{min_res} (limite superiore alla distanza)")
    print(f"\nTempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_test2_fallimenti_peso_fissato',
        'stato': 'esplorativo',
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'codici': args.codici, 'w_max': args.w_max,
                      'shots_max': args.shots_max, 'min_failures': args.min_failures,
                      'chunk': args.chunk, 'priore_decoder': PRIORE_FISSO,
                      'diretti_json': [os.path.basename(p) for p in args.diretti_json],
                      'seed_words': "[seed, 3000 + indice codice, w, blocco]"},
        'risultati': risultati,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_test2_fallimenti_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
