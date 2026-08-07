"""
gen_qec_surface.py — figura M7: curve p vs p_L del surface code per d=3,5,7.
Legge il JSON di experiments/M7_surface_code/ e produce qec_surface_curve.pdf/png:
la firma della soglia è l'incrocio delle curve a distanza crescente.

Uso: python gen_qec_surface.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments', 'M7_surface_code')


def _latest():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M7_surface_*.json')))
    if not files:
        raise FileNotFoundError("Nessun JSON M7. Esegui: python qec_surface.py")
    with open(files[-1]) as f:
        return json.load(f)


def main():
    data = _latest()
    curve = data['curve']
    table = curve['table']
    p_th = curve.get('threshold')
    distances = sorted(int(d) for d in table)

    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    colors = {3: 'C0', 5: 'C1', 7: 'C2', 9: 'C3'}
    markers = {3: 'o', 5: 's', 7: '^', 9: 'D'}
    for d in distances:
        pts = table[str(d)]
        p = np.array([r['p'] for r in pts])
        pL = np.array([r['p_L'] for r in pts])
        se = np.array([r['p_L_se'] for r in pts])
        ax.errorbar(p, pL, yerr=se, fmt=markers.get(d, 'o') + '-', color=colors.get(d, None),
                    ms=5, capsize=2, lw=1.3, label=f'$d={d}$')

    if p_th:
        ax.axvline(float(p_th), color='0.5', ls='--', lw=1)
        # a destra della linea resta poco spazio prima del bordo: l'etichetta va a sinistra
        ax.annotate(f'soglia $p_{{th}}\\approx{float(p_th):.3f}$',
                    xy=(float(p_th) * 0.97, 1.2e-4), fontsize=8.5, color='0.35',
                    ha='right', rotation=90, va='bottom')

    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(r'errore fisico $p$ (circuit-level)')
    ax.set_ylabel(r'errore logico $p_L$')
    ax.set_title('Surface code: comportamento a soglia (decoder MWPM)')
    ax.legend(fontsize=9, title='distanza')
    ax.grid(alpha=0.3, which='both')
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_surface_curve')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png  (soglia p_th={p_th})")


if __name__ == '__main__':
    main()
