"""
generalizzazione.py — M14: il decoder appreso e' trasferibile, o va riaddestrato per ogni
dispositivo?

PERCHE' CONTA. La Sez. 12.7 mostra che il decoder ibrido riduce l'errore logico in presenza
di rumore correlato. Ma addestra e valuta sullo STESSO profilo di rumore. Se il modello
funzionasse solo li', andrebbe riaddestrato per ogni esemplare di QPU e a ogni deriva di
calibrazione --- il che ne limiterebbe drasticamente l'utilita' pratica. La domanda e' quindi:

    la rete ha imparato una REGOLA o le idiosincrasie di un profilo di rumore?

DISEGNO. Si addestra su un'intensita' di crosstalk e si valuta su un'altra, senza alcun
riaddestramento, confrontando con:
  - il MWPM (che non si addestra: e' il riferimento invariante)
  - la rete addestrata SULLO STESSO profilo di test (limite superiore: oracolo di dominio)

La differenza fra rete trasferita e rete "in casa" misura il costo del trasferimento; quella
fra rete trasferita e MWPM dice se il trasferimento conservi comunque un vantaggio.

Uso: ~/quantum-env/bin/python generalizzazione.py [--shots 400000]
"""
import argparse
import json
import math
from datetime import datetime

import numpy as np

from qec_neural_decoder import (build_circuit, with_crosstalk, sample, matcher,
                                mwpm_predict, train_nn, binom_se, P_PHYS)

FRAC_TRAIN = 0.75


def dati(d, p_ct, shots, seed):
    """Campiona un profilo di rumore e restituisce sindromi, verita' e predizione MWPM."""
    nom = build_circuit(d, P_PHYS)
    det, y = sample(with_crosstalk(nom, p_ct), shots, seed)
    pred = mwpm_predict(matcher(nom), det)
    return det, y, pred


def ibrido(nnh, det, pred, y, thr=0.5):
    X = np.concatenate([det, pred[:, None]], axis=1).astype(np.float32)
    flip = nnh.predict_proba(X)[:, 1] >= thr
    return float(((pred ^ flip) != y).mean())


def main():
    ap = argparse.ArgumentParser(description='M14 — generalizzazione del decoder')
    ap.add_argument('--shots', type=int, default=400_000)
    ap.add_argument('--d', type=int, default=3)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--profili', type=float, nargs='+', default=[0.005, 0.01, 0.02, 0.04])
    args = ap.parse_args()

    print('=' * 78)
    print('M14 — il decoder appreso e\' trasferibile fra profili di rumore?')
    print(f"    surface code d={args.d}, p fisico {P_PHYS}, {args.shots} shot per profilo")
    print('=' * 78)

    # --- un dataset per profilo, e una rete addestrata su ciascuno ---
    dset, reti = {}, {}
    for i, pc in enumerate(args.profili):
        det, y, pred = dati(args.d, pc, args.shots, args.seed + i)
        n_tr = int(args.shots * FRAC_TRAIN)
        dset[pc] = {'det': det, 'y': y, 'pred': pred, 'n_tr': n_tr}
        X = np.concatenate([det[:n_tr], pred[:n_tr, None]], axis=1)
        reti[pc] = train_nn(X, (pred[:n_tr] != y[:n_tr]).astype(np.uint8), args.seed + i)
        print(f"  profilo p_ct={pc:<6g} addestrato "
              f"(MWPM p_L = {float((pred[n_tr:] != y[n_tr:]).mean()):.5f})", flush=True)

    # --- matrice di trasferimento ---
    print('\n  p_L dell\'ibrido: righe = profilo di ADDESTRAMENTO, colonne = profilo di TEST')
    intest = '  addestr.\\test  ' + ''.join(f"{pc:<12g}" for pc in args.profili) + 'MWPM'
    print(intest)
    print('  ' + '-' * (len(intest) - 2))

    M = np.zeros((len(args.profili), len(args.profili)))
    for i, pa in enumerate(args.profili):
        riga = f"  {pa:<15g}"
        for j, pt in enumerate(args.profili):
            D = dset[pt]
            sl = slice(D['n_tr'], None)
            M[i, j] = ibrido(reti[pa], D['det'][sl], D['pred'][sl], D['y'][sl])
            riga += f"{M[i, j]:<12.5f}"
        print(riga, flush=True)
    riga = '  MWPM (nessun addestr.)'
    base = []
    for pt in args.profili:
        D = dset[pt]; sl = slice(D['n_tr'], None)
        b = float((D['pred'][sl] != D['y'][sl]).mean())
        base.append(b)
    print('  ' + 'MWPM'.ljust(15) + ''.join(f"{b:<12.5f}" for b in base))

    # --- sintesi ---
    print('\n' + '=' * 78)
    print('ESITO M14')
    print('=' * 78)
    n_tot = n_meglio = 0
    perdite = []
    for j, pt in enumerate(args.profili):
        in_casa = M[j, j]
        fuori = [M[i, j] for i in range(len(args.profili)) if i != j]
        for i, v in enumerate(fuori):
            n_tot += 1
            if v < base[j]:
                n_meglio += 1
        perdite.append((np.mean(fuori) - in_casa) / in_casa if in_casa > 0 else np.nan)
        print(f"  test p_ct={pt:<7g} MWPM {base[j]:.5f} | rete in casa {in_casa:.5f} | "
              f"rete trasferita (media) {np.mean(fuori):.5f}")
    print(f"\n  reti trasferite che battono comunque MWPM: {n_meglio}/{n_tot}")
    print(f"  costo medio del trasferimento (peggioramento vs rete in casa): "
          f"{np.nanmean(perdite)*100:+.1f}%")

    if n_meglio >= 0.75 * n_tot:
        flag = ("VERDE — il vantaggio sopravvive al trasferimento: la rete ha imparato una "
                "regola, non un profilo")
    elif n_meglio >= 0.4 * n_tot:
        flag = "GIALLO — il trasferimento conserva il vantaggio solo in parte"
    else:
        flag = ("ROSSO — il vantaggio non sopravvive al trasferimento: serve riaddestrare "
                "per ogni profilo")
    print(f"\n  FLAG: {flag}")

    fn = f"results_M14_generalizzazione_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump({'milestone': 'M14_generalizzazione', 'timestamp': datetime.now().isoformat(),
               'd': args.d, 'p_phys': P_PHYS, 'shots': args.shots, 'profili': args.profili,
               'matrice_trasferimento': M.tolist(), 'mwpm': base,
               'n_trasferite_meglio_di_mwpm': int(n_meglio), 'n_totali': int(n_tot),
               'costo_medio_trasferimento': float(np.nanmean(perdite)), 'flag': flag},
              open(fn, 'w'), indent=2)
    print(f"\nRisultati salvati in: {fn}")


if __name__ == '__main__':
    main()
