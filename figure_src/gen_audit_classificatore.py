"""
gen_audit_classificatore.py — tre figure a supporto dell'audit del classificatore
(Appendice F) e della sezione sulla frazione coerente efficace (Capitolo 10):

  1. audit_istogramma_negativo  — un istogramma etichettato "negativo" dal dataset
     originale, con i quattro picchi QPE evidenziati: il segnale c'e' tutto, e' solo
     la moda a cadere sull'esito sterile y=0.
  2. frazione_coerente          — f efficace contro P_surv in scala doppio-logaritmica:
     coincidono a rumore basso, divergono di ventitre ordini di grandezza.
  3. tetto_classe_negativa      — frazione massima di negativi ottenibile con la regola
     TOP-K su istogramma privo di segnale, con i due punti osservati.

Uso: python gen_audit_classificatore.py
"""
import os
import sys
from math import comb

import joblib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments',
                       'campagne_classiche_M1-M4')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure')
sys.path.insert(0, EXP_DIR)

N, A, N_COUNT = 15, 7, 8
N_CELLE = 2 ** N_COUNT
PICCHI = [0, 64, 128, 192]


def _salva(fig, nome):
    base = os.path.join(OUT_DIR, nome)
    fig.savefig(base + '.pdf', bbox_inches='tight')
    fig.savefig(base + '.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  -> {base}.pdf')


# ---------------------------------------------------------------- figura 1
def fig_istogramma_negativo():
    from shor_core import extract_factors

    d = joblib.load(os.path.join(EXP_DIR, 'clf_UC1_campagna_originale.joblib'))
    X, y = d['X_test'], d['y_test']
    neg = X[y == 0]
    # si sceglie il campione negativo la cui massa sui picchi e' mediana: rappresentativo
    masse = neg[:, PICCHI].sum(axis=1)
    riga = neg[np.argsort(masse)[len(masse) // 2]]

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.bar(np.arange(N_CELLE), riga, width=1.0, color='0.75',
           label='esiti non utili')

    utili = [k for k in PICCHI if extract_factors(k, N_COUNT, N, A)[0] is not None]
    ax.bar(utili, riga[utili], width=3.0, color='C2',
           label='picchi che conducono ai fattori $(3,5)$')
    ax.bar([0], riga[[0]], width=3.0, color='C3',
           label='moda $y=0$: fase nulla, scartata per costruzione')

    ordine = np.argsort(-riga)[:4]
    for rango, k in enumerate(ordine, start=1):
        ax.annotate(f'#{rango}\n$y={int(k)}$', xy=(k, riga[k]),
                    xytext=(k, riga[k] + 0.012), ha='center', fontsize=8.5,
                    color='C3' if k == 0 else 'C2', fontweight='bold')

    ax.set_xlabel('esito della misura $y$ (registro di controllo, $2^8 = 256$ celle)')
    ax.set_ylabel('frequenza relativa')
    ax.set_title("Un istogramma etichettato «negativo» nel dataset di addestramento",
                 fontsize=11)
    ax.set_xlim(-4, N_CELLE + 3)
    ax.set_ylim(0, riga.max() * 1.22)
    # legenda sotto gli assi: in alto collide con le etichette dei quattro picchi
    ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.17),
              ncol=1, frameon=False)
    ax.grid(alpha=0.25, axis='y')
    _salva(fig, 'audit_istogramma_negativo')


# ---------------------------------------------------------------- figura 2
def fig_frazione_coerente():
    # Misure di frazione_coerente_efficace.py (k_2q = 166 porte a due qubit).
    eps = np.array([1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1, 3e-1])
    f = np.array([0.8621, 0.8041, 0.7386, 0.6221, 0.3721, 0.1582, 0.0319, 0.0076])
    p_surv = (1 - eps) ** 166

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.plot(eps, p_surv, 's--', color='C3', ms=5, lw=1.3,
            label=r'$P_{\mathrm{surv}} = (1-\varepsilon_{2q})^{166}$  (stima analitica)')
    ax.plot(eps, f, 'o-', color='C0', ms=6, lw=1.6,
            label=r'$f$ efficace  (misurata)')

    for x, marcatore, testo in ((1e-2, 'UC1', 'UC1'), (5e-2, 'UC2', 'UC2')):
        ax.axvline(x, color='0.6', ls=':', lw=1)
        ax.annotate(testo, xy=(x, 3e-3), fontsize=8, color='0.35',
                    ha='center', backgroundcolor='white')

    i = -1
    esponente = int(np.floor(np.log10(f[i] / p_surv[i])))
    mantissa = (f[i] / p_surv[i]) / 10 ** esponente
    ax.annotate(f'divario\n${mantissa:.0f}\\times 10^{{{esponente}}}$',
                xy=(eps[i], np.sqrt(f[i] * p_surv[i])), fontsize=8.5, ha='right',
                xytext=(eps[i] * 0.72, np.sqrt(f[i] * p_surv[i])), color='0.25')
    ax.annotate('', xy=(eps[i], f[i]), xytext=(eps[i], p_surv[i]),
                arrowprops=dict(arrowstyle='<->', color='0.5', lw=1))

    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_ylim(1e-28, 3)
    ax.set_xlabel(r'errore sui gate a due qubit $\varepsilon_{2q}$')
    ax.set_ylabel('frazione di segnale coerente')
    ax.set_title('Quanto $P_{\\mathrm{surv}}$ sottostima la sopravvivenza del segnale',
                 fontsize=11)
    ax.legend(fontsize=8, loc='lower left')
    ax.grid(alpha=0.3, which='both')
    _salva(fig, 'frazione_coerente')


# ---------------------------------------------------------------- figura 3
def fig_tetto_classe_negativa():
    from shor_core import extract_factors

    utili = sum(1 for k in range(N_CELLE)
                if extract_factors(k, N_COUNT, N, A)[0] is not None)
    ks = np.arange(1, 33)
    tetto = np.array([comb(N_CELLE - utili, k) / comb(N_CELLE, k)
                      if k <= N_CELLE - utili else 0.0 for k in ks])

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.plot(ks, 100 * tetto, '-', color='0.4', lw=1.6,
            label='tetto teorico su istogramma privo di segnale')
    ax.plot([1], [25.8], 'o', color='C3', ms=9,
            label='TOP-1: regola effettivamente usata (25.8% osservato)')
    ax.plot([16], [0.5], 's', color='C0', ms=9,
            label='TOP-16: regola documentata (0.5% osservato)')

    for k, testo in ((1, '75.4%'), (4, '32.1%'), (16, '0.9%')):
        ax.annotate(testo, xy=(k, 100 * tetto[k - 1]),
                    xytext=(k + 0.7, 100 * tetto[k - 1] * 1.45),
                    fontsize=8, color='0.3')

    ax.set_yscale('log')
    ax.set_xlabel('numero di candidati valutati $K$')
    ax.set_ylabel('frazione massima di campioni negativi (%)')
    ax.set_title(f'Il tetto combinatorio: {utili} esiti su {N_CELLE} conducono ai fattori',
                 fontsize=11)
    ax.legend(fontsize=8, loc='lower left')
    ax.grid(alpha=0.3, which='both')
    _salva(fig, 'tetto_classe_negativa')


if __name__ == '__main__':
    print('Generazione figure audit classificatore ...')
    fig_istogramma_negativo()
    fig_frazione_coerente()
    fig_tetto_classe_negativa()
