"""M16 — enumerazione esaustiva degli errori di peso basso sul Gross code.

Decodifica TUTTI gli errori X di peso w = 0…w_max (per w_max = 5: 1 + 144 + … +
C(144,5) ≈ 5,1·10⁸ configurazioni) e conta i fallimenti logici. Se sono zero, f(w) = 0
esattamente per quei pesi: nella ricostruzione p_L(q) = Σ B(w; n, q) f(w) il contributo
degli errori piccoli non e' piu' una stima campionaria ma un fatto.

Per un codice di distanza 12 un decoder a distanza piena corregge ogni errore di peso
≤ 5; il campionamento del test 2 non aveva trovato fallimenti sotto w = 6 con il decoder
serial, ma su 2·10⁶ prove per peso. Questo script lo verifica su tutti i casi.

Nota: la simmetria per traslazione del codice non si usa, perche' la schedulazione
serial visita i qubit in un ordine fisso e il decoder non e' invariante.

Le decisioni del min-sum con priore uniforme non dipendono dal valore del priore
(vedi analisi_fallimenti.py): si usa 0,01.

Uso:
    $PY enumerazione_esaustiva.py --variante serial --w-max 5 --output-dir artifacts/v2_20260926
    $PY enumerazione_esaustiva.py --quick
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from itertools import combinations

import numpy as np

from codici_bb import costruisci
from gross_code_capacity import SCHEMA_VERSION, gf2_nullspace, manifest, verifica_css
from sweep_decoder import VARIANTI, crea_decoder

PRIORE_FISSO = 0.01
_STATO = {}


def _inizializza(nome_codice, variante):
    """Ogni processo costruisce una volta codice e decoder."""
    Hx, Hz, _, _ = costruisci(nome_codice)
    _STATO['Hz'] = Hz.astype(np.uint8)
    _STATO['K'] = gf2_nullspace(Hx).astype(np.int32)
    _STATO['dec'] = crea_decoder(Hz, PRIORE_FISSO, VARIANTI[variante])


def compito(args):
    """Tutti gli errori di peso w il cui supporto inizia con il prefisso dato."""
    w, prefisso = args
    Hz, K, dec = _STATO['Hz'], _STATO['K'], _STATO['dec']
    n = Hz.shape[1]
    Hz32 = Hz.astype(np.int32)
    resto = w - len(prefisso)
    inizio = prefisso[-1] + 1 if prefisso else 0
    contati = falliti = violate = 0
    esempi = []
    gen = combinations(range(inizio, n), resto)
    lotto = 20_000
    while True:
        code = list(next(gen, None) for _ in range(lotto))
        code = [c for c in code if c is not None]
        if not code:
            break
        m = len(code)
        err = np.zeros((m, n), dtype=np.uint8)
        if prefisso:
            err[:, list(prefisso)] = 1
        if resto:
            idx = np.array(code, dtype=np.int64).reshape(m, resto)
            np.put_along_axis(err, idx, 1, axis=1)
        synd = ((err.astype(np.int32) @ Hz32.T) % 2).astype(np.uint8)
        corr = np.array([dec.decode(s) for s in synd], dtype=np.uint8)
        res = (err ^ corr).astype(np.int32)
        violate += int(((res @ Hz32.T) % 2).any(axis=1).sum())
        fail = ((res @ K.T) % 2).any(axis=1)
        falliti += int(fail.sum())
        for r in np.nonzero(fail)[0][:max(0, 5 - len(esempi))]:
            esempi.append(np.nonzero(err[r])[0].tolist())
        contati += m
    return w, contati, falliti, violate, esempi


def compiti_per_peso(n, w):
    """Divide gli errori di peso w per prefisso dei primi due indici (w >= 3)."""
    if w <= 2:
        return [(w, ())]
    return [(w, (i, j)) for i in range(n) for j in range(i + 1, n)
            if n - j - 1 >= w - 2]


def main():
    ap = argparse.ArgumentParser(description="M16 — enumerazione esaustiva dei pesi bassi")
    ap.add_argument('--codice', default='gross_144_12_12')
    ap.add_argument('--variante', default='serial')
    ap.add_argument('--w-max', type=int, default=5)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    if args.quick:
        args.w_max = 3
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    Hx, Hz, k, d = costruisci(args.codice)
    verifica = verifica_css(Hx, Hz, k, args.codice)
    n = Hz.shape[1]
    print(f"{args.codice} con decoder {args.variante}: n={n}, d={d}, pesi 0…{args.w_max}")
    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_inizializza,
                             initargs=(args.codice, args.variante)) as pool:
        for w in range(args.w_max + 1):
            t0 = time.time()
            atteso = math.comb(n, w)
            tot = fal = vio = 0
            esempi = []
            for _, c, f, v, es in pool.map(compito, compiti_per_peso(n, w), chunksize=8):
                tot += c
                fal += f
                vio += v
                esempi.extend(es[:max(0, 5 - len(esempi))])
            if tot != atteso:
                raise RuntimeError(f"w={w}: enumerati {tot}, attesi {atteso}")
            risultati.append({'w': w, 'configurazioni': tot, 'fallimenti': fal,
                              'f_esatta': fal / tot, 'sindromi_violate': vio,
                              'esempi_di_fallimento': esempi,
                              'secondi': round(time.time() - t0, 1)})
            print(f"  w={w}: {tot:>12,} configurazioni, {fal} fallimenti"
                  + (f", {vio} sindromi violate" if vio else "")
                  + f"  ({time.time() - t0:.0f}s)", flush=True)
    corregge_tutto = all(r['fallimenti'] == 0 for r in risultati)
    print(f"\nCorregge tutti gli errori fino a peso {args.w_max}: {corregge_tutto}")
    print(f"Tempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_enumerazione_esaustiva',
        'stato': 'esplorativo',
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'codice': args.codice, 'variante': args.variante,
                      'decoder': VARIANTI[args.variante], 'w_max': args.w_max,
                      'priore_decoder': PRIORE_FISSO},
        'verifica_codice': verifica,
        'risultati': risultati,
        'esito': {'corregge_tutti_fino_a_w_max': corregge_tutto},
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_esaustivo_{args.codice}_{args.variante}_w{args.w_max}_"
                        f"{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
