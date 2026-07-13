"""
gen_shor_pk.py — figura: probabilità di successo cumulativa di Shor dopo k esecuzioni.
P(k) = 1 - (1 - Ps)^k  (esecuzioni indipendenti).

Indicazione del relatore: la probabilità per singolo run (Ps) NON è un limite invalicabile;
con poche ripetizioni si supera comodamente l'80%. La figura lo mostra per il valore misurato
a p_L→0 su N=15 (Ps≈0.75) e per alcuni regimi di rumore.

Uso: python gen_shor_pk.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments', 'M8_shor_logico')


def _P_ideal():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M8_shor_logico_*.json')))
    if files:
        with open(files[-1]) as f:
            return json.load(f)['curve']['P_ideal']
    return 0.75


def main():
    Ps_ideal = _P_ideal()
    k = np.arange(1, 9)
    # Ps rappresentativi: limite N=15 (p_L→0), regime fisico, rumore medio, plateau
    curves = [
        (Ps_ideal, f'$P_s = {Ps_ideal:.2f}$ (N=15, $p_L\\to 0$)', 'C0', 'o'),
        (0.64, '$P_s = 0.64$ (fisico nudo)', 'C3', 's'),
        (0.40, '$P_s = 0.40$ (rumore medio)', 'C1', '^'),
        (0.25, '$P_s = 0.25$ (plateau)', '0.5', 'D'),
    ]

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.axhline(0.80, color='C2', ls=':', lw=1.3, label='soglia 80\\%')
    for Ps, lab, col, mk in curves:
        Pk = 1 - (1 - Ps) ** k
        ax.plot(k, Pk, mk + '-', color=col, ms=5, lw=1.4, label=lab)
        # primo k che supera 0.80
        kk = np.argmax(Pk >= 0.80)
        if Pk[kk] >= 0.80:
            ax.plot(k[kk], Pk[kk], 'o', color=col, ms=11, mfc='none', mew=1.6)

    ax.set_xlabel(r'numero di esecuzioni $k$')
    ax.set_ylabel(r'$P(k) = 1-(1-P_s)^k$')
    ax.set_title('Probabilità di successo cumulativa di Shor dopo $k$ esecuzioni')
    ax.set_xticks(k)
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8, loc='lower right')
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_shor_pk')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    # riepilogo: k per superare 80%
    for Ps, lab, _, _ in curves:
        Pk = 1 - (1 - Ps) ** k
        kk = int(np.argmax(Pk >= 0.80)) + 1
        print(f"  Ps={Ps:.2f}: k={kk} esecuzioni per superare 80% (P={1-(1-Ps)**kk:.3f})")
    print(f"Figura salvata: {out}.pdf / .png")


if __name__ == '__main__':
    main()
