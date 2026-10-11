"""
gen_qec_surface.py — figura M7: curve p vs p_L del surface code in base Z.
Legge un JSON esplicito di experiments/M7_surface_code/ e produce
qec_surface_curve.pdf in file_latex/figure, con anteprima .png in
figure_src/anteprime: la firma della soglia è l'incrocio delle curve a
distanza crescente.

Questa figura non è più inclusa nella tesi: nel capitolo sul surface code è
stata sostituita da gen_qec_surface_zone.py, che mostra entrambe le basi con
le zone operative. Resta disponibile come vista in sola base Z.

L'input è esplicito: nessuna selezione implicita del file più recente. Il
default punta al JSON canonico a quattro distanze (d = 3, 5, 7, 9); i file del
31/07/2026 ne contengono solo tre.

Uso:
    python gen_qec_surface.py
    python gen_qec_surface.py --input <file.json>
"""
import argparse
import json
import os

import numpy as np
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
EXP_DIR = os.path.join(_HERE, '..', 'Extra', 'experiments', 'M7_surface_code')
PNG_DIR = os.path.join(_HERE, 'anteprime')

# JSON M7 canonico in base Z, indicato per nome esatto: la regola sui
# generatori vieta di lasciare che sia il glob a scegliere.
DEFAULT_INPUT = 'results_M7_surface_z_20260808_001903.json'


def _parse_args():
    ap = argparse.ArgumentParser(description='Figura M7: curve p vs p_L, base Z.')
    ap.add_argument('--input', default=os.path.join(EXP_DIR, DEFAULT_INPUT),
                    help='JSON M7 da usare (default: %(default)s)')
    return ap.parse_args()


def _load(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"JSON M7 non trovato: {path}. "
            "Indicarlo con --input, oppure eseguire qec_surface.py."
        )
    with open(path) as f:
        return json.load(f)


def main():
    args = _parse_args()
    data = _load(args.input)
    print(f"[gen_qec_surface] input <- {os.path.basename(args.input)}")
    curve = data['curve']
    table = curve['table']
    p_th = curve['threshold']   # niente fallback: deve venire dal JSON
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

    out = os.path.join(_HERE, '..', 'file_latex', 'figure', 'qec_surface_curve')
    fig.savefig(out + '.pdf')
    os.makedirs(PNG_DIR, exist_ok=True)
    png = os.path.join(PNG_DIR, 'qec_surface_curve.png')
    fig.savefig(png, dpi=150)
    print(f"Figura salvata: {out}.pdf  (soglia p_th={p_th})")
    print(f"Anteprima: {png}")


if __name__ == '__main__':
    main()
