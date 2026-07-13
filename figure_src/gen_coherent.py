"""
gen_coherent.py — figura (Cap. 12): errore coerente vs errore di Pauli (accumulo).
Legge il JSON di experiments/extra_rumore_coerente/ e mostra che, a parità di probabilità
di errore per operazione, l'errore coerente cresce molto più rapidamente di quello di Pauli
→ il modello Pauli (Stim/twirling) è ottimistico.

Uso: python gen_coherent.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments', 'extra_rumore_coerente')


def _latest():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_coherent_vs_pauli_*.json')))
    if not files:
        raise FileNotFoundError("Nessun JSON. Esegui: python qec_coherent.py")
    with open(files[-1]) as f:
        return json.load(f)


def main():
    data = _latest()
    p = data['p']
    pts = data['points']
    N = np.array([r['N'] for r in pts])
    coe_sim = np.array([r['coherent_sim'] for r in pts])
    coe_th = np.array([r['coherent_theory'] for r in pts])
    pau_sim = np.array([r['pauli_sim'] for r in pts])
    pau_th = np.array([r['pauli_theory'] for r in pts])

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.plot(N, coe_th, '-', color='C3', lw=1.4, label='coerente (teoria $\\sin^2(N\\theta/2)$)')
    ax.plot(N, coe_sim, 'o', color='C3', ms=5, label='coerente (simulazione)')
    ax.plot(N, pau_th, '-', color='C0', lw=1.4, label='Pauli (teoria)')
    ax.plot(N, pau_sim, 's', color='C0', ms=4, mfc='none', label='Pauli (simulazione)')

    # evidenzia il divario a un N rappresentativo
    i = 7  # N=8
    ax.annotate(f'a $N={N[i]}$: {coe_sim[i]/pau_sim[i]:.0f}$\\times$',
                xy=(N[i], coe_sim[i]), xytext=(N[i] + 1.5, coe_sim[i] - 0.02),
                fontsize=8.5, color='0.25',
                arrowprops=dict(arrowstyle='->', color='0.5', lw=0.8))
    ax.annotate('', xy=(N[i], coe_sim[i]), xytext=(N[i], pau_sim[i]),
                arrowprops=dict(arrowstyle='<->', color='0.5', lw=1))

    ax.set_xlabel(r'numero di operazioni rumorose $N$')
    ax.set_ylabel(r'probabilità di errore accumulato')
    ax.set_title(f'Errore coerente vs Pauli (stessa $p={p}$ per operazione)')
    ax.set_xticks(N[::2])
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_coherent')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png")


if __name__ == '__main__':
    main()
