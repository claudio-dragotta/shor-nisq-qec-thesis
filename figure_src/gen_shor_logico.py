"""
gen_shor_logico.py — FIGURA CONCLUSIVA della tesi (M8, documento §11.3).
P_success di Shor (N=15) in funzione dell'errore logico p_L, con i tre regimi sovrapposti:
circuito fisico nudo -> codice di Steane -> surface code. Mostra come, riducendo p_L con la
correzione, la probabilità di successo risale verso il limite dell'istanza.

Curva: JSON di experiments/M8_shor_logico/. Regimi p_L: dai risultati M6 (Steane) e M7 (surface).

Uso: python gen_shor_logico.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments', 'M8_shor_logico')

# Regimi (errore logico p_L per gate) — valori dai risultati M6/M7:
#   fisico nudo:  errore fisico non corretto, ~ epsilon_2q NISQ
#   Steane:       M6, Steane a p_fisico=0.01 -> p_L≈1.7e-3
#   surface d=7:  M7, a p_fisico sotto soglia (p=0.002) -> p_L≈1e-4
REGIMES = [
    ('Shor fisico nudo\n(nessuna correzione)', 1.0e-2, 'C3'),
    ('Steane [[7,1,3]]', 1.7e-3, 'C1'),
    ('surface code $d=7$', 1.0e-4, 'C2'),
]


def _latest():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M8_shor_logico_*.json')))
    if not files:
        raise FileNotFoundError("Nessun JSON M8. Esegui: python shor_logico.py")
    with open(files[-1]) as f:
        return json.load(f)


def main():
    data = _latest()
    c = data['curve']
    pts = c['points']
    pL = np.array([r['p_L'] for r in pts])
    pS = np.array([r['P_success'] for r in pts])
    se = np.array([r['P_success_se'] for r in pts])
    P_ideal = c['P_ideal']

    # per posizionare i regimi: interpolo P_success al p_L del regime (in log).
    # Aggiungo un'ancora a p_L→0 (= limite intrinseco) così i regimi a p_L molto piccolo
    # (es. surface d=7, ~1e-4) non vengono appiattiti al primo punto simulato (2e-3).
    mask = pL > 0
    logpL = np.concatenate([[-6.0], np.log10(pL[mask])])
    ys = np.concatenate([[P_ideal], pS[mask]])
    order = np.argsort(logpL)
    logpL, ys = logpL[order], ys[order]

    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    # limite intrinseco dell'istanza
    ax.axhline(P_ideal, color='0.6', ls=':', lw=1,
               label=f'limite intrinseco $N=15$ ({P_ideal:.2f})')
    # curva P_success vs p_L
    ax.errorbar(pL[mask], pS[mask], yerr=se[mask], fmt='o-', color='C0', ms=4, lw=1.4,
                capsize=2, label='Shor $N=15$ (per singola misura)')

    # regimi
    p_min = min(r[1] for r in REGIMES)
    for label, p_reg, col in REGIMES:
        y_reg = float(np.interp(np.log10(p_reg), logpL, ys))
        ax.axvline(p_reg, color=col, ls='--', lw=1.1, alpha=0.8)
        ax.plot(p_reg, y_reg, 'D', color=col, ms=7, zorder=5)
        ha = 'left' if p_reg == p_min else 'center'
        xt = p_reg * 1.4 if ha == 'left' else p_reg
        ax.annotate(label, xy=(p_reg, y_reg), xytext=(xt, y_reg + 0.06),
                    fontsize=7.5, color=col, ha=ha, fontweight='bold')

    # freccia "direzione della correzione"
    ax.annotate('', xy=(1.3e-4, 0.30), xytext=(0.8e-2, 0.30),
                arrowprops=dict(arrowstyle='->', color='0.4', lw=1.3))
    ax.text(1.0e-3, 0.25, 'più correzione  →  meno errore  →  più successo',
            fontsize=7.5, color='0.4', ha='center')

    ax.set_xscale('log')
    ax.set_xlabel(r'errore logico per gate $p_L$')
    ax.set_ylabel(r'probabilità di successo di Shor')
    ax.set_ylim(0.15, 0.85)
    ax.set_xlim(5e-5, 1)
    ax.set_title('Figura conclusiva: Shor fisico vs Steane vs surface code')
    ax.legend(fontsize=8, loc='lower left')
    ax.grid(alpha=0.3, which='both')
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure', 'qec_shor_logico_curve')
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png")


if __name__ == '__main__':
    main()
