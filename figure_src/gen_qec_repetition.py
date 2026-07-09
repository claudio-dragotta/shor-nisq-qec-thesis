"""
gen_qec_repetition.py — figura M5: curva p vs p_L del codice a ripetizione.
Legge i JSON prodotti da experiments/qec_repetition.py (--mode curve) per bit-flip (Z)
e phase-flip (X) e produce qec_repetition_curve.pdf/png.

Regola del documento di indirizzo: le figure si rigenerano da script, non a mano.

Uso:
    python gen_qec_repetition.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments')


def _latest(basis):
    pattern = os.path.join(EXP_DIR, f'results_M5_repetition_{basis}_*.json')
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"Nessun JSON per basis {basis}. Esegui prima:\n"
            f"  python qec_repetition.py --mode curve --basis {basis}")
    with open(files[-1]) as f:
        return json.load(f)


def main():
    data_z = _latest('Z')
    pts_z = data_z['curve']['points']
    p = np.array([d['p'] for d in pts_z])
    pL_z = np.array([d['p_L'] for d in pts_z])
    se_z = np.array([d['p_L_se'] for d in pts_z])

    # phase-flip: opzionale (stessa curva per dualità); se assente si usa solo Z
    try:
        pts_x = _latest('X')['curve']['points']
        pL_x = np.array([d['p_L'] for d in pts_x])
        se_x = np.array([d['p_L_se'] for d in pts_x])
        have_x = True
    except FileNotFoundError:
        have_x = False

    pp = np.linspace(0, 0.5, 200)
    theory = 3 * pp**2 - 2 * pp**3

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    # regione in cui la codifica conviene (p_L < p): sotto la bisettrice
    ax.plot([0, 0.5], [0, 0.5], ls=':', color='0.6', lw=1,
            label=r'$p_L = p$ (qubit fisico non codificato)')
    ax.plot(pp, theory, color='C3', lw=2,
            label=r'previsione analitica $3p^2 - 2p^3$')
    ax.errorbar(p, pL_z, yerr=se_z, fmt='o', color='C0', ms=5, capsize=3,
                label='bit-flip (Monte Carlo)')
    if have_x:
        ax.errorbar(p, pL_x, yerr=se_x, fmt='s', color='C2', ms=4, capsize=3,
                    mfc='none', label='phase-flip (Monte Carlo)')
    ax.axvline(0.5, color='0.8', lw=0.8)
    ax.annotate('break-even\n$p=0.5$', xy=(0.5, 0.5), xytext=(0.36, 0.40),
                fontsize=8, color='0.4')

    ax.set_xlabel(r'errore fisico per qubit $p$')
    ax.set_ylabel(r'errore logico $p_L$')
    ax.set_xlim(0, 0.52)
    ax.set_ylim(0, 0.52)
    ax.set_title('Codice a ripetizione a 3 qubit: correzione di un errore singolo')
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_repetition_curve')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png")


if __name__ == '__main__':
    main()
