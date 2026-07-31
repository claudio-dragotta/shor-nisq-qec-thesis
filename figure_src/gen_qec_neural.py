"""
gen_qec_neural.py — figure M10: decodifica appresa vs MWPM sul surface code.
Legge il JSON di experiments/M10_neural_decoder/ e produce tre figure:

  qec_neural_leale.pdf     E1  — confronto leale (DEM esatto) + scaling col volume di dati
  qec_neural_crosstalk.pdf E2  — rumore correlato: MWPM nominale / MWPM oracolo / rete
  qec_neural_flag.pdf      E3  — la rete come validatore della correzione MWPM

Uso: python gen_qec_neural.py
"""
import glob
import json
import os

import numpy as np
import matplotlib.pyplot as plt

EXP_DIR = os.path.join(os.path.dirname(__file__), '..', 'Extra', 'experiments',
                       'M10_neural_decoder')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'file_latex', 'figure')

C_MWPM, C_NN, C_ORA, C_TRIV = 'C0', 'C3', 'C1', '0.6'
MK = {3: 'o', 5: 's', 7: '^'}


def _latest():
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M10_neural_decoder_*.json')))
    if not files:
        raise FileNotFoundError("Nessun JSON M10. Esegui: python qec_neural_decoder.py")
    with open(files[-1]) as f:
        return json.load(f)


def _save(fig, name):
    out = os.path.join(OUT_DIR, name)
    fig.savefig(out + '.pdf')
    fig.savefig(out + '.png', dpi=150)
    print(f"Figura salvata: {out}.pdf / .png")


def _arr(points, key):
    return np.array([r[key] for r in points], dtype=float)


# ----------------------------------------------------------------------------- E1
def fig_leale(data):
    e1 = data['E1_leale']['points']
    e1b = data.get('E1b_scaling', {}).get('points', [])
    distances = sorted({r['d'] for r in e1})

    ncols = 2 if e1b else 1
    fig, axes = plt.subplots(1, ncols, figsize=(10.6 if e1b else 5.6, 4.3))
    ax = axes[0] if e1b else axes

    for d in distances:
        pts = [r for r in e1 if r['d'] == d]
        p = _arr(pts, 'p')
        ax.errorbar(p, _arr(pts, 'pL_mwpm'), yerr=_arr(pts, 'pL_mwpm_se'),
                    fmt=MK.get(d, 'o') + '-', color=C_MWPM, ms=5, lw=1.3, capsize=2,
                    label=f'MWPM, $d={d}$')
        ax.errorbar(p, _arr(pts, 'pL_nn'), yerr=_arr(pts, 'pL_nn_se'),
                    fmt=MK.get(d, 'o') + '--', color=C_NN, ms=5, lw=1.3, capsize=2,
                    mfc='none', label=f'rete, $d={d}$')

    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(r'errore fisico $p$ (circuit-level)')
    ax.set_ylabel(r'errore logico $p_L$')
    ax.set_title('(a) Confronto leale: MWPM riceve il modello esatto', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, which='both')

    if e1b:
        ax2 = axes[1]
        n = _arr(e1b, 'n_train')
        ax2.errorbar(n, _arr(e1b, 'pL_nn'), yerr=_arr(e1b, 'pL_nn_se'),
                     fmt='o--', color=C_NN, ms=5, lw=1.3, capsize=2, mfc='none',
                     label='rete')
        mw = float(np.mean(_arr(e1b, 'pL_mwpm')))
        ax2.axhline(mw, color=C_MWPM, lw=1.4, label='MWPM (DEM esatto)')
        ax2.axhline(float(np.mean(_arr(e1b, 'base_rate'))), color=C_TRIV, ls=':', lw=1.2,
                    label='nessuna correzione')
        ax2.set_xscale('log'); ax2.set_yscale('log')
        ax2.set_xlabel('campioni di addestramento')
        ax2.set_ylabel(r'errore logico $p_L$')
        d0 = data['E1b_scaling']['d']; p0 = data['E1b_scaling']['p']
        ax2.set_title(f'(b) Fame di dati ($d={d0}$, $p={p0}$)', fontsize=10)
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3, which='both')

    fig.tight_layout()
    _save(fig, 'qec_neural_leale')


# ----------------------------------------------------------------------------- E2
def fig_crosstalk(data):
    pts = data['E2_crosstalk']['points']
    distances = sorted({r['d'] for r in pts})
    fig, axes = plt.subplots(1, len(distances), figsize=(5.4 * len(distances), 4.3),
                             squeeze=False)

    for ax, d in zip(axes[0], distances):
        sub = sorted([r for r in pts if r['d'] == d], key=lambda r: r['p_crosstalk'])
        pct = _arr(sub, 'p_crosstalk')
        # il punto p_ct=0 non si vede in scala log: lo si mostra come linea di riferimento
        ref = [r for r in sub if r['p_crosstalk'] == 0]
        withct = [r for r in sub if r['p_crosstalk'] > 0]
        x = _arr(withct, 'p_crosstalk')

        ax.errorbar(x, _arr(withct, 'pL_mwpm'), yerr=_arr(withct, 'pL_mwpm_se'),
                    fmt='o-', color=C_MWPM, ms=5, lw=1.4, capsize=2,
                    label='MWPM (modello nominale)')
        ora = [r for r in withct if r.get('pL_mwpm_oracle') is not None]
        if ora:
            ax.errorbar(_arr(ora, 'p_crosstalk'), _arr(ora, 'pL_mwpm_oracle'),
                        yerr=_arr(ora, 'pL_mwpm_oracle_se'),
                        fmt='^-', color=C_ORA, ms=5, lw=1.2, capsize=2, mfc='none',
                        label='MWPM (modello reale)')
        ax.errorbar(x, _arr(withct, 'pL_nn'), yerr=_arr(withct, 'pL_nn_se'),
                    fmt='s--', color=C_NN, ms=5, lw=1.4, capsize=2,
                    label='rete (appresa dai dati)')
        ax.plot(x, _arr(withct, 'base_rate'), ':', color=C_TRIV, lw=1.2,
                label='nessuna correzione')
        if ref:
            ax.axhline(ref[0]['pL_mwpm'], color=C_MWPM, ls='-.', lw=1,
                       alpha=0.6, label='MWPM senza crosstalk')

        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel('intensità del crosstalk $p_{ct}$')
        ax.set_ylabel(r'errore logico $p_L$')
        ax.set_title(f'$d={d}$', fontsize=10)
        ax.legend(fontsize=7.5, loc='lower right')
        ax.grid(alpha=0.3, which='both')

    fig.suptitle('Rumore correlato: il matching non ha archi per rappresentarlo',
                 fontsize=11)
    fig.tight_layout()
    _save(fig, 'qec_neural_crosstalk')


# ----------------------------------------------------------------------------- E3
def fig_flag(data):
    e3 = data.get('E3_validatore')
    if not e3:
        return
    rows = e3['soglie']
    thr = [r['soglia'] for r in rows]
    prec = [r['precision'] for r in rows]
    rec = [r['recall'] for r in rows]
    rate = [r['flag_rate'] * 100 for r in rows]

    fig, ax = plt.subplots(figsize=(6.2, 4.3))
    ax.plot(thr, prec, 'o-', color=C_NN, lw=1.5, ms=6, label='precision del flag')
    ax.plot(thr, rec, 's--', color=C_MWPM, lw=1.5, ms=6, label='recall del flag')
    ax.set_xlabel('soglia di confidenza sotto cui la rete nega la correzione')
    ax.set_ylabel('precision / recall')
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)

    ax2 = ax.twinx()
    ax2.bar(thr, rate, width=0.03, color=C_TRIV, alpha=0.35, label='shot segnalati (%)')
    ax2.set_ylabel('shot segnalati (%)')

    c = e3['config']
    auc = e3.get('auc_flag')
    ax.set_title(f"La rete come validatore di MWPM ($d={c['d']}$, "
                 f"$p_{{ct}}={c['p_crosstalk']}$)"
                 + (f" — AUC = {auc:.3f}" if auc else ''), fontsize=10)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='center right')
    fig.tight_layout()
    _save(fig, 'qec_neural_flag')


# ----------------------------------------------------------------------------- E4
def fig_hybrid():
    """Decoder ibrido: la rete non sostituisce MWPM, impara quando ribaltarlo."""
    files = sorted(glob.glob(os.path.join(EXP_DIR, 'results_M10_hybrid_*.json')))
    if not files:
        print("Nessun JSON E4: salto la figura dell'ibrido.")
        return
    with open(files[-1]) as f:
        pts = json.load(f)['points']

    distances = sorted({r['d'] for r in pts})
    fig, axes = plt.subplots(1, len(distances), figsize=(5.4 * len(distances), 4.3),
                             squeeze=False)
    for ax, d in zip(axes[0], distances):
        sub = sorted([r for r in pts if r['d'] == d and r['p_crosstalk'] > 0],
                     key=lambda r: r['p_crosstalk'])
        x = _arr(sub, 'p_crosstalk')
        ax.errorbar(x, _arr(sub, 'pL_mwpm'), yerr=_arr(sub, 'pL_mwpm_se'),
                    fmt='o-', color=C_MWPM, ms=5, lw=1.4, capsize=2, label='MWPM')
        ax.errorbar(x, _arr(sub, 'pL_nn'), yerr=_arr(sub, 'pL_nn_se'),
                    fmt='s--', color=C_ORA, ms=5, lw=1.2, capsize=2, mfc='none',
                    label='rete da sola (sostituzione)')
        ax.errorbar(x, _arr(sub, 'pL_hybrid'), yerr=_arr(sub, 'pL_hybrid_se'),
                    fmt='D-', color=C_NN, ms=5, lw=1.6, capsize=2,
                    label='ibrido MWPM + rete')
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel('intensità del crosstalk $p_{ct}$')
        ax.set_ylabel(r'errore logico $p_L$')
        ax.set_title(f'$d={d}$', fontsize=10)
        ax.legend(fontsize=8, loc='lower right')
        ax.grid(alpha=0.3, which='both')

    fig.suptitle('Decoder ibrido: la rete corregge il matching invece di sostituirlo',
                 fontsize=11)
    fig.tight_layout()
    _save(fig, 'qec_neural_ibrido')


def main():
    data = _latest()
    if 'E1_leale' in data:
        fig_leale(data)
    if 'E2_crosstalk' in data:
        fig_crosstalk(data)
    fig_flag(data)
    fig_hybrid()


if __name__ == '__main__':
    main()
