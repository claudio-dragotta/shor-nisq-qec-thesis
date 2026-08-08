"""
gen_confronto_decoder.py — figura E7: BP+OSD e decoder ibrido agiscono su assi ortogonali.

Il guadagno di BP+OSD sul MWPM DECRESCE al crescere del crosstalk (sfrutta meglio il
modello che riceve, e il modello diventa progressivamente sbagliato); quello del decoder
ibrido CRESCE (cattura cio' che al modello sfugge, e cio' che sfugge aumenta). E' la
lettura centrale della sezione, e in forma tabellare non si vede.

Uso: python gen_confronto_decoder.py
"""
import glob
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

EXP = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments',
                   'M10_neural_decoder')
OUT = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure')


def _tutti_i_punti(pattern):
    """Unisce i punti di tutti i JSON che corrispondono al pattern.

    La campagna dell'ibrido e' stata eseguita in due riprese (d=3,5 e poi d=7), quindi
    prendere il solo file piu' recente perderebbe le distanze basse.
    """
    punti = []
    for percorso in sorted(glob.glob(os.path.join(EXP, pattern))):
        with open(percorso) as fh:
            punti.extend(json.load(fh).get('points', []))
    if not punti:
        raise FileNotFoundError(pattern)
    return punti


def main():
    # guadagno = pL_mwpm / pL_metodo, per (distanza, crosstalk)
    g_bp, g_ib = {}, {}
    for r in _tutti_i_punti('results_M10_bposd_*.json'):
        g_bp.setdefault(r['d'], {})[r['p_crosstalk']] = r['pL_mwpm'] / r['pL_bposd']
    for r in _tutti_i_punti('results_M10_hybrid_*.json'):
        g_ib.setdefault(r['d'], {})[r['p_crosstalk']] = r['pL_mwpm'] / r['pL_hybrid']

    distanze = [d for d in (3, 5) if d in g_bp and d in g_ib]
    fig, axes = plt.subplots(1, len(distanze), figsize=(10, 4.2), sharey=True)
    if len(distanze) == 1:
        axes = [axes]

    for ax, d in zip(axes, distanze):
        pct = sorted(g_bp[d])
        ax.axhline(1.0, color='0.6', ls='--', lw=1)
        ax.plot([100 * x for x in pct], [g_bp[d][x] for x in pct], 'o-',
                color='C0', ms=6, lw=1.7, label='BP+OSD (decoder analitico migliore)')
        ax.plot([100 * x for x in pct], [g_ib[d][x] for x in pct], 's-',
                color='C3', ms=6, lw=1.7, label='ibrido appreso (MWPM + rete)')
        ax.set_title(f'distanza $d = {d}$', fontsize=11)
        ax.set_xlabel('intensità del crosstalk (%)')
        ax.grid(alpha=0.3)

    axes[0].set_ylabel('guadagno rispetto al MWPM\n($p_L^{\\mathrm{MWPM}} / p_L$)')
    axes[-1].legend(fontsize=8.5, loc='upper right')
    fig.suptitle('Due sorgenti di guadagno ortogonali: sfruttare il modello '
                 'contro catturare ciò che gli sfugge', fontsize=11.5)
    fig.tight_layout()

    base = os.path.join(OUT, 'confronto_decoder')
    fig.savefig(base + '.pdf', bbox_inches='tight')
    fig.savefig(base + '.png', dpi=150, bbox_inches='tight')
    print(f'Figura salvata: {base}.pdf / .png')


if __name__ == '__main__':
    main()
