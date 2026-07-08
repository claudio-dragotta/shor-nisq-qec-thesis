"""
generate_figures.py — Genera le figure per la tesi (Cap. 10-11).

Figure prodotte (salvate in ../file_latex/figure/):
  fig_istogrammi_qpe.pdf   — Istogramma QPE con segnale vs istogramma piatto (UC1)
  fig_roc_curve.pdf        — Curve ROC dei classificatori (UC1: RF, UC2: SVM)
  fig_iterazioni_m1_m2.pdf — Box plot iterazioni M1 vs M2 su UC1

Eseguire da WSL con quantum-env attivato:
  source ~/quantum-env/bin/activate
  cd ~/path/to/experiments
  python generate_figures.py
"""

import joblib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_curve, auc

from shor_core import build_noise_model, shor_circuit, run_method1, run_method2
from qiskit import transpile
from qiskit_aer import AerSimulator

OUT_DIR = '../file_latex/figure'
FIGSIZE_WIDE  = (10, 4)
FIGSIZE_SQUARE = (6, 5)
FIGSIZE_BOX   = (6, 5)

NOISE_REALISTIC = dict(eps_1q=1e-3, eps_2q=1e-2, t1_ns=100_000, t2_ns=80_000, p_ro=0.02)
NOISE_DEGRADED  = dict(eps_1q=5e-3, eps_2q=5e-2, t1_ns=50_000,  t2_ns=30_000,  p_ro=0.05)


# ──────────────────────────────────────────────
# Figura 1: Istogrammi QPE comparativi (UC1)
# ──────────────────────────────────────────────

def fig_istogrammi_qpe():
    print('Generazione fig_istogrammi_qpe.pdf ...')
    nm = build_noise_model(**NOISE_REALISTIC)
    sim = AerSimulator(noise_model=nm, method='statevector')
    qc  = shor_circuit(15, 7, 8)
    tc  = transpile(qc, sim, optimization_level=2)

    # Seed 0 → tipicamente buon segnale per UC1
    counts_good = sim.run(tc, shots=1024, seed_simulator=1).result().get_counts()
    # Seed 6 → iterazione difficile (segnale debole, trovato empiricamente con M1 K=30)
    counts_flat = sim.run(tc, shots=1024, seed_simulator=60001).result().get_counts()

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    for ax, counts, title, color in zip(
        axes,
        [counts_good, counts_flat],
        ['Iterazione con segnale QPE', 'Iterazione dominata dal rumore'],
        ['steelblue', 'tomato']
    ):
        x = np.arange(256)
        y = np.zeros(256)
        for k, v in counts.items():
            y[int(k, 2)] = v / 1024

        ax.bar(x, y, color=color, alpha=0.75, width=1.0)
        # Evidenzia i picchi teorici: 64, 128, 192
        for peak in [64, 128, 192]:
            ax.axvline(peak, color='black', linestyle='--', linewidth=1.0, alpha=0.7)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('Misura QPE (valore decimale)', fontsize=10)
        ax.set_ylabel('Frequenza relativa', fontsize=10)
        ax.set_xlim(0, 255)
        ax.set_xticks([0, 64, 128, 192, 255])

    axes[0].annotate('64', xy=(64, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)
    axes[0].annotate('128', xy=(128, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)
    axes[0].annotate('192', xy=(192, axes[0].get_ylim()[1]*0.95), ha='center', fontsize=9)

    fig.suptitle('Istogrammi QPE — UC1 ($N=15$, NISQ-realistico)', fontsize=12)
    plt.tight_layout()
    path = f'{OUT_DIR}/fig_istogrammi_qpe.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f'  → {path}')


# ──────────────────────────────────────────────
# Figura 2: Curve ROC
# ──────────────────────────────────────────────

def fig_roc_curve():
    print('Generazione fig_roc_curve.pdf ...')

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    configs = [
        ('UC1', 'clf_UC1.joblib', NOISE_REALISTIC, 'steelblue', 'Random Forest'),
        ('UC2', 'clf_UC2.joblib', NOISE_DEGRADED,  'darkorange', 'SVM'),
    ]

    for ax, (uc_name, clf_path, noise_params, color, model_name) in zip(axes, configs):
        data = joblib.load(clf_path)
        clf    = data['clf']
        X_test = data['X_test']
        y_test = data['y_test']

        if hasattr(clf, 'predict_proba'):
            y_score = clf.predict_proba(X_test)[:, 1]
        else:
            y_score = clf.decision_function(X_test)

        fpr, tpr, _ = roc_curve(y_test, y_score)
        roc_auc = auc(fpr, tpr)

        ax.plot(fpr, tpr, color=color, lw=2,
                label=f'{model_name} (AUC = {roc_auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5)
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('Tasso falsi positivi (FPR)', fontsize=10)
        ax.set_ylabel('Tasso veri positivi (TPR)', fontsize=10)
        ax.set_title(f'Curva ROC — {uc_name}', fontsize=11)
        ax.legend(loc='lower right', fontsize=9)

    fig.suptitle('Curve ROC dei classificatori selezionati', fontsize=12)
    plt.tight_layout()
    path = f'{OUT_DIR}/fig_roc_curve.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f'  → {path}')


# ──────────────────────────────────────────────
# Figura 3: Distribuzione iterazioni M1 vs M2 (UC1)
# ──────────────────────────────────────────────

def _run_method_top4(N, a, n_count, noise_model, shots=1024, max_iter=50, seed=42):
    """TOP-4 senza classificatore (ablazione)."""
    from shor_core import extract_factors, shor_circuit
    from qiskit import transpile
    base_qc = shor_circuit(N, a, n_count)
    sim = AerSimulator(noise_model=noise_model, method='statevector')
    tc = transpile(base_qc, sim, optimization_level=2)
    for iteration in range(1, max_iter + 1):
        counts = sim.run(tc, shots=shots,
                         seed_simulator=seed * 10000 + iteration).result().get_counts()
        for meas_str, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:4]:
            p, q = extract_factors(int(meas_str, 2), n_count, N, a)
            if p is not None:
                return iteration
    return max_iter


def fig_iterazioni_m1_m2():
    print('Raccolta dati iterazioni M1 / M_TOP4 / M2 su UC1 (K=30) ...')
    nm  = build_noise_model(**NOISE_REALISTIC)
    data = joblib.load('clf_UC1.joblib')
    clf  = data['clf']

    K = 30
    m1_iters, mt4_iters, m2_iters = [], [], []
    for rep in range(K):
        print(f'  rep {rep+1}/{K}', end='\r', flush=True)
        r1 = run_method1(15, 7, 8, nm, shots=1024, max_iter=50, seed=rep)
        r2 = run_method2(15, 7, 8, nm, clf, shots=1024, max_iter=50, seed=rep)
        m1_iters.append(r1['iterations'])
        mt4_iters.append(_run_method_top4(15, 7, 8, nm, shots=1024, max_iter=50, seed=rep))
        m2_iters.append(r2['iterations'])
    print()

    m1  = np.array(m1_iters)
    mt4 = np.array(mt4_iters)
    m2  = np.array(m2_iters)

    fig, ax = plt.subplots(figsize=(7, 5))

    bp = ax.boxplot(
        [m1, mt4, m2],
        tick_labels=['M1\n(TOP-1)', '$M_{\\mathrm{TOP4}}$\n(no clf)', 'M2\n(CLF+TOP-4)'],
        patch_artist=True,
        medianprops=dict(color='black', linewidth=2),
        flierprops=dict(marker='o', markerfacecolor='gray', markersize=5, alpha=0.5),
        widths=0.5,
    )
    bp['boxes'][0].set_facecolor('#aec6e8')
    bp['boxes'][1].set_facecolor('#a8d8a8')
    bp['boxes'][2].set_facecolor('#ffb347')

    for i, arr in enumerate([m1, mt4, m2], start=1):
        ax.text(i, arr.mean() + 0.8, f'$\\bar{{M}}={arr.mean():.2f}$',
                ha='center', fontsize=9, color='black')

    # p-value M1 vs M_TOP4
    _, p1 = mannwhitneyu(m1, mt4, alternative='greater')
    # p-value M_TOP4 vs M2 (ablazione)
    _, p2 = mannwhitneyu(mt4, m2, alternative='less')
    ax.text(0.98, 0.97,
            f'M1$>$$M_{{\\mathrm{{TOP4}}}}$: $p={p1:.4f}$\n'
            f'Ablazione $M_{{\\mathrm{{TOP4}}}}$vs M2: $p={p2:.3f}$',
            transform=ax.transAxes, ha='right', va='top', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    ax.set_ylabel('Iterazioni per ottenere i fattori corretti', fontsize=10)
    ax.set_title('UC1 — Analisi di ablazione: M1, $M_{\\mathrm{TOP4}}$, M2\n'
                 '($N=15$, NISQ-realistico, $K=30$, $M_{\\mathrm{max}}=50$)', fontsize=11)
    ax.set_ylim(0, 55)
    ax.axhline(50, color='gray', linestyle=':', linewidth=1, alpha=0.6)
    ax.text(3.35, 50.5, '$M_{\\mathrm{max}}$', fontsize=8, color='gray')

    plt.tight_layout()
    path = f'{OUT_DIR}/fig_iterazioni_m1_m2.pdf'
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    print(f'  → {path}')


if __name__ == '__main__':
    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    # Figura 1: solo simulazione leggera (2 run × 1024 shot)
    fig_istogrammi_qpe()

    # Figura 2: usa solo i .joblib già addestrati
    fig_roc_curve()

    # Figura 3: ri-esegue K=30 run (stessi seed deterministici di mwu_analysis.py)
    fig_iterazioni_m1_m2()

    print('\nTutte le figure generate.')
