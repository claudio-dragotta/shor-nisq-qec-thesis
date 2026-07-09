"""
gen_qec_steane.py — figura M6: curva p vs p_L del codice di Steane [[7,1,3]].
Legge il JSON prodotto da experiments/qec_steane.py (--mode curve) e produce
qec_steane_curve.pdf/png in file_latex/figure/ (log-log: dati pendenza ~2 vs
bisettrice p_L=p; la loro intersezione è la pseudo-soglia).

Uso: python gen_qec_steane.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments', 'M6_steane_code')


def _latest_curve():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M6_steane_*.json')))
    for f in reversed(files):                       # il più recente CON chiave 'curve'
        with open(f) as fh:
            d = json.load(fh)
        if 'curve' in d:
            return d
    raise FileNotFoundError("Nessun JSON M6 con 'curve'. Esegui: python qec_steane.py --mode curve")


def main():
    data = _latest_curve()
    pts = data['curve']['points']
    p = np.array([d['p'] for d in pts])
    pL = np.array([d['p_L'] for d in pts])
    se = np.array([d['p_L_se'] for d in pts])

    # riferimento pendenza 2 calibrato sul punto più piccolo: p_L = A p^2
    A = pL[0] / p[0]**2
    pp = np.logspace(np.log10(p.min() * 0.8), np.log10(p.max() * 1.1), 200)

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.plot(pp, pp, ls=':', color='0.55', lw=1.2,
            label=r'$p_L = p$ (qubit fisico non protetto)')
    ax.plot(pp, A * pp**2, color='C1', lw=1.6, ls='--',
            label=r'riferimento $\propto p^2$ (distanza $d=3$)')
    ax.errorbar(p, pL, yerr=se, fmt='o', color='C0', ms=5, capsize=3,
                label='Steane (Monte Carlo Pauli-frame)')

    # pseudo-soglia: intersezione dati con la bisettrice (interpolazione in log)
    below = pL < p
    if below.any() and (~below).any():
        i = np.where(np.diff(below.astype(int)) != 0)[0][0]
        x0, x1 = np.log10(p[i]), np.log10(p[i + 1])
        y0 = np.log10(pL[i] / p[i]); y1 = np.log10(pL[i + 1] / p[i + 1])
        pth = 10 ** (x0 - y0 * (x1 - x0) / (y1 - y0))
        ax.axvline(pth, color='0.8', lw=0.8)
        ax.annotate(f'pseudo-soglia\n$p\\approx{pth:.2f}$', xy=(pth, pth),
                    xytext=(pth * 1.05, pth * 0.25), fontsize=8, color='0.4')

    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(r'errore fisico per qubit $p$')
    ax.set_ylabel(r'errore logico $p_L$')
    ax.set_title('Codice di Steane $[[7,1,3]]$: soppressione dell\'errore ($d=3$)')
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(alpha=0.3, which='both')
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_steane_curve')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png  (pseudo-soglia log-log, A={A:.1f})")


if __name__ == '__main__':
    main()
