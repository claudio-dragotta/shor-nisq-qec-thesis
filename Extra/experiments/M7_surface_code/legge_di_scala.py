"""Legge di scala p_L(d, p) del surface code, e distanza richiesta da Shor logico.

Con tre sole distanze si poteva constatare la soppressione; con quattro si puo'
stimarne la forma funzionale. Sotto soglia la teoria prevede

    p_L(d, p) ~ A * (p / p_th)^((d+1)/2)

cioe' l'errore logico decade esponenzialmente in d, con esponente pari al numero di
errori necessari a produrre un errore logico non rilevabile, floor((d+1)/2). Questo
script stima A e p_th dai dati di M7 e ne ricava la risposta alla domanda operativa
del Capitolo 13: *quale distanza serve perche' Shor logico raggiunga un dato p_L*.

Uso:
    python legge_di_scala.py results_M7_surface_z_<timestamp>.json
"""
import glob
import json
import sys

import numpy as np


def carica(percorso):
    d = json.load(open(percorso))
    c = d['curve']
    dist = sorted(int(k) for k in c['table'])
    punti = {}
    for k in c['table']:
        for r in c['table'][k]:
            if r['p_L'] > 0:                       # gli zeri non sono utilizzabili in log
                punti.setdefault(int(k), []).append((r['p'], r['p_L'], r.get('shots')))
    return c['basis'], dist, punti


def stima_esponente(punti, dist, p_max=0.006):
    """Esponente empirico di soppressione: pendenza di ln p_L rispetto a d, a p fisso.

    La teoria prevede pendenza ln(p/p_th)/2 per unita' di d, cioe' un fattore costante
    di soppressione per ogni incremento di 2 nella distanza. Si riporta il fattore
    misurato fra distanze consecutive.
    """
    print('  Fattore di soppressione per incremento di distanza (sotto soglia):')
    p_comuni = sorted({p for d in dist for p, _, _ in punti.get(d, []) if p <= p_max})
    for p in p_comuni:
        val = []
        for d in dist:
            v = [pl for pp, pl, _ in punti.get(d, []) if pp == p]
            val.append((d, v[0]) if v else (d, None))
        fattori = []
        for (d1, v1), (d2, v2) in zip(val, val[1:]):
            fattori.append(f'{d1}->{d2}: {v1 / v2:5.1f}x' if v1 and v2 else f'{d1}->{d2}:   n/d')
        serie = '  '.join(f'{v:.2e}' if v else '  n/d' for _, v in val)
        print(f'    p={p:<7g} p_L = {serie}   |  ' + '  '.join(fattori))


def adatta_modello(punti, dist):
    """Adatta ln p_L = ln A + ((d+1)/2) * ln(p / p_th) ai punti sotto soglia."""
    # Forma lineare nelle incognite (ln A, ln p_th):
    #     ln p_L - k ln p = ln A - k ln p_th ,   con k = (d+1)/2
    A_mat, b = [], []
    for d in dist:
        for p, pl, _ in punti.get(d, []):
            if p <= 0.006:
                k = (d + 1) / 2
                A_mat.append([1.0, -k])
                b.append(np.log(pl) - k * np.log(p))
    A_mat, b = np.array(A_mat), np.array(b)
    sol, *_ = np.linalg.lstsq(A_mat, b, rcond=None)
    lnA, ln_pth = sol
    A, p_th = np.exp(lnA), np.exp(ln_pth)
    resid = b - A_mat @ sol
    print(f'\n  Modello  p_L = A (p/p_th)^((d+1)/2)   adattato sui punti con p <= 0.006:')
    print(f'    A     = {A:.3g}')
    print(f'    p_th  = {p_th:.4f}  ({100 * p_th:.2f}%)')
    print(f'    residuo RMS in ln p_L = {np.sqrt((resid ** 2).mean()):.3f}')
    return A, p_th


def distanza_richiesta(A, p_th, p_fisico, obiettivi=(1e-4, 1e-6, 1e-9, 1e-12)):
    """Distanza minima (dispari) per raggiungere p_L obiettivo a errore fisico dato."""
    print(f'\n  Distanza richiesta a p = {p_fisico:g}:')
    if p_fisico >= p_th:
        print(f'    p e\' SOPRA soglia ({100 * p_th:.2f}%): aumentare d peggiora. Nessuna d utile.')
        return
    for obiettivo in obiettivi:
        # A (p/p_th)^((d+1)/2) = obiettivo  =>  d = 2 ln(obiettivo/A)/ln(p/p_th) - 1
        d = 2 * np.log(obiettivo / A) / np.log(p_fisico / p_th) - 1
        d_int = max(int(np.ceil(d)), 3)
        if d_int % 2 == 0:
            d_int += 1
        # surface code ruotato: d^2 qubit di dato + (d^2 - 1) di misura
        print(f'    p_L <= {obiettivo:.0e}  ->  d = {d_int:2d}  '
              f'({2 * d_int ** 2 - 1:5d} qubit fisici per qubit logico)')


if __name__ == '__main__':
    percorsi = sys.argv[1:] or sorted(glob.glob('results_M7_surface_*_*.json'))[-2:]
    for percorso in percorsi:
        basis, dist, punti = carica(percorso)
        print(f'\n=== {percorso}  (base {basis.upper()}, distanze {dist}) ===')
        stima_esponente(punti, dist)
        A, p_th = adatta_modello(punti, dist)
        for p_fis in (2e-3, 1e-3, 5e-4):
            distanza_richiesta(A, p_th, p_fis)
