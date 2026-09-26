"""M16 / test 1 — quanto resta da guadagnare con il decoder sul Gross code?

Tutte le varianti decodificano GLI STESSI shot: il confronto con il riferimento e'
appaiato e si valuta con il test di McNemar sulle coppie discordanti. I semi sono
[seed, 0, indice di q in Q_LIST, blocco], come nelle corse precedenti del Gross code:
con --chunk 10000 i campioni coincidono con la corsa minsum_basso_rumore a q = 0,5–2%,
che fa quindi da controllo incrociato del riferimento.

Criterio fissato prima della corsa (REGISTRO_M16, sez. 10): il decoder e' considerato
saturo se nessuna variante migliora il riferimento di piu' del 10% con p di McNemar
< 0,01 a nessun q. Altrimenti la variante migliore diventa il nuovo riferimento.

Uso:
    $PY sweep_decoder.py --seed 42 --output-dir artifacts/v2_20260926
    $PY sweep_decoder.py --quick
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np
from ldpc import BpLsdDecoder, BpOsdDecoder

from gross_code_capacity import (Q_LIST, SCHEMA_VERSION, gf2_nullspace, gross_code,
                                 manifest, verifica_css, wilson)

RIFERIMENTO = 'rif_minsum0625_osd10'
_BASE = dict(tipo='bposd', bp_method='minimum_sum', ms_scaling_factor=0.625,
             max_iter=100, schedule='parallel', osd_method='osd_cs', osd_order=10)


def _v(**modifiche):
    d = dict(_BASE)
    d.update(modifiche)
    return d


VARIANTI = {
    RIFERIMENTO: _v(),
    'minsum0500': _v(ms_scaling_factor=0.5),
    'minsum0750': _v(ms_scaling_factor=0.75),
    'minsum0875': _v(ms_scaling_factor=0.875),
    'minsum1000': _v(ms_scaling_factor=1.0),
    'osd_cs30': _v(osd_order=30),
    'osd_cs60': _v(osd_order=60),
    'osd_e7': _v(osd_method='osd_e', osd_order=7),
    'iter1000': _v(max_iter=1000),
    'serial': _v(schedule='serial'),
    'lsd_cs10': dict(tipo='bplsd', bp_method='minimum_sum', ms_scaling_factor=0.625,
                     max_iter=100, schedule='parallel', lsd_method='LSD_CS', lsd_order=10),
    'product_sum_osd10': _v(bp_method='product_sum', ms_scaling_factor=None),
    # --- giro 1b: attorno ai vincitori del primo sweep (serial e fattore 0,5) ---
    'minsum0400': _v(ms_scaling_factor=0.4),
    'minsum0450': _v(ms_scaling_factor=0.45),
    'minsum0550': _v(ms_scaling_factor=0.55),
    'minsum0500_osd60': _v(ms_scaling_factor=0.5, osd_order=60),
    'serial_minsum0500': _v(schedule='serial', ms_scaling_factor=0.5),
    'serial_minsum0875': _v(schedule='serial', ms_scaling_factor=0.875),
    'serial_osd60': _v(schedule='serial', osd_order=60),
    'serial_minsum0500_osd60': _v(schedule='serial', ms_scaling_factor=0.5, osd_order=60),
    'serial_iter1000': _v(schedule='serial', max_iter=1000),
}

# Varianti del giro 1b, confrontate con il vincitore del primo giro.
GIRO_1B = ['serial', 'minsum0500', 'minsum0400', 'minsum0450', 'minsum0550',
           'minsum0500_osd60', 'osd_cs60', 'serial_minsum0500', 'serial_minsum0875',
           'serial_osd60', 'serial_minsum0500_osd60', 'serial_iter1000']

SHOTS_PER_Q = {0.005: 4_000_000, 0.01: 2_000_000, 0.02: 1_000_000, 0.03: 400_000,
               0.04: 200_000}


def crea_decoder(Hz, q, spec):
    comuni = dict(error_rate=float(q), max_iter=spec['max_iter'],
                  bp_method=spec['bp_method'], schedule=spec['schedule'])
    if spec.get('ms_scaling_factor') is not None:
        comuni['ms_scaling_factor'] = spec['ms_scaling_factor']
    if spec['tipo'] == 'bplsd':
        return BpLsdDecoder(Hz, lsd_method=spec['lsd_method'],
                            lsd_order=spec['lsd_order'], **comuni)
    return BpOsdDecoder(Hz, osd_method=spec['osd_method'], osd_order=spec['osd_order'],
                        **comuni)


def blocco(task):
    """Campiona un blocco di shot e lo decodifica con TUTTE le varianti."""
    Hz, K, q, shots, seed_words, nomi = task
    rng = np.random.default_rng(np.random.SeedSequence(seed_words))
    n = Hz.shape[1]
    err = (rng.random((shots, n)) < q).astype(np.uint8)
    Hz32, K32 = Hz.astype(np.int32), K.astype(np.int32)
    synd = ((err.astype(np.int32) @ Hz32.T) % 2).astype(np.uint8)
    esiti, violate, secondi = {}, {}, {}
    for nome in nomi:
        t0 = time.time()
        dec = crea_decoder(Hz, q, VARIANTI[nome])
        corr = np.array([dec.decode(s) for s in synd], dtype=np.uint8)
        res = (err ^ corr).astype(np.int32)
        violate[nome] = int(((res @ Hz32.T) % 2).any(axis=1).sum())
        esiti[nome] = np.packbits(((res @ K32.T) % 2).any(axis=1))
        secondi[nome] = time.time() - t0
    return shots, esiti, violate, secondi


def mcnemar(b, c):
    """p a due code, con correzione di continuita' (come in M10/E7)."""
    if b + c == 0:
        return 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    return math.erfc(math.sqrt(chi2 / 2)) if chi2 > 0 else 1.0


def main():
    ap = argparse.ArgumentParser(description="M16 test 1 — sweep del decoder sul Gross code")
    ap.add_argument('--q-list', type=float, nargs='+', default=list(SHOTS_PER_Q))
    ap.add_argument('--riferimento', default=RIFERIMENTO,
                    help="variante con cui si confrontano le altre")
    ap.add_argument('--giro-1b', action='store_true',
                    help="varianti del giro 1b attorno ai vincitori del primo sweep")
    ap.add_argument('--etichetta', default='', help="suffisso del file di output")
    ap.add_argument('--shots-scala', type=float, default=1.0,
                    help="moltiplica gli shot per q di SHOTS_PER_Q")
    ap.add_argument('--varianti', nargs='+', default=list(VARIANTI))
    ap.add_argument('--chunk', type=int, default=10_000)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--soglia-miglioramento', type=float, default=0.10)
    ap.add_argument('--alpha', type=float, default=0.01)
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    if args.giro_1b:
        args.varianti = list(GIRO_1B)
    if args.riferimento not in args.varianti:
        args.varianti = [args.riferimento] + args.varianti
    if args.quick:
        args.q_list, args.shots_scala, args.chunk = [0.02], 0.002, 500
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    Hx, Hz = gross_code()
    verifica = verifica_css(Hx, Hz, 12, 'Gross code')
    K = gf2_nullspace(Hx)

    print("=" * 96)
    print(f"M16 test 1 — sweep del decoder, {len(args.varianti)} varianti, stessi shot")
    print("=" * 96)
    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for q in args.q_list:
            idx_q = Q_LIST.index(q)          # stesso flusso di campioni delle corse base
            totale = max(args.chunk, int(SHOTS_PER_Q.get(q, 1_000_000) * args.shots_scala))
            tasks, fatti, b = [], 0, 0
            while fatti < totale:
                s = min(args.chunk, totale - fatti)
                tasks.append((Hz, K, q, s, [args.seed, 0, idx_q, b], args.varianti))
                fatti += s
                b += 1
            fail = {v: [] for v in args.varianti}
            viol = {v: 0 for v in args.varianti}
            sec = {v: 0.0 for v in args.varianti}
            for shots, esiti, violate, secondi in pool.map(blocco, tasks):
                for v in args.varianti:
                    fail[v].append(np.unpackbits(esiti[v])[:shots].astype(bool))
                    viol[v] += violate[v]
                    sec[v] += secondi[v]
            fail = {v: np.concatenate(fail[v]) for v in args.varianti}
            rif = fail[args.riferimento]
            n_shots = rif.size
            print(f"\nq = {q}   shots = {n_shots}")
            for v in args.varianti:
                f = fail[v]
                k = int(f.sum())
                bb = int((f & ~rif).sum())      # la variante sbaglia dove il rif azzecca
                cc = int((rif & ~f).sum())      # la variante azzecca dove il rif sbaglia
                p_rif = rif.mean()
                var = (f.mean() - p_rif) / p_rif if p_rif > 0 else float('nan')
                pm = mcnemar(bb, cc)
                risultati.append({
                    'q': q, 'variante': v, 'spec': VARIANTI[v], 'shots': n_shots,
                    'fallimenti': k, 'p_fallimento': k / n_shots,
                    'ic95_wilson': list(wilson(k, n_shots)),
                    'variazione_rel_vs_rif': var,
                    'mcnemar': {'b_variante_peggiora': bb, 'c_variante_migliora': cc,
                                'p_value': pm},
                    'sindromi_violate': viol[v],
                    'secondi_cpu_decodifica': round(sec[v], 1),
                })
                print(f"  {v:<22} p_L={k / n_shots:.3e} ({k:>6})  var={var:+7.1%}  "
                      f"b={bb:<5} c={cc:<5} p={pm:.1e}  cpu={sec[v]:.0f}s"
                      + (f"  VIOLATE={viol[v]}" if viol[v] else ""), flush=True)

    migliori = [r for r in risultati if r['variante'] != args.riferimento
                and r['variazione_rel_vs_rif'] < -args.soglia_miglioramento
                and r['mcnemar']['p_value'] < args.alpha]
    saturo = not migliori
    print(f"\nDecoder saturo (nessun miglioramento >{args.soglia_miglioramento:.0%} "
          f"con p<{args.alpha}): {saturo}")
    for r in migliori:
        print(f"  migliora: {r['variante']} a q={r['q']} ({r['variazione_rel_vs_rif']:+.1%}, "
              f"p={r['mcnemar']['p_value']:.1e})")
    print(f"Tempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_test1_sweep_decoder',
        'stato': 'esplorativo',
        'modello_rumore': "code-capacity, errori X indipendenti, sindromi perfette",
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'q_list': args.q_list, 'shots_per_q': {str(q): int(SHOTS_PER_Q.get(
            q, 1_000_000) * args.shots_scala) for q in args.q_list},
            'riferimento': args.riferimento, 'varianti': {v: VARIANTI[v] for v in args.varianti},
            'criterio': {'soglia_miglioramento': args.soglia_miglioramento,
                         'alpha': args.alpha},
            'seed_words': "[seed, 0, indice di q in Q_LIST, blocco]"},
        'verifica_codice': verifica,
        'risultati': risultati,
        'esito': {'decoder_saturo': saturo,
                  'varianti_migliori': [{k: r[k] for k in ('q', 'variante',
                                         'variazione_rel_vs_rif')} for r in migliori]},
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_test1_sweep_decoder{'_' + args.etichetta if args.etichetta else ''}"
                        f"_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
