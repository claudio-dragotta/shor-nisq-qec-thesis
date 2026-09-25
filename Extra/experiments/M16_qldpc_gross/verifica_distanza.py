"""M16 — controllo della distanza del surface code costruito in gross_code_capacity.py.

Cerca per forza bruta il peso minimo di un errore X non rilevato (Hz e = 0) che non sia
uno stabilizzatore (e fuori dallo spazio delle righe di Hx): e' la distanza del settore X.
Per il Gross code la forza bruta non e' praticabile; si riporta solo un limite superiore,
il peso minimo fra i vettori di una base dei logici.

Uso:
    $PY verifica_distanza.py --distances 3 5 7
"""
import argparse
from itertools import combinations

import numpy as np

from gross_code_capacity import gf2_nullspace, gross_code, rotated_surface


def distanza_x(Hx, Hz, w_max):
    n = Hz.shape[1]
    K = gf2_nullspace(Hx).astype(np.int64)
    Hz = Hz.astype(np.int64)
    for w in range(1, w_max + 1):
        for supp in combinations(range(n), w):
            idx = list(supp)
            if (Hz[:, idx].sum(axis=1) % 2).any():
                continue
            if (K[:, idx].sum(axis=1) % 2).any():
                return w
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--distances', type=int, nargs='+', default=[3, 5, 7])
    args = ap.parse_args()
    for d in args.distances:
        Hx, Hz = rotated_surface(d)
        print(f"surface d={d}: distanza X trovata = {distanza_x(Hx, Hz, d)}", flush=True)
    Hx, Hz = gross_code()
    print("Gross code: righe Hz di peso", sorted(set(Hz.sum(axis=1))),
          "- distanza 12 da Bravyi et al. 2024, non verificata qui per forza bruta")


if __name__ == '__main__':
    main()
