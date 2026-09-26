"""M16 / test 3 — ricerca di operatori logici di peso basso (limite superiore alla distanza).

Metodo a insieme d'informazione casuale (information set): i vettori di ker(Hz) formano
un codice classico con matrice generatrice G. A ogni iterazione si permutano a caso le
colonne, si porta G in forma sistematica e si esaminano le righe e le somme di coppie di
righe (variante semplificata dell'algoritmo di Stern). Un vettore e' un operatore logico X
non banale se sta in ker(Hz) ma non nello spazio delle righe di Hx; il suo peso e' un
limite superiore alla distanza del settore X. Lo stesso con Hx e Hz scambiati per il
settore Z.

Trovare un logico del peso pubblicato conferma la costruzione; trovarne uno PIU' LEGGERO
indicherebbe un errore nei polinomi o nel codice. Il metodo non dimostra che logici piu'
leggeri non esistano: per questo servirebbe una ricerca esaustiva, qui non praticabile.

Controllo del metodo: sul surface code la distanza e' nota (e verificata per forza bruta
fino a d = 7 in verifica_distanza.py) e deve essere ritrovata.

Uso:
    $PY cerca_distanza.py --seed 42 --output-dir artifacts/v2_20260926
    $PY cerca_distanza.py --quick
"""
import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

from codici_bb import CODICI_BB, costruisci
from gross_code_capacity import (SCHEMA_VERSION, gf2_nullspace, gf2_rref, manifest,
                                 verifica_css)


def iterazioni(task):
    """Esegue un gruppo di iterazioni; restituisce il peso minimo e un logico di quel peso."""
    G, K, n_iter, seed_words = task
    rng = np.random.default_rng(np.random.SeedSequence(seed_words))
    n = G.shape[1]
    K32 = K.astype(np.int32)
    migliore, vettore, pesi_visti = n + 1, None, {}
    for _ in range(n_iter):
        perm = rng.permutation(n)
        R, _ = gf2_rref(G[:, perm])
        cand = [R]
        if R.shape[0] > 1:
            i, j = np.triu_indices(R.shape[0], 1)
            cand.append(R[i] ^ R[j])
        C = np.vstack(cand)
        pesi = C.sum(axis=1)
        # un vettore di ker(Hz) e' un logico non banale se non e' ortogonale a ker(Hx);
        # C e' nelle coordinate permutate, quindi anche K va permutato
        logici = ((C.astype(np.int32) @ K32[:, perm].T) % 2).any(axis=1)
        if not logici.any():
            continue
        pl = pesi[logici]
        for w in np.unique(pl):
            pesi_visti[int(w)] = pesi_visti.get(int(w), 0) + int((pl == w).sum())
        k = int(np.argmin(np.where(logici, pesi, n + 1)))
        if pesi[k] < migliore:
            migliore = int(pesi[k])
            inv = np.empty(n, dtype=np.int64)
            inv[perm] = np.arange(n)
            vettore = C[k][inv]              # riporta alle coordinate originali
    return migliore, (np.nonzero(vettore)[0].tolist() if vettore is not None else None), \
        pesi_visti


def cerca(pool, Hx, Hz, n_iter, workers, seed_words_base):
    """Settore X: logici in ker(Hz) fuori da rowspace(Hx)."""
    G = gf2_nullspace(Hz)
    K = gf2_nullspace(Hx)
    per = max(1, n_iter // workers)
    tasks = [(G, K, per, seed_words_base + [i]) for i in range(workers)]
    migliore, supporto, pesi = G.shape[1] + 1, None, {}
    for m, s, pv in pool.map(iterazioni, tasks):
        if m < migliore:
            migliore, supporto = m, s
        for w, c in pv.items():
            pesi[w] = pesi.get(w, 0) + c
    return migliore, supporto, dict(sorted(pesi.items())), per * workers


def verifica_logico(Hx, Hz, supporto):
    """Controllo indipendente del logico trovato."""
    v = np.zeros(Hz.shape[1], dtype=np.int64)
    v[supporto] = 1
    in_kernel = not ((Hz.astype(np.int64) @ v) % 2).any()
    K = gf2_nullspace(Hx).astype(np.int64)
    non_banale = bool(((K @ v) % 2).any())
    return in_kernel and non_banale


def main():
    ap = argparse.ArgumentParser(description="M16 test 3 — ricerca di logici di peso basso")
    ap.add_argument('--codici', nargs='+',
                    default=['surface_d5', 'surface_d7', 'surface_d9'] + list(CODICI_BB))
    ap.add_argument('--iterazioni', type=int, default=40_000,
                    help="iterazioni per codice e per settore")
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--output-dir', default=None)
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    if args.quick:
        args.codici, args.iterazioni = ['surface_d5', 'gross_144_12_12'], 200
    elif not args.output_dir:
        ap.error("--output-dir e' obbligatorio fuori da --quick")

    risultati = []
    t_tot = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i_c, nome in enumerate(args.codici):
            Hx, Hz, k_atteso, d_attesa = costruisci(nome)
            verifica = verifica_css(Hx, Hz, k_atteso, nome)
            voce = {'codice': nome, 'n': int(Hz.shape[1]), 'k': k_atteso,
                    'distanza_attesa': d_attesa, 'verifica': verifica, 'settori': {}}
            t0 = time.time()
            for i_s, (settore, A, B) in enumerate((('X', Hx, Hz), ('Z', Hz, Hx))):
                m, supp, pesi, fatte = cerca(pool, A, B, args.iterazioni, args.workers,
                                             [args.seed, 4000 + i_c, i_s])
                ok = verifica_logico(A, B, supp) if supp else False
                voce['settori'][settore] = {
                    'peso_minimo_trovato': m, 'supporto': supp,
                    'logico_verificato': ok, 'iterazioni': fatte,
                    'pesi_logici_visti': {str(w): c for w, c in pesi.items()
                                          if w <= d_attesa + 6},
                }
            wx = voce['settori']['X']['peso_minimo_trovato']
            wz = voce['settori']['Z']['peso_minimo_trovato']
            limite = min(wx, wz)
            voce['limite_superiore_distanza'] = limite
            voce['esito'] = ('coincide con la distanza attesa' if limite == d_attesa else
                             'PIU LEGGERO del previsto: controllare la costruzione'
                             if limite < d_attesa else
                             'nessun logico del peso atteso trovato: aumentare le iterazioni')
            voce['secondi'] = round(time.time() - t0, 1)
            risultati.append(voce)
            ver = all(s['logico_verificato'] for s in voce['settori'].values())
            voce['tutti_i_logici_verificati'] = ver
            print(f"{nome:<18} n={voce['n']:<4} d attesa {d_attesa:<3} trovati X={wx} Z={wz}"
                  f"  verificati={ver}  -> {voce['esito']}  ({voce['secondi']}s)", flush=True)
    print(f"Tempo totale: {time.time() - t_tot:.0f}s")

    if args.quick:
        print("--quick: nessun file salvato.")
        return
    out = {
        'schema_version': SCHEMA_VERSION,
        'milestone': 'M16_test3_ricerca_distanza',
        'stato': 'esplorativo',
        'metodo': ("information set casuale su ker(Hz) con righe e somme di coppie di righe; "
                   "ogni vettore trovato e' verificato come logico non banale"),
        'limite_metodo': "fornisce limiti superiori, non dimostra la distanza",
        'experiment_manifest': manifest(args, __file__),
        'parametri': {'codici': args.codici, 'iterazioni': args.iterazioni,
                      'workers': args.workers,
                      'seed_words': "[seed, 4000 + indice codice, settore, worker]"},
        'risultati': risultati,
    }
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir,
                        f"results_M16_test3_distanza_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"Salvato: {path}")


if __name__ == '__main__':
    main()
